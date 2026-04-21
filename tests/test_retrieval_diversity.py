"""Tests for MMR per-session diversity in search_episodes_by_entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from ai_knot.storage.sqlite_storage import (
    _mmr_rerank,
    _mmr_sim,
    _per_session_floor,
)

# ---------------------------------------------------------------------------
# Minimal fake episode for testing
# ---------------------------------------------------------------------------


@dataclass
class FakeEpisode:
    id: str
    session_id: str
    raw_text: str


# ---------------------------------------------------------------------------
# Tests for _per_session_floor
# ---------------------------------------------------------------------------


def test_per_session_floor_guarantees_one_per_session() -> None:
    """Each session must have ≥ 1 representative in the floor list."""
    eps = [
        FakeEpisode(id="a1", session_id="s1", raw_text="alpha one"),
        FakeEpisode(id="a2", session_id="s1", raw_text="alpha two"),
        FakeEpisode(id="b1", session_id="s2", raw_text="beta one"),
        FakeEpisode(id="b2", session_id="s2", raw_text="beta two"),
        FakeEpisode(id="c1", session_id="s3", raw_text="gamma one"),
    ]
    eps_by_id: dict[str, Any] = {e.id: e for e in eps}
    ranked_ids = [e.id for e in eps]  # a1, a2, b1, b2, c1

    result = _per_session_floor(ranked_ids, eps_by_id)

    # All original IDs must be present exactly once.
    assert sorted(result) == sorted(ranked_ids)

    # The first n_floor=1 items per session must appear before the rest.
    # Sessions: s1→a1, s2→b1, s3→c1 must all be in the floor prefix.
    floor_set = {"a1", "b1", "c1"}
    result_set_prefix = set(result[: len(floor_set)])
    assert floor_set.issubset(result_set_prefix), f"Floor representatives not in prefix: {result}"


def test_per_session_floor_single_session_unchanged_order() -> None:
    """When all episodes belong to one session, order is preserved."""
    eps = [
        FakeEpisode(id="x1", session_id="s1", raw_text="text one"),
        FakeEpisode(id="x2", session_id="s1", raw_text="text two"),
        FakeEpisode(id="x3", session_id="s1", raw_text="text three"),
    ]
    eps_by_id: dict[str, Any] = {e.id: e for e in eps}
    ranked_ids = ["x1", "x2", "x3"]

    result = _per_session_floor(ranked_ids, eps_by_id)
    assert result == ranked_ids


def test_per_session_floor_preserves_all_ids() -> None:
    """No IDs should be lost or duplicated after floor application."""
    eps = [FakeEpisode(id=f"e{i}", session_id=f"s{i % 3}", raw_text=f"text {i}") for i in range(9)]
    eps_by_id: dict[str, Any] = {e.id: e for e in eps}
    ranked_ids = [e.id for e in eps]

    result = _per_session_floor(ranked_ids, eps_by_id)

    assert len(result) == len(ranked_ids)
    assert sorted(result) == sorted(ranked_ids)


# ---------------------------------------------------------------------------
# Tests for _mmr_rerank
# ---------------------------------------------------------------------------


def test_mmr_rerank_reduces_same_session_clustering() -> None:
    """MMR with high beta should promote diversity across sessions."""
    # 4 eps from session s1 (high BM25 rank) and 2 from s2 (lower rank)
    eps_s1 = [
        FakeEpisode(id=f"s1_{i}", session_id="s1", raw_text=f"cats dogs food {i}") for i in range(4)
    ]
    eps_s2 = [
        FakeEpisode(id=f"s2_{i}", session_id="s2", raw_text=f"books reading library {i}")
        for i in range(2)
    ]

    # All s1 episodes ranked first (simulating BM25 cluster)
    ranked_ids = [e.id for e in eps_s1] + [e.id for e in eps_s2]
    eps_by_id: dict[str, Any] = {e.id: e for e in eps_s1 + eps_s2}

    # Apply MMR with high beta=0.8 to strongly penalize same-session similarity
    result = _mmr_rerank(ranked_ids, eps_by_id, k=4, beta=0.8)

    # With strong diversity pressure, at least one s2 episode should be selected
    selected_sessions = {eps_by_id[rid].session_id for rid in result}
    assert "s2" in selected_sessions, (
        f"MMR did not introduce s2 diversity; got sessions: {selected_sessions}"
    )


def test_mmr_rerank_respects_k() -> None:
    """Output length must not exceed k."""
    eps = [FakeEpisode(id=f"e{i}", session_id=f"s{i % 2}", raw_text=f"word{i}") for i in range(10)]
    eps_by_id: dict[str, Any] = {e.id: e for e in eps}
    ranked_ids = [e.id for e in eps]

    for k in (1, 3, 5, 10):
        result = _mmr_rerank(ranked_ids, eps_by_id, k=k, beta=0.3)
        assert len(result) <= k, f"MMR returned {len(result)} > k={k}"


def test_mmr_rerank_single_item_unchanged() -> None:
    """A single-item list must be returned as-is."""
    eps = [FakeEpisode(id="only", session_id="s1", raw_text="solo")]
    eps_by_id: dict[str, Any] = {e.id: e for e in eps}
    result = _mmr_rerank(["only"], eps_by_id, k=5, beta=0.3)
    assert result == ["only"]


def test_mmr_rerank_no_duplicates() -> None:
    """MMR must not return duplicate IDs."""
    eps = [FakeEpisode(id=f"e{i}", session_id=f"s{i % 3}", raw_text=f"token{i}") for i in range(12)]
    eps_by_id: dict[str, Any] = {e.id: e for e in eps}
    ranked_ids = [e.id for e in eps]

    result = _mmr_rerank(ranked_ids, eps_by_id, k=8, beta=0.3)
    assert len(result) == len(set(result)), "Duplicate IDs found in MMR output"


# ---------------------------------------------------------------------------
# Tests for _mmr_sim
# ---------------------------------------------------------------------------


def test_mmr_sim_same_session_high() -> None:
    """Same-session episodes should have high similarity."""
    a = FakeEpisode(id="a", session_id="s1", raw_text="alpha beta gamma")
    b = FakeEpisode(id="b", session_id="s1", raw_text="alpha delta epsilon")
    sim = _mmr_sim(a, b)
    # same_session=1.0, jaccard>0 → sim >= 0.7
    assert sim >= 0.7


def test_mmr_sim_different_session_low() -> None:
    """Different-session episodes with no token overlap should have low sim."""
    a = FakeEpisode(id="a", session_id="s1", raw_text="cats dogs pets")
    b = FakeEpisode(id="b", session_id="s2", raw_text="books reading library")
    sim = _mmr_sim(a, b)
    # same_session=0.0, jaccard=0.0 → sim = 0.0
    assert sim == pytest.approx(0.0)


def test_mmr_sim_symmetric() -> None:
    """Similarity must be symmetric."""
    a = FakeEpisode(id="a", session_id="s1", raw_text="hello world foo")
    b = FakeEpisode(id="b", session_id="s2", raw_text="hello bar baz world")
    assert _mmr_sim(a, b) == pytest.approx(_mmr_sim(b, a))
