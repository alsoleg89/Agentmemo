"""Regression tests for _joint_rerank_episodes RRF fusion.

Verifies:
1. Operator head is always first when provided.
2. Episodes appearing in multiple ranked lists rank higher than single-list ones.
3. Empty inputs produce empty output.
4. cap is respected.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_knot.query_runtime import _joint_rerank_episodes
from ai_knot.query_types import AnswerItem, AtomicClaim, ClaimKind


def _make_item(ep_ids: list[str], value: str = "v") -> AnswerItem:
    return AnswerItem(
        value=value,
        confidence=0.9,
        source_claim_ids=(),
        source_episode_ids=tuple(ep_ids),
    )


def _make_claim(ep_id: str) -> AtomicClaim:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return AtomicClaim(
        id="c" + ep_id,
        agent_id="a",
        kind=ClaimKind.STATE,
        subject="X",
        relation="has",
        value_text="v",
        value_tokens=("v",),
        qualifiers={},
        polarity="support",
        event_time=None,
        observed_at=now,
        valid_from=now,
        valid_until=None,
        confidence=0.8,
        salience=0.8,
        source_episode_id=ep_id,
        source_spans=(),
        materialization_version=1,
        materialized_at=now,
        slot_key="X::has",
        version=1,
        origin_agent_id="a",
    )


class TestJointRerank:
    def test_operator_head_always_first(self) -> None:
        """operator_head must be position 0 regardless of RRF rank."""
        items = [_make_item(["ep1", "ep2"])]
        claims = [_make_claim("ep3")]
        raw = ["ep2", "ep1", "ep3"]

        result = _joint_rerank_episodes(items, claims, raw, cap=5, operator_head="ep3")
        assert result[0] == "ep3", f"operator_head not first: {result}"

    def test_multi_list_beats_single_list(self) -> None:
        """An episode in both raw_list and claim_list must outrank one only in raw_list."""
        # ep_shared appears in both raw_list and item_list
        # ep_raw_only appears only in raw_list (at rank 1)
        items = [_make_item(["ep_shared"])]
        claims = []
        raw = ["ep_raw_only", "ep_shared"]  # ep_raw_only is rank 1 in raw

        result = _joint_rerank_episodes(items, claims, raw, cap=5)
        shared_rank = result.index("ep_shared")
        raw_only_rank = result.index("ep_raw_only")
        assert shared_rank < raw_only_rank, (
            f"ep_shared (in 2 lists) rank {shared_rank} must beat "
            f"ep_raw_only (in 1 list) rank {raw_only_rank}"
        )

    def test_cap_respected(self) -> None:
        """Result must not exceed cap."""
        raw = [f"ep{i}" for i in range(20)]
        items = [_make_item([f"ep{i}" for i in range(5, 15)])]
        claims = [_make_claim(f"ep{i}") for i in range(10, 20)]

        result = _joint_rerank_episodes(items, claims, raw, cap=7)
        assert len(result) <= 7

    def test_empty_inputs(self) -> None:
        """All-empty inputs produce empty list."""
        result = _joint_rerank_episodes([], [], None, cap=5)
        assert result == []

    def test_operator_head_not_duplicated(self) -> None:
        """operator_head must appear exactly once in output."""
        items = [_make_item(["ep1"])]
        claims = [_make_claim("ep1")]
        raw = ["ep1", "ep2"]

        result = _joint_rerank_episodes(items, claims, raw, cap=5, operator_head="ep1")
        assert result.count("ep1") == 1, f"ep1 duplicated in {result}"
        assert result[0] == "ep1"
