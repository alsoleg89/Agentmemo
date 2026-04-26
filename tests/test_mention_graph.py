"""Tests for mention_graph entity extraction and 1-hop expansion."""

from __future__ import annotations

import pathlib

from ai_knot.mention_graph import extract_entities, hop_expand, index_fact_entities


class TestExtractEntities:
    def test_extracts_person_names(self) -> None:
        text = "Caroline met Melanie at the coffee shop"
        entities = extract_entities(text)
        assert "Caroline" in entities
        assert "Melanie" in entities

    def test_skips_non_entity_capitals(self) -> None:
        text = "Thanks for the info! That sounds great, and yeah I agree."
        entities = extract_entities(text)
        assert not entities

    def test_skips_month_names(self) -> None:
        text = "[6 July, 2023] Caroline: Hey there!"
        entities = extract_entities(text)
        assert "July" not in entities
        assert "Caroline" in entities

    def test_deduplicates_repeated_names(self) -> None:
        text = "Alice talked to Alice about Alice's plans"
        entities = extract_entities(text)
        assert entities.count("Alice") == 1

    def test_min_length_three(self) -> None:
        # Single-char or two-char caps words should not appear
        text = "He went to NYC with Jo"
        entities = extract_entities(text)
        assert "He" not in entities
        assert "Jo" not in entities

    def test_empty_text(self) -> None:
        assert extract_entities("") == []

    def test_all_lowercase(self) -> None:
        assert extract_entities("no names here at all") == []


class TestMentionGraphStorage:
    def test_store_and_retrieve(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        db.store_mention("agent1", "Alice", "fact01", confidence=1.0)
        db.store_mention("agent1", "Alice", "fact02", confidence=0.9)
        db.store_mention("agent1", "Bob", "fact03", confidence=1.0)

        alice_facts = db.facts_for_entity("agent1", "Alice")
        assert set(alice_facts) == {"fact01", "fact02"}

        bob_facts = db.facts_for_entity("agent1", "Bob")
        assert bob_facts == ["fact03"]

    def test_cross_agent_isolation(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        db.store_mention("agent1", "Alice", "fact01")
        db.store_mention("agent2", "Alice", "fact99")

        assert db.facts_for_entity("agent1", "Alice") == ["fact01"]
        assert db.facts_for_entity("agent2", "Alice") == ["fact99"]

    def test_entities_for_fact(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        db.store_mention("agent1", "Alice", "fact01")
        db.store_mention("agent1", "Bob", "fact01")

        entities = db.entities_for_fact("agent1", "fact01")
        assert set(entities) == {"Alice", "Bob"}

    def test_unknown_entity_returns_empty(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        assert db.facts_for_entity("agent1", "NoSuch") == []

    def test_clear_mentions(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        db.store_mention("agent1", "Alice", "fact01")
        db.clear_mentions("agent1")
        assert db.facts_for_entity("agent1", "Alice") == []

    def test_idempotent_store(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        db.store_mention("agent1", "Alice", "fact01")
        db.store_mention("agent1", "Alice", "fact01")  # same row, no error
        assert len(db.facts_for_entity("agent1", "Alice")) == 1


class TestIndexFactEntities:
    def test_indexes_entities_in_sqlite(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        index_fact_entities("agent1", "abc123", "Caroline met Melanie at the park", db)

        assert "abc123" in db.facts_for_entity("agent1", "Caroline")
        assert "abc123" in db.facts_for_entity("agent1", "Melanie")

    def test_no_op_for_unsupported_backend(self) -> None:
        # YAMLStorage does not have store_mention; should not raise
        import tempfile

        from ai_knot.storage.yaml_storage import YAMLStorage

        with tempfile.TemporaryDirectory() as tmp:
            storage = YAMLStorage(base_dir=tmp)
            index_fact_entities("agent1", "abc123", "Alice was here", storage)


class TestHopExpand:
    def test_expands_query_entities(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        db.store_mention("agent1", "Melanie", "fact_mel_1")
        db.store_mention("agent1", "Melanie", "fact_mel_2")
        db.store_mention("agent1", "Caroline", "fact_car_1")

        fids = hop_expand("What does Melanie like?", "agent1", db)
        assert "fact_mel_1" in fids
        assert "fact_mel_2" in fids
        assert "fact_car_1" not in fids

    def test_no_op_for_yaml_backend(self) -> None:
        import tempfile

        from ai_knot.storage.yaml_storage import YAMLStorage

        with tempfile.TemporaryDirectory() as tmp:
            storage = YAMLStorage(base_dir=tmp)
            result = hop_expand("Alice's hobbies", "agent1", storage)
            assert result == set()

    def test_empty_query(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.storage.sqlite_storage import SQLiteStorage

        db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
        assert hop_expand("", "agent1", db) == set()
