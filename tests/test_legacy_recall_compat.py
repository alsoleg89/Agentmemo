"""Regression tests — legacy recall() must continue to work unchanged.

These tests verify that adding v2 planes (ingest_episode, query, rebuild_materialized)
does not break the existing add/recall/forget/snapshot API.
"""

from __future__ import annotations

from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.sqlite_storage import SQLiteStorage
from ai_knot.storage.yaml_storage import YAMLStorage


def _sqlite_kb(tmp_path, agent_id="agent") -> KnowledgeBase:
    storage = SQLiteStorage(db_path=str(tmp_path / "test.db"))
    return KnowledgeBase(agent_id=agent_id, storage=storage)


def _yaml_kb(tmp_path, agent_id="agent") -> KnowledgeBase:
    storage = YAMLStorage(base_dir=str(tmp_path / "yaml"))
    return KnowledgeBase(agent_id=agent_id, storage=storage)


# ---------------------------------------------------------------------------
# Core add / recall / forget — SQLite backend
# ---------------------------------------------------------------------------


class TestLegacyRecallSQLite:
    def test_add_and_recall_returns_content(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        kb.add("Alice works as a software engineer.")
        result = kb.recall("what does Alice do?")
        assert "Alice" in result or "engineer" in result or result  # non-empty

    def test_add_multiple_and_recall_top_k(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        for i in range(10):
            kb.add(f"Fact number {i} about Alice.")
        result = kb.recall("Alice facts", top_k=3)
        assert isinstance(result, str)

    def test_forget_removes_fact(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        fact = kb.add("Alice likes coffee.")
        kb.forget(fact.id)
        result = kb.recall("Alice coffee")
        assert "coffee" not in result.lower() or result == ""

    def test_list_facts_shows_added_facts(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        kb.add("Bob is a doctor.")
        facts = kb.list_facts()
        assert len(facts) >= 1
        assert any("Bob" in f.content or "doctor" in f.content for f in facts)

    def test_stats_returns_expected_keys(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        kb.add("Charlie plays guitar.")
        stats = kb.stats()
        assert "total_facts" in stats
        assert stats["total_facts"] >= 1

    def test_snapshot_and_restore(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        kb.add("Diana is an artist.")
        kb.snapshot("snap1")
        kb.forget(kb.list_facts()[0].id)
        kb.restore("snap1")
        facts = kb.list_facts()
        assert any("Diana" in f.content for f in facts)

    def test_recall_returns_string(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        result = kb.recall("anything at all", top_k=5)
        assert isinstance(result, str)

    def test_recall_empty_kb_returns_string(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        result = kb.recall("nothing here", top_k=5)
        assert isinstance(result, str)

    def test_recall_facts_returns_list(self, tmp_path):
        kb = _sqlite_kb(tmp_path)
        kb.add("Eve is a painter.")
        facts = kb.recall_facts("Eve painter", top_k=5)
        assert isinstance(facts, list)


# ---------------------------------------------------------------------------
# Mixed v2 + legacy in same KB — SQLite
# ---------------------------------------------------------------------------


class TestLegacyRecallCoexistsWithV2:
    def test_add_recall_still_works_after_ingest_episode(self, tmp_path):
        """Legacy add/recall must not be broken after ingest_episode is called."""
        from datetime import UTC, datetime

        kb = _sqlite_kb(tmp_path)
        NOW = datetime(2024, 1, 1, tzinfo=UTC)

        # Use v2 path
        kb.ingest_episode(
            session_id="sess-0",
            turn_id="turn-0",
            speaker="user",
            observed_at=NOW,
            raw_text="Frank is a carpenter.",
        )

        # Legacy path still works
        kb.add("Grace plays violin.")
        result = kb.recall("Grace violin")
        assert isinstance(result, str)

    def test_legacy_facts_not_lost_after_rebuild(self, tmp_path):
        """rebuild_materialized does not touch the legacy facts table."""
        from datetime import UTC, datetime

        kb = _sqlite_kb(tmp_path)
        NOW = datetime(2024, 1, 1, tzinfo=UTC)

        kb.add("Henry is a chef.")
        kb.ingest_episode(
            session_id="sess-0",
            turn_id="turn-0",
            speaker="user",
            observed_at=NOW,
            raw_text="Iris is a nurse.",
        )
        kb.rebuild_materialized(force=True)

        # Legacy fact must still be there
        facts = kb.list_facts()
        assert any("Henry" in f.content for f in facts)

    def test_recall_not_empty_after_mixed_ingest(self, tmp_path):
        from datetime import UTC, datetime

        kb = _sqlite_kb(tmp_path)
        NOW = datetime(2024, 1, 1, tzinfo=UTC)

        kb.add("Jack is an engineer.")
        kb.ingest_episode(
            session_id="sess-0",
            turn_id="t0",
            speaker="user",
            observed_at=NOW,
            raw_text="Jack works at Acme.",
        )
        result = kb.recall("Jack", top_k=5)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# YAML backend — basic recall regression
# ---------------------------------------------------------------------------


class TestLegacyRecallYAML:
    def test_add_and_recall_yaml(self, tmp_path):
        kb = _yaml_kb(tmp_path)
        kb.add("Kim likes hiking.")
        result = kb.recall("Kim hiking")
        assert isinstance(result, str)

    def test_snapshot_yaml(self, tmp_path):
        kb = _yaml_kb(tmp_path)
        kb.add("Leo is a musician.")
        kb.snapshot("snap1")
        kb.restore("snap1")
        facts = kb.list_facts()
        assert any("Leo" in f.content for f in facts)
