"""Regression tests for episode-level fallback when bundle plane is empty."""

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


def test_episode_fallback_when_bundle_plane_empty(tmp_path: object) -> None:
    """With materialize=False the bundle plane is empty; fallback must kick in."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t",
        speaker="Quentin",
        observed_at=NOW,
        raw_text="Quentin witnessed Novalux on 2024-06-15.",
        session_date=datetime(2024, 6, 15, tzinfo=UTC),
        materialize=False,
    )
    ans = kb.query("When did Quentin witness Novalux?")
    assert ans.trace.evidence_profile.episode_fallback_used is True
    assert "Quentin witnessed Novalux" in ans.evidence_text


def test_episode_fallback_not_triggered_when_bundles_exist(tmp_path: object) -> None:
    """When bundles exist and return claims, episode_fallback_used must be False."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t",
        speaker="Petra",
        observed_at=NOW,
        raw_text="Petra: I drive a Vortex.",
    )
    ans = kb.query("What does Petra drive?")
    assert ans.trace.evidence_profile.episode_fallback_used is False
