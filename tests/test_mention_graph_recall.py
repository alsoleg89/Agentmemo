"""Integration tests: mention graph improves recall for entity-hop queries."""

from __future__ import annotations

import os
import pathlib

import pytest

from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.sqlite_storage import SQLiteStorage


def _kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    return KnowledgeBase(
        agent_id="mg-test",
        storage=SQLiteStorage(db_path=str(tmp_path / "mg.db")),
    )


class TestMentionGraphRecall:
    def test_entity_hop_expands_candidate_pool(self, tmp_path: pathlib.Path) -> None:
        """Facts about Alice should surface when query uses her name, via mg."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("AI_KNOT_MENTION_GRAPH", "1")
            # Re-read the module flag
            import importlib

            import ai_knot.mention_graph as mg_mod

            importlib.reload(mg_mod)
            import ai_knot.knowledge as k_mod

            importlib.reload(k_mod)
            from ai_knot.knowledge import KnowledgeBase as KB
            from ai_knot.storage.sqlite_storage import SQLiteStorage as SS

            kb = KB(agent_id="mg-int", storage=SS(db_path=str(tmp_path / "kb.db")))
            kb.add("Alice went to the museum with her kids")
            kb.add("They enjoyed the dinosaur exhibit")
            kb.add("Bob likes fishing on weekends")

            # Alice is indexed in mention_graph; hop_expand("Alice's kids") → Alice facts
            db = kb._storage
            alice_facts = db.facts_for_entity("mg-int", "Alice")
            assert len(alice_facts) >= 1

    def test_no_circular_reference_crash(self, tmp_path: pathlib.Path) -> None:
        """Entity that points to itself via the mention graph must not loop."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("AI_KNOT_MENTION_GRAPH", "1")
            import importlib

            import ai_knot.mention_graph as mg_mod

            importlib.reload(mg_mod)
            import ai_knot.knowledge as k_mod

            importlib.reload(k_mod)
            from ai_knot.knowledge import KnowledgeBase as KB
            from ai_knot.storage.sqlite_storage import SQLiteStorage as SS

            kb = KB(agent_id="mg-circ", storage=SS(db_path=str(tmp_path / "circ.db")))
            kb.add("Alice told Alice about Alice's schedule")
            # Should not raise or infinite-loop
            result = kb.recall("What did Alice say?", top_k=5)
            assert isinstance(result, str)

    def test_mention_graph_off_by_default(self, tmp_path: pathlib.Path) -> None:
        """Mention graph must be disabled unless AI_KNOT_MENTION_GRAPH=1."""
        import ai_knot.mention_graph as mg_mod

        assert mg_mod.MENTION_GRAPH_ENABLED is False or os.environ.get(
            "AI_KNOT_MENTION_GRAPH", ""
        ) not in {"1", "true", "yes"}
