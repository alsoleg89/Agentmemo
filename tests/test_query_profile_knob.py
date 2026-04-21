"""Regression tests for AIKNOT_QUERY_PROFILE query caps.

Verifies that:
1. narrow < balanced < wide in terms of episode count rendered.
2. char_budget is enforced and evidence_text doesn't overflow.
3. Default profile (balanced) is applied when env var is not set.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from ai_knot.query_runtime import _PROFILE_CAPS, _CapSet, _get_caps, _render_evidence_context
from ai_knot.query_types import RawEpisode
from ai_knot.storage.sqlite_storage import SQLiteStorage


def _ep(n: int, text: str = "some content here", agent_id: str = "a") -> RawEpisode:
    return RawEpisode(
        id=f"ep{n}",
        agent_id=agent_id,
        session_id="s",
        turn_id=f"s-{n}",
        speaker="user",
        observed_at=datetime(2024, 1, n + 1, tzinfo=UTC),
        session_date=None,
        raw_text=text,
        source_meta={},
        parent_episode_id=None,
    )


class TestCapOrdering:
    def test_narrow_has_smaller_caps_than_balanced(self) -> None:
        n = _PROFILE_CAPS["narrow"]
        b = _PROFILE_CAPS["balanced"]
        assert n.raw_search_top_k < b.raw_search_top_k
        assert n.window_dedup_cap < b.window_dedup_cap
        assert n.collect_cap < b.collect_cap
        assert n.render_top_k < b.render_top_k
        assert n.char_budget < b.char_budget

    def test_balanced_has_smaller_caps_than_wide(self) -> None:
        b = _PROFILE_CAPS["balanced"]
        w = _PROFILE_CAPS["wide"]
        assert b.raw_search_top_k < w.raw_search_top_k
        assert b.window_dedup_cap < w.window_dedup_cap
        assert b.collect_cap < w.collect_cap
        assert b.render_top_k < w.render_top_k
        assert b.char_budget < w.char_budget


class TestGetCaps:
    def test_default_is_balanced(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AIKNOT_QUERY_PROFILE", None)
            caps = _get_caps()
        assert caps == _PROFILE_CAPS["balanced"]

    def test_narrow_profile(self) -> None:
        with patch.dict(os.environ, {"AIKNOT_QUERY_PROFILE": "narrow"}):
            caps = _get_caps()
        assert caps == _PROFILE_CAPS["narrow"]

    def test_wide_profile(self) -> None:
        with patch.dict(os.environ, {"AIKNOT_QUERY_PROFILE": "wide"}):
            caps = _get_caps()
        assert caps == _PROFILE_CAPS["wide"]

    def test_unknown_profile_falls_back_to_balanced(self) -> None:
        with patch.dict(os.environ, {"AIKNOT_QUERY_PROFILE": "unknown_value"}):
            caps = _get_caps()
        assert caps == _PROFILE_CAPS["balanced"]


class TestRenderEvidenceContext:
    def test_char_budget_is_enforced(self, tmp_path: object) -> None:
        """evidence_text total length must not exceed char_budget."""
        storage = SQLiteStorage(str(tmp_path) + "/test.db", embed_url="")  # type: ignore[operator]
        episodes = [_ep(i, "A" * 500) for i in range(20)]
        storage.save_episodes("a", episodes)

        result = _render_evidence_context(
            storage, "a",
            [f"ep{i}" for i in range(20)],
            top_k=20,
            char_budget=2_000,
            per_turn_max=500,
        )
        assert len(result) <= 2_000 + 100  # small slack for line overhead

    def test_per_turn_max_truncates_long_turns(self, tmp_path: object) -> None:
        """Individual turns longer than per_turn_max must be truncated."""
        storage = SQLiteStorage(str(tmp_path) + "/test2.db", embed_url="")  # type: ignore[operator]
        long_ep = _ep(0, "X" * 2000)
        storage.save_episodes("a", [long_ep])

        result = _render_evidence_context(
            storage, "a", ["ep0"], top_k=5, char_budget=10_000, per_turn_max=100
        )
        # The raw_text in output should be capped at per_turn_max
        # "[1] user: " + 100 X's
        assert "X" * 101 not in result

    def test_balanced_renders_more_than_narrow(self, tmp_path: object) -> None:
        """balanced profile must render more episodes than narrow."""
        storage = SQLiteStorage(str(tmp_path) + "/test3.db", embed_url="")  # type: ignore[operator]
        episodes = [_ep(i, f"episode content {i}") for i in range(25)]
        storage.save_episodes("a", episodes)
        ep_ids = [f"ep{i}" for i in range(25)]

        narrow = _PROFILE_CAPS["narrow"]
        balanced = _PROFILE_CAPS["balanced"]

        narrow_result = _render_evidence_context(
            storage, "a", ep_ids,
            top_k=narrow.render_top_k,
            char_budget=narrow.char_budget,
            per_turn_max=narrow.per_turn_max,
        )
        balanced_result = _render_evidence_context(
            storage, "a", ep_ids,
            top_k=balanced.render_top_k,
            char_budget=balanced.char_budget,
            per_turn_max=balanced.per_turn_max,
        )

        narrow_count = narrow_result.count("\n[") + (1 if narrow_result else 0)
        balanced_count = balanced_result.count("\n[") + (1 if balanced_result else 0)
        assert balanced_count > narrow_count, (
            f"balanced ({balanced_count} episodes) must exceed narrow ({narrow_count})"
        )
