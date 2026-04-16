"""Tests for embedding cache durability in save_episodes, save_claims, replace_claims_for_episodes.

Verifies that re-ingesting with unchanged text preserves the cached embedding vector,
and that changed text properly clears the cache.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from ai_knot.storage.sqlite_storage import SQLiteStorage, _deserialize_vec, _serialize_vec


def _make_storage(tmp_path: Any, *, embed: bool = False) -> SQLiteStorage:
    url = "http://fake-embed" if embed else ""
    return SQLiteStorage(str(tmp_path / "test.db"), embed_url=url, embed_model="m1")


def _make_episode(ep_id: str, text: str = "Hello world") -> Any:
    from ai_knot.query_types import RawEpisode

    return RawEpisode(
        id=ep_id,
        agent_id="agent1",
        session_id="s1",
        turn_id=f"s1-{ep_id}",
        speaker="user",
        observed_at=datetime(2024, 1, 1, tzinfo=UTC),
        session_date=None,
        raw_text=text,
        source_meta={},
        parent_episode_id=None,
    )


def _make_claim(claim_id: str, value_text: str = "Alice lives in Paris") -> Any:
    from ai_knot.query_types import AtomicClaim, ClaimKind

    return AtomicClaim(
        id=claim_id,
        agent_id="agent1",
        kind=ClaimKind.STATE,
        subject="Alice",
        relation="lives_in",
        value_text=value_text,
        value_tokens=("alice", "lives", "paris"),
        qualifiers={},
        polarity="support",
        event_time=None,
        observed_at=datetime(2024, 1, 1, tzinfo=UTC),
        valid_from=datetime(2024, 1, 1, tzinfo=UTC),
        valid_until=None,
        confidence=1.0,
        salience=1.0,
        source_episode_id="ep1",
        source_spans=(),
        materialization_version=1,
        materialized_at=datetime(2024, 1, 1, tzinfo=UTC),
        slot_key="Alice::lives_in",
        version=1,
        origin_agent_id="",
    )


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


def test_vec_serialization_round_trip() -> None:
    vec = [0.1, 0.5, -0.3, 0.99]
    assert _deserialize_vec(_serialize_vec(vec)) == pytest.approx(vec, abs=1e-5)


# ---------------------------------------------------------------------------
# Episode embedding cache
# ---------------------------------------------------------------------------


def _write_embedding(
    storage: SQLiteStorage, agent_id: str, ep_id: str, vec: list[float], model: str
) -> None:
    blob = _serialize_vec(vec)
    with storage._conn() as conn:
        conn.execute(
            "UPDATE raw_episodes SET embedding=?, embedding_model=? WHERE agent_id=? AND id=?",
            (blob, model, agent_id, ep_id),
        )


def _read_embedding(
    storage: SQLiteStorage, agent_id: str, ep_id: str
) -> tuple[bytes | None, str | None]:
    with storage._conn() as conn:
        row = conn.execute(
            "SELECT embedding, embedding_model FROM raw_episodes WHERE agent_id=? AND id=?",
            (agent_id, ep_id),
        ).fetchone()
    return (row[0], row[1]) if row else (None, None)


def test_episode_cache_survives_same_text_reingest(tmp_path: Any) -> None:
    """Re-ingesting episode with identical raw_text must preserve embedding."""
    storage = _make_storage(tmp_path)
    ep = _make_episode("ep1", "Alice lives in Paris")
    storage.save_episodes("agent1", [ep])

    # Manually write a cached vector.
    _write_embedding(storage, "agent1", "ep1", [0.1, 0.2], "m1")

    # Re-ingest same episode with unchanged text.
    storage.save_episodes("agent1", [ep])

    blob, model = _read_embedding(storage, "agent1", "ep1")
    assert blob is not None, "Embedding must survive re-ingest with same raw_text"
    assert model == "m1"


def test_episode_cache_clears_on_text_change(tmp_path: Any) -> None:
    """Re-ingesting episode with changed raw_text must clear embedding."""
    storage = _make_storage(tmp_path)
    ep = _make_episode("ep1", "Alice lives in Paris")
    storage.save_episodes("agent1", [ep])
    _write_embedding(storage, "agent1", "ep1", [0.1, 0.2], "m1")

    # Re-ingest with different text.
    ep2 = _make_episode("ep1", "Alice moved to London")
    storage.save_episodes("agent1", [ep2])

    blob, _ = _read_embedding(storage, "agent1", "ep1")
    assert blob is None, "Embedding must be cleared when raw_text changes"


# ---------------------------------------------------------------------------
# Claim embedding cache
# ---------------------------------------------------------------------------


def _write_claim_embedding(
    storage: SQLiteStorage, agent_id: str, claim_id: str, vec: list[float], model: str
) -> None:
    blob = _serialize_vec(vec)
    with storage._conn() as conn:
        conn.execute(
            "UPDATE atomic_claims SET embedding=?, embedding_model=? WHERE agent_id=? AND id=?",
            (blob, model, agent_id, claim_id),
        )


def _read_claim_embedding(
    storage: SQLiteStorage, agent_id: str, claim_id: str
) -> tuple[bytes | None, str | None]:
    with storage._conn() as conn:
        row = conn.execute(
            "SELECT embedding, embedding_model FROM atomic_claims WHERE agent_id=? AND id=?",
            (agent_id, claim_id),
        ).fetchone()
    return (row[0], row[1]) if row else (None, None)


def test_claim_cache_survives_same_value_reingest(tmp_path: Any) -> None:
    """Re-ingesting claim with identical value_text must preserve embedding."""
    storage = _make_storage(tmp_path)
    ep = _make_episode("ep1")
    storage.save_episodes("agent1", [ep])
    claim = _make_claim("c1", "Alice lives in Paris")
    storage.save_claims("agent1", [claim])
    _write_claim_embedding(storage, "agent1", "c1", [0.3, 0.4], "m1")

    storage.save_claims("agent1", [claim])

    blob, model = _read_claim_embedding(storage, "agent1", "c1")
    assert blob is not None, "Claim embedding must survive re-ingest with same value_text"
    assert model == "m1"


def test_claim_cache_clears_on_value_change(tmp_path: Any) -> None:
    """Re-ingesting claim with changed value_text must clear embedding."""
    storage = _make_storage(tmp_path)
    ep = _make_episode("ep1")
    storage.save_episodes("agent1", [ep])
    claim = _make_claim("c1", "Alice lives in Paris")
    storage.save_claims("agent1", [claim])
    _write_claim_embedding(storage, "agent1", "c1", [0.3, 0.4], "m1")

    claim2 = _make_claim("c1", "Alice lives in London")
    storage.save_claims("agent1", [claim2])

    blob, _ = _read_claim_embedding(storage, "agent1", "c1")
    assert blob is None, "Claim embedding must be cleared when value_text changes"


def test_replace_claims_cache_survives_same_value(tmp_path: Any) -> None:
    """replace_claims_for_episodes: cache survives when value_text is unchanged."""
    storage = _make_storage(tmp_path)
    ep = _make_episode("ep1")
    storage.save_episodes("agent1", [ep])
    claim = _make_claim("c1", "Alice lives in Paris")
    storage.save_claims("agent1", [claim])
    _write_claim_embedding(storage, "agent1", "c1", [0.3, 0.4], "m1")

    # replace_claims_for_episodes deletes then re-inserts — cache should survive
    storage.replace_claims_for_episodes("agent1", ["ep1"], [claim])

    blob, model = _read_claim_embedding(storage, "agent1", "c1")
    assert blob is not None, "Cache must survive replace_claims_for_episodes with same value_text"
    assert model == "m1"


def test_replace_claims_cache_clears_on_value_change(tmp_path: Any) -> None:
    """replace_claims_for_episodes: cache clears when value_text changes."""
    storage = _make_storage(tmp_path)
    ep = _make_episode("ep1")
    storage.save_episodes("agent1", [ep])
    claim = _make_claim("c1", "Alice lives in Paris")
    storage.save_claims("agent1", [claim])
    _write_claim_embedding(storage, "agent1", "c1", [0.3, 0.4], "m1")

    claim2 = _make_claim("c1", "Alice lives in London")
    storage.replace_claims_for_episodes("agent1", ["ep1"], [claim2])

    blob, _ = _read_claim_embedding(storage, "agent1", "c1")
    assert blob is None, "Cache must clear when value_text changes in replace_claims_for_episodes"
