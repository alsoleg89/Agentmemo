"""Tests for ProfileIndex — (entity, facet) in-memory index."""

from __future__ import annotations

import dataclasses

from ai_knot._profile_index import ProfileIndex
from ai_knot.types import Fact


def _fact(content: str, *, entity: str = "", attribute: str = "", value_text: str = "") -> Fact:
    return dataclasses.replace(
        Fact(content=content),
        entity=entity,
        attribute=attribute,
        value_text=value_text,
    )


class TestProfileIndexStructuredPath:
    def test_structured_fields_indexed(self) -> None:
        idx = ProfileIndex()
        f = _fact("Alice paints", entity="Alice", attribute="hobbies", value_text="painting")
        idx.index_fact(f)
        rows = idx.lookup("Alice", ["hobbies"])
        assert len(rows) == 1
        assert rows[0].entity == "Alice"
        assert rows[0].facet == "hobbies"
        assert rows[0].value_snippet == "painting"
        assert rows[0].fact_id == f.id

    def test_dedup_by_fact_id(self) -> None:
        idx = ProfileIndex()
        f = _fact("Alice paints", entity="Alice", attribute="art", value_text="painting")
        idx.index_fact(f)
        idx.index_fact(f)  # duplicate add
        rows = idx.lookup("Alice", ["art"])
        assert len(rows) == 1


class TestProfileIndexContentParsing:
    def test_observation_tagged_fact(self) -> None:
        idx = ProfileIndex()
        content = (
            "[2023-07-01] [source=observation session=session_1 evidence=direct]"
            " Melanie: Melanie enjoys running and yoga as hobbies."
        )
        f = _fact(content)
        idx.index_fact(f)
        rows = idx.lookup("Melanie", ["hobbies", "fitness"])
        assert len(rows) >= 1
        assert any(r.entity == "Melanie" for r in rows)

    def test_dated_turn_fact(self) -> None:
        idx = ProfileIndex()
        content = "[2023-08-15] Caroline: Caroline has two dogs and one cat as pets."
        f = _fact(content)
        idx.index_fact(f)
        rows = idx.lookup("Caroline", ["pets"])
        assert len(rows) >= 1

    def test_no_facet_detected_not_indexed(self) -> None:
        idx = ProfileIndex()
        content = "[2023-08-15] Bob: Bob said hello."
        f = _fact(content)
        idx.index_fact(f)
        rows = idx.lookup("Bob", ["hobbies"])
        assert rows == []

    def test_entity_fallback_lookup(self) -> None:
        """When facets don't match, entity-only fallback returns all rows."""
        idx = ProfileIndex()
        f = _fact(
            "[2023-01-01] Jon: Jon enjoys painting.",
            entity="Jon",
            attribute="art",
            value_text="painting",
        )
        idx.index_fact(f)
        # Lookup with non-matching facet but correct entity → fallback returns row
        rows = idx.lookup("Jon", ["cooking"])
        assert len(rows) >= 1

    def test_top_n_respected(self) -> None:
        idx = ProfileIndex()
        for i in range(15):
            f = _fact(
                f"[2023-0{(i % 9) + 1}-01] Alice: Alice loves painting.",
                entity="Alice",
                attribute="art",
                value_text=f"painting_{i}",
            )
            idx.index_fact(f)
        rows = idx.lookup("Alice", ["art"], top_n=5)
        assert len(rows) == 5
