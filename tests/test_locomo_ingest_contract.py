"""Contract tests for the LoCoMo ingest path.

Verifies that facts written by the bench harness via kb.add() satisfy the
single-speaker invariant introduced in Stage A (A4-trimmed).
"""

from __future__ import annotations

import pytest

from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage import create_storage


@pytest.fixture()
def kb(tmp_path: pytest.fixture) -> KnowledgeBase:  # type: ignore[type-arg]
    storage = create_storage("sqlite", dsn=str(tmp_path / "contract.db"))
    return KnowledgeBase(storage=storage, agent_id="test-agent")


class TestSingleSpeakerIngest:
    """Each kb.add() call for a dated turn should store one speaker's content."""

    def test_separate_speaker_turns_stored_as_distinct_facts(self, kb: KnowledgeBase) -> None:
        turns = [
            "[1 Jan, 2023] Caroline: I love painting.",
            "[1 Jan, 2023] Melanie: I enjoy pottery.",
            "[3 Feb, 2023] Caroline: Yesterday was great.",
        ]
        for turn in turns:
            kb.add(turn)

        stored = kb._storage.load("test-agent")
        # At minimum the three turns must be stored (children from enum-split may add more).
        assert len(stored) >= 3

    def test_no_multi_speaker_content_in_stored_facts(self, kb: KnowledgeBase) -> None:
        """No single stored fact should contain both 'Caroline' and 'Melanie'."""
        turns = [
            "[1 Jan, 2023] Caroline: I love painting.",
            "[1 Jan, 2023] Melanie: I enjoy pottery.",
        ]
        for turn in turns:
            kb.add(turn)

        stored = kb._storage.load("test-agent")
        for fact in stored:
            has_caroline = "Caroline" in fact.content
            has_melanie = "Melanie" in fact.content
            assert not (has_caroline and has_melanie), (
                f"Multi-speaker fact found after single-speaker ingest: {fact.content!r}"
            )

    def test_date_prefix_preserved(self, kb: KnowledgeBase) -> None:
        kb.add("[8 May, 2023] Jon: I went running today.")
        stored = kb._storage.load("test-agent")
        assert any("8 May, 2023" in f.content or "2023" in f.content for f in stored), (
            "Date prefix not preserved in any stored fact"
        )
