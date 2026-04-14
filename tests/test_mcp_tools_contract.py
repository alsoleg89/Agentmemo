"""Regression tests for Fix 4: MCP tool_rebuild_materialized serializes correctly.

Previously, tool_rebuild_materialized() passed a RebuildReport dataclass directly
to json.dumps(), which raised TypeError and returned {"error": "not JSON serializable"}
even on successful rebuilds.
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime

from ai_knot import _mcp_tools
from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.sqlite_storage import SQLiteStorage

NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    return KnowledgeBase("a", storage=SQLiteStorage(str(tmp_path / "t.db")))


def test_tool_rebuild_materialized_returns_report_json(tmp_path: pathlib.Path) -> None:
    """tool_rebuild_materialized must return valid JSON with report fields, not an error."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t0",
        speaker="user",
        observed_at=NOW,
        raw_text="Alice is a software engineer.",
    )
    out = _mcp_tools.tool_rebuild_materialized(kb, force=True)
    parsed = json.loads(out)
    assert parsed.get("error") is None, f"unexpected error in response: {parsed.get('error')}"
    assert "materialization_version" in parsed
    assert "n_episodes" in parsed
    assert "skipped" in parsed


def test_tool_rebuild_materialized_skipped_is_valid_json(tmp_path: pathlib.Path) -> None:
    """When rebuild is skipped (already current), response must still be valid JSON."""
    kb = _kb(tmp_path)
    kb.ingest_episode(
        session_id="s",
        turn_id="t0",
        speaker="user",
        observed_at=NOW,
        raw_text="Bob is a doctor.",
    )
    # First rebuild: upgrades materialization_version.
    _mcp_tools.tool_rebuild_materialized(kb, force=True)
    # Second call without force=True: should be skipped.
    out = _mcp_tools.tool_rebuild_materialized(kb)
    parsed = json.loads(out)
    assert parsed.get("error") is None
    assert parsed.get("skipped") is True
