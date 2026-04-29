"""Tests for ProfileIndex — (entity, facet) in-memory index."""

from __future__ import annotations

import dataclasses
import logging

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

    def test_no_match_without_facet(self) -> None:
        idx = ProfileIndex()
        content = "[2023-01-01] Alice: Alice went to the store."
        f = _fact(content)
        idx.index_fact(f)
        # No facet detected → nothing indexed
        rows = idx.lookup("Alice", ["hobbies"])
        assert rows == []


class TestProfileIndexB1SingleSpeakerGuard:
    """B1: ProfileIndex warns when multi-speaker window content is detected."""

    def test_multi_speaker_content_triggers_warning(
        self, caplog: logging.LogCaptureFixture
    ) -> None:
        idx = ProfileIndex()
        # Old 3-turn window format: multi-speaker joined with " / "
        content = (
            "[2023-05-10] Caroline: I love painting / "
            "Melanie: That's great! / Caroline: Yes, it's my main hobby."
        )
        f = _fact(content)
        with caplog.at_level(logging.WARNING, logger="ai_knot._profile_index"):
            idx.index_fact(f)
        assert any("multi-speaker" in rec.message for rec in caplog.records)

    def test_single_speaker_fact_no_warning(self, caplog: logging.LogCaptureFixture) -> None:
        idx = ProfileIndex()
        content = "[2023-05-10] Caroline: I love painting as a hobby."
        f = _fact(content)
        with caplog.at_level(logging.WARNING, logger="ai_knot._profile_index"):
            idx.index_fact(f)
        assert not any("multi-speaker" in rec.message for rec in caplog.records)
