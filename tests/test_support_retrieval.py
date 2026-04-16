"""Tests for support_retrieval.fallback_claim_search hybrid path and ranking preservation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ai_knot.storage.sqlite_storage import SQLiteStorage
from ai_knot.support_retrieval import fallback_claim_search


def _make_storage(tmp_path: Any, *, embed: bool = False) -> SQLiteStorage:
    url = "http://fake-embed" if embed else ""
    return SQLiteStorage(str(tmp_path / "test.db"), embed_url=url, embed_model="m1")


def _make_episode(ep_id: str) -> Any:
    from ai_knot.query_types import RawEpisode

    return RawEpisode(
        id=ep_id,
        agent_id="agent1",
        session_id="s1",
        turn_id=f"s1-{ep_id}",
        speaker="user",
        observed_at=datetime(2024, 1, 1, tzinfo=UTC),
        session_date=None,
        raw_text="placeholder",
        source_meta={},
        parent_episode_id=None,
    )


def _make_claim(
    claim_id: str,
    value_text: str,
    observed_at: datetime,
    subject: str = "Alice",
) -> Any:
    from ai_knot.query_types import AtomicClaim, ClaimKind

    return AtomicClaim(
        id=claim_id,
        agent_id="agent1",
        kind=ClaimKind.STATE,
        subject=subject,
        relation="is",
        value_text=value_text,
        value_tokens=tuple(value_text.lower().split()),
        qualifiers={},
        polarity="support",
        event_time=None,
        observed_at=observed_at,
        valid_from=datetime(2024, 1, 1, tzinfo=UTC),
        valid_until=None,
        confidence=1.0,
        salience=1.0,
        source_episode_id="ep1",
        source_spans=(),
        materialization_version=1,
        materialized_at=datetime(2024, 1, 1, tzinfo=UTC),
        slot_key=f"{subject}::is",
        version=1,
        origin_agent_id="",
    )


# ---------------------------------------------------------------------------
# Ranking preservation guard (finding #1)
# ---------------------------------------------------------------------------


def test_fallback_claim_search_returns_bm25_order_not_observed_at(tmp_path: Any) -> None:
    """fallback_claim_search must return claims in BM25-scored order, not observed_at order.

    This test seeds three claims with hand-picked observed_at timestamps so that
    load_claims(ORDER BY observed_at) would return them in the OPPOSITE order
    to BM25 relevance. The test asserts that the BM25-ranked order is preserved.
    """
    storage = _make_storage(tmp_path)

    # Claim timestamps: newest first by observed_at → c_new > c_mid > c_old
    # But BM25 relevance for "Paris capital France" → c_old has highest overlap
    c_old = _make_claim(
        "c_old",
        "Paris is the capital of France and a major European city",  # high BM25 for 'Paris capital'
        observed_at=datetime(2023, 1, 1, tzinfo=UTC),  # oldest
    )
    c_mid = _make_claim(
        "c_mid",
        "France is a country in Western Europe",  # medium BM25
        observed_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    c_new = _make_claim(
        "c_new",
        "The weather in London is often cloudy",  # zero BM25 for 'Paris capital'
        observed_at=datetime(2025, 1, 1, tzinfo=UTC),  # newest
    )

    ep = _make_episode("ep1")
    storage.save_episodes("agent1", [ep])
    storage.save_claims("agent1", [c_old, c_mid, c_new])

    results = fallback_claim_search(storage, "agent1", "What is the capital of France?", top_k=10)

    # Results must include the relevant claims.
    ids = [c.id for c in results]
    assert "c_old" in ids, "BM25-relevant claim must appear in results"

    # The BM25-most-relevant claim (c_old) must appear before the newest-but-irrelevant (c_new).
    # If c_new appears in results at all, c_old must precede it.
    if "c_new" in ids:
        assert ids.index("c_old") < ids.index("c_new"), (
            f"BM25-ranked c_old (observed=2023) must precede c_new (observed=2025) "
            f"even though observed_at order is c_new first. Got order: {ids}"
        )


# ---------------------------------------------------------------------------
# Legacy backend path (no search_claims_semantic)
# ---------------------------------------------------------------------------


def test_fallback_claim_search_legacy_path(tmp_path: Any) -> None:
    """Legacy overlap-TF path fires when storage lacks search_claims_semantic."""

    class MinimalStorage:
        """Minimal storage with only iter_value_text + load_claims (no search_claims_semantic)."""

        def __init__(self) -> None:
            self._claims: dict[str, Any] = {}

        def iter_value_text(self, agent_id: str) -> list[tuple[str, str]]:
            return [(cid, c.value_text) for cid, c in self._claims.items()]

        def load_claims(
            self,
            agent_id: str,
            *,
            ids: list[str] | None = None,
            subjects: list[str] | None = None,
            kinds: list[Any] | None = None,
            active_only: bool = True,
        ) -> list[Any]:
            if ids is None:
                return list(self._claims.values())
            return [self._claims[i] for i in ids if i in self._claims]

    store = MinimalStorage()
    claim = _make_claim("c1", "Alice lives in Paris", datetime(2024, 1, 1, tzinfo=UTC))
    store._claims["c1"] = claim

    results = fallback_claim_search(store, "agent1", "Where does Alice live?", top_k=10)
    ids = [c.id for c in results]
    assert "c1" in ids, "Legacy path must return results via iter_value_text + load_claims"


# ---------------------------------------------------------------------------
# Stub embed — semantic match wins when BM25 scores zero
# ---------------------------------------------------------------------------


def test_fallback_search_semantic_gap(tmp_path: Any, monkeypatch: Any) -> None:
    """Hybrid: stub embed makes semantic match win even when BM25 overlap is zero."""
    import ai_knot.embedder as _embedder_mod

    storage = _make_storage(tmp_path, embed=True)

    c_bm25 = _make_claim("c_bm25", "Alice works at Google", datetime(2024, 1, 1, tzinfo=UTC))
    c_semantic = _make_claim(
        "c_semantic",
        "Alice is employed by Google",  # no BM25 overlap with "job"
        datetime(2023, 1, 1, tzinfo=UTC),
    )

    ep = _make_episode("ep1")
    storage.save_episodes("agent1", [ep])
    storage.save_claims("agent1", [c_bm25, c_semantic])

    # Stub: query "Alice job" → closer to c_semantic vector
    async def fake_embed(
        texts: list[str],
        *,
        base_url: str,
        model: str,
        api_key: Any = None,
        timeout: float = 30.0,
    ) -> list[list[float]]:
        vmap = {
            "Alice is Alice works at Google": [0.1, 0.9],  # low cosine with query
            "Alice is Alice is employed by Google": [0.9, 0.1],  # high cosine with query
            "Alice works at Google": [0.1, 0.9],
            "Alice is employed by Google": [0.9, 0.1],
            "Alice job": [0.9, 0.1],  # query vector — closer to c_semantic
        }
        return [vmap.get(t, [0.5, 0.5]) for t in texts]

    monkeypatch.setattr(_embedder_mod, "embed_texts", fake_embed)

    results = fallback_claim_search(storage, "agent1", "Alice job", top_k=5)
    ids = [c.id for c in results]
    assert "c_semantic" in ids, f"Semantic match c_semantic must appear in results: {ids}"
