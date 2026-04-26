"""Tests: mention graph does not create infinite loops or circular expansions."""

from __future__ import annotations

import pathlib

from ai_knot.mention_graph import extract_entities, hop_expand


class TestNoCircularReference:
    def test_hop_expand_single_call_bounded(self, tmp_path: pathlib.Path) -> None:
        """hop_expand returns a finite set even when entity maps to many facts."""
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "circ.db"))
        # Alice mentioned in 100 facts
        for i in range(100):
            db.store_mention("agent1", "Alice", f"fact{i:03d}")

        result = hop_expand("What did Alice do?", "agent1", db)
        assert len(result) == 100  # exact count, not infinite

    def test_entity_in_query_and_fact_does_not_double_expand(self, tmp_path: pathlib.Path) -> None:
        """hop_expand is a single-hop only: does not recurse into returned facts."""
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "circ2.db"))
        db.store_mention("agent1", "Alice", "fact_alice")
        db.store_mention("agent1", "Bob", "fact_bob")
        # fact_alice also mentions Bob (would cause expansion if we recurse)
        db.store_mention("agent1", "Bob", "fact_alice")

        result = hop_expand("What did Alice do?", "agent1", db)
        # Should only expand Alice (query entity); Bob is not in query
        assert "fact_alice" in result
        assert "fact_bob" not in result

    def test_extract_entities_no_duplicate_cycles(self) -> None:
        """Repeated names in text produce exactly one entity entry."""
        text = "Alice Alice Alice went to meet Alice"
        entities = extract_entities(text)
        assert entities == ["Alice"]
