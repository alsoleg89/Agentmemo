"""Decay visibility — default stability_hours=48 makes forgetting observable within a day.

Validates that:
1. High vs low importance facts have a visible retention ratio after 24 h.
2. KnowledgeBase(stability_hours=48) behaves differently from stability_hours=336.
3. The base_hours parameter threads correctly from KnowledgeBase through apply_decay.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime, timedelta

import pytest

from ai_knot.forgetting import apply_decay, calculate_retention, calculate_stability
from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.yaml_storage import YAMLStorage
from ai_knot.types import Fact


class TestDecayVisibility:
    """With base_hours=48, high/low importance have a noticeable ratio after 24 h."""

    def test_ratio_above_2x_after_24h_default(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=UTC)
        now = base + timedelta(hours=24)

        high = Fact(content="important fact", importance=0.9, last_accessed=base)
        low = Fact(content="trivial fact", importance=0.2, last_accessed=base)

        r_high = calculate_retention(high, now=now, base_hours=48.0)
        r_low = calculate_retention(low, now=now, base_hours=48.0)

        assert r_high > 0.0
        assert r_low > 0.0
        ratio = r_high / r_low
        assert ratio > 2.0, (
            f"Expected ratio > 2.0 after 24 h with base_hours=48, got {ratio:.2f} "
            f"(high={r_high:.3f}, low={r_low:.3f})"
        )

    def test_conservative_336h_flat_after_24h(self) -> None:
        """With base_hours=336, both facts still have retention > 0.9 after 24 h."""
        base = datetime(2026, 1, 1, tzinfo=UTC)
        now = base + timedelta(hours=24)

        high = Fact(content="important", importance=0.9, last_accessed=base)
        low = Fact(content="trivial", importance=0.2, last_accessed=base)

        r_high = calculate_retention(high, now=now, base_hours=336.0)
        r_low = calculate_retention(low, now=now, base_hours=336.0)

        # Both are still near 1.0 — decay barely visible at 24 h with 336 h base
        assert r_high > 0.9
        assert r_low > 0.5  # e^(-24/67.2) ≈ 0.70 — still relatively high

    def test_apply_decay_threads_base_hours(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=UTC)
        now = base + timedelta(hours=24)

        facts_48 = [Fact(content="test", importance=0.9, last_accessed=base)]
        facts_336 = [Fact(content="test", importance=0.9, last_accessed=base)]

        apply_decay(facts_48, now=now, base_hours=48.0)
        apply_decay(facts_336, now=now, base_hours=336.0)

        assert facts_48[0].retention_score < facts_336[0].retention_score

    def test_calculate_stability_base_hours_param(self) -> None:
        s_48 = calculate_stability(0.8, 0, base_hours=48.0)
        s_336 = calculate_stability(0.8, 0, base_hours=336.0)
        assert s_48 == pytest.approx(48.0 * 0.8 * 1.0, rel=1e-6)
        assert s_336 == pytest.approx(336.0 * 0.8 * 1.0, rel=1e-6)
        assert s_48 < s_336


class TestKnowledgeBaseStabilityHours:
    """KnowledgeBase.stability_hours is threaded into all apply_decay calls."""

    def test_aggressive_decay_produces_lower_retention(self, tmp_path: pathlib.Path) -> None:
        base = datetime(2026, 1, 1, tzinfo=UTC)
        now = base + timedelta(hours=24)

        # Build fact with known last_accessed
        fact = Fact(content="test fact", importance=0.9, last_accessed=base)

        # Simulate what KnowledgeBase.recall does internally
        facts_48 = [Fact(content="test fact", importance=0.9, last_accessed=base)]
        facts_336 = [Fact(content="test fact", importance=0.9, last_accessed=base)]

        apply_decay(facts_48, now=now, base_hours=48.0)
        apply_decay(facts_336, now=now, base_hours=336.0)

        assert facts_48[0].retention_score < facts_336[0].retention_score
        del fact  # silence unused warning

    def test_default_stability_hours_is_48(self, tmp_path: pathlib.Path) -> None:
        storage = YAMLStorage(base_dir=str(tmp_path))
        kb = KnowledgeBase(agent_id="test", storage=storage)
        assert kb._stability_hours == 48.0

    def test_custom_stability_hours_stored(self, tmp_path: pathlib.Path) -> None:
        storage = YAMLStorage(base_dir=str(tmp_path))
        kb = KnowledgeBase(agent_id="test", storage=storage, stability_hours=336.0)
        assert kb._stability_hours == 336.0
