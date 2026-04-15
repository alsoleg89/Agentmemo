"""Regression tests for evidence_text rendering in QueryAnswer.

Verifies that ans.evidence_text contains source sentences and dates,
and that ans.text (answer-text contract) is unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.sqlite_storage import SQLiteStorage

NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _kb(tmp_path: object) -> KnowledgeBase:
    return KnowledgeBase(
        agent_id="a",
        storage=SQLiteStorage(db_path=str(tmp_path / "t.db")),  # type: ignore[operator]
    )


def test_evidence_text_contains_source_sentence(tmp_path: object) -> None:
    """evidence_text must contain the raw source text, not value_text fragments."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t",
        speaker="Elara",
        observed_at=NOW,
        raw_text="Elara told Solun about Verdana yesterday.",
        session_date=datetime(2024, 5, 1, tzinfo=UTC),
    )
    ans = kb.query("Where did Elara go?")
    # Must contain the full source sentence, not a stripped value fragment.
    assert "Elara told Solun about Verdana" in ans.evidence_text


def test_evidence_text_contains_iso_date(tmp_path: object) -> None:
    """evidence_text must embed session_date in ISO format."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t",
        speaker="Elara",
        observed_at=NOW,
        raw_text="Elara mentioned an event.",
        session_date=datetime(2024, 5, 1, tzinfo=UTC),
    )
    ans = kb.query("What did Elara mention?")
    assert "2024-05-01" in ans.evidence_text


def test_answer_text_contract_preserved(tmp_path: object) -> None:
    """Adding evidence_text must not change the type of ans.text."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t",
        speaker="Elara",
        observed_at=NOW,
        raw_text="Elara did something.",
    )
    ans = kb.query("What did Elara do?")
    assert isinstance(ans.text, str)
    # text and evidence_text are separate fields.
    assert hasattr(ans, "evidence_text")
    assert isinstance(ans.evidence_text, str)


def test_no_double_speaker_prefix(tmp_path: object) -> None:
    """If raw_text already starts with 'Speaker:', don't double-prefix."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t",
        speaker="Elara",
        observed_at=NOW,
        raw_text="Elara: I live in Verdana.",
    )
    # evidence_text is only populated when episodes are retrieved.
    # This test just verifies no double-prefix appears if text is present.
    ans = kb.query("Where does Elara live?")
    # Whether or not evidence_text is non-empty, it must not double-prefix.
    if ans.evidence_text:
        assert "Elara: Elara:" not in ans.evidence_text
