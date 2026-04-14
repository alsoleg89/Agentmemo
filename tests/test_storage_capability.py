"""Regression tests for Fix 2: explicit supports_v2_query_planes capability flag.

PostgresStorage must NOT advertise v2 support while its methods still raise
NotImplementedError.  SQLiteStorage must advertise it.  KnowledgeBase.query()
must reject backends that don't have the flag set.
"""

from __future__ import annotations

import pathlib

import pytest

from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.postgres_storage import PostgresStorage
from ai_knot.storage.sqlite_storage import SQLiteStorage
from ai_knot.storage.yaml_storage import YAMLStorage


def test_sqlite_storage_advertises_v2() -> None:
    assert SQLiteStorage.supports_v2_query_planes is True


def test_postgres_storage_does_not_advertise_v2() -> None:
    assert getattr(PostgresStorage, "supports_v2_query_planes", False) is False


def test_kb_query_rejects_yaml_backend(tmp_path: pathlib.Path) -> None:
    """YAMLStorage has no supports_v2_query_planes → query() must raise RuntimeError."""
    kb = KnowledgeBase("a", storage=YAMLStorage(str(tmp_path)))
    with pytest.raises(RuntimeError, match="supports_v2_query_planes"):
        kb.query("anything?")


def test_kb_ingest_episode_rejects_yaml_backend(tmp_path: pathlib.Path) -> None:
    """YAMLStorage has no supports_v2_query_planes → ingest_episode() must raise TypeError."""
    from datetime import UTC, datetime

    kb = KnowledgeBase("a", storage=YAMLStorage(str(tmp_path)))
    with pytest.raises(TypeError, match="supports_v2_query_planes"):
        kb.ingest_episode(
            session_id="s",
            turn_id="t0",
            speaker="user",
            observed_at=datetime(2024, 1, 1, tzinfo=UTC),
            raw_text="Alice is an engineer.",
        )


def test_kb_query_accepts_sqlite_backend(tmp_path: pathlib.Path) -> None:
    """SQLiteStorage supports v2 planes → query() must not raise on empty corpus."""
    kb = KnowledgeBase("a", storage=SQLiteStorage(str(tmp_path / "t.db")))
    # Empty corpus returns empty answer, not RuntimeError.
    ans = kb.query("anything?")
    assert ans is not None
