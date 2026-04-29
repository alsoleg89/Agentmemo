"""Regression tests for F1: kb.add() must populate entity/attribute/value_text/slot_key
from dated-turn content so that Channel C entity-hop and slot-exact retrieval work."""

from __future__ import annotations

import pathlib

import pytest

from ai_knot._profile_index import extract_entity_fields
from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.yaml_storage import YAMLStorage


@pytest.fixture
def kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    storage = YAMLStorage(base_dir=str(tmp_path))
    return KnowledgeBase(agent_id="f1_test", storage=storage)


class TestExtractEntityFields:
    def test_dated_turn_returns_fields(self) -> None:
        result = extract_entity_fields("[2023-05-10] Caroline: I love painting as a hobby.")
        assert result is not None
        entity, attribute, value_text, slot_key = result
        assert entity == "Caroline"
        assert attribute == "art"
        assert "painting" in value_text
        assert slot_key == "Caroline::art"

    def test_no_facet_returns_none(self) -> None:
        result = extract_entity_fields("[2023-05-10] Caroline: I went to the store.")
        assert result is None

    def test_multi_speaker_returns_none(self) -> None:
        content = "[2023-05-10] Caroline: I love painting / Melanie: Me too."
        assert extract_entity_fields(content) is None

    def test_plain_content_returns_none(self) -> None:
        assert extract_entity_fields("Some random fact without date prefix.") is None


class TestAddPopulatesStructuredFields:
    def test_dated_fact_gets_entity_field(self, kb: KnowledgeBase) -> None:
        fact = kb.add("[2023-05-10] Caroline: I love painting as a hobby.")
        assert fact.entity == "Caroline"
        assert fact.attribute == "art"
        assert fact.slot_key == "Caroline::art"
        assert "painting" in fact.value_text

    def test_plain_fact_entity_empty(self, kb: KnowledgeBase) -> None:
        fact = kb.add("Caroline went to the store.")
        assert fact.entity == ""
        assert fact.slot_key == ""

    def test_structured_fields_persisted_in_storage(self, kb: KnowledgeBase) -> None:
        kb.add("[2023-06-01] Alice: Alice enjoys reading books in her spare time.")
        stored = kb.list_facts()
        dated_fact = next(
            (f for f in stored if "Alice" in f.content and "reading" in f.content), None
        )
        assert dated_fact is not None
        assert dated_fact.entity == "Alice"
        assert dated_fact.attribute == "books"

    def test_entity_hop_fires_after_f1(self, kb: KnowledgeBase) -> None:
        """After F1 fix, Channel C entity-hop should connect value_text tokens to entities."""
        kb.add(
            "[2023-05-10] Alice: Alice works at the hospital as a doctor.",
        )
        kb.add("[2023-05-12] Bob: Bob loves hiking on weekends.")
        results = kb.recall_facts("hiking outdoors activities", top_k=5)
        assert any("hiking" in f.content.lower() for f in results)
