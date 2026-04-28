"""Tests that _build_kb() routes AI_KNOT_DB_PATH to the storage dsn argument."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_knot.mcp_server import _build_kb


class TestBuildKbDsnRouting:
    """_build_kb() must pass AI_KNOT_DB_PATH as dsn to create_storage."""

    def test_ai_knot_db_path_passed_as_dsn(
        self,
        tmp_path: pytest.fixture,
        monkeypatch: pytest.MonkeyPatch,  # type: ignore[type-arg]
    ) -> None:
        db_file = str(tmp_path / "custom.db")
        monkeypatch.setenv("AI_KNOT_DB_PATH", db_file)
        monkeypatch.setenv("AI_KNOT_DATA_DIR", str(tmp_path / "base"))
        monkeypatch.setenv("AI_KNOT_STORAGE", "sqlite")

        with (
            patch("ai_knot.mcp_server.create_storage") as mock_cs,
            patch("ai_knot.mcp_server.KnowledgeBase") as mock_kb,
        ):
            mock_cs.return_value = MagicMock()
            mock_kb.return_value = MagicMock()
            _build_kb()

            mock_cs.assert_called_once()
            call_kwargs = mock_cs.call_args.kwargs
            assert call_kwargs.get("dsn") == db_file, (
                f"create_storage was called with dsn={call_kwargs.get('dsn')!r}, "
                f"expected {db_file!r}"
            )

    def test_fallback_to_data_dir_when_no_db_path(
        self,
        tmp_path: pytest.fixture,
        monkeypatch: pytest.MonkeyPatch,  # type: ignore[type-arg]
    ) -> None:
        """When AI_KNOT_DB_PATH is absent, dsn falls back to data_dir/ai_knot.db."""
        monkeypatch.delenv("AI_KNOT_DB_PATH", raising=False)
        monkeypatch.setenv("AI_KNOT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("AI_KNOT_STORAGE", "sqlite")

        with (
            patch("ai_knot.mcp_server.create_storage") as mock_cs,
            patch("ai_knot.mcp_server.KnowledgeBase") as mock_kb,
        ):
            mock_cs.return_value = MagicMock()
            mock_kb.return_value = MagicMock()
            _build_kb()

            call_kwargs = mock_cs.call_args.kwargs
            dsn = call_kwargs.get("dsn") or ""
            assert "ai_knot.db" in dsn, (
                f"Expected fallback path containing 'ai_knot.db', got {dsn!r}"
            )
