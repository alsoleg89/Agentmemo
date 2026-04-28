"""Tests for K1 intent router (vocabulary-based, no LLM)."""

from __future__ import annotations

from ai_knot._k1_router import classify_k1


class TestClassifyK1:
    def test_what_hobbies_returns_entity_and_facet(self) -> None:
        result = classify_k1("What hobbies does Melanie have?")
        assert result is not None
        assert result.entity == "Melanie"
        assert "hobbies" in result.facets

    def test_list_activities_returns_query(self) -> None:
        result = classify_k1("List all activities Caroline enjoys.")
        assert result is not None
        assert result.entity == "Caroline"
        assert "activities" in result.facets

    def test_how_many_pets_returns_count_query(self) -> None:
        result = classify_k1("How many pets does Jon have?")
        assert result is not None
        assert result.entity == "Jon"
        assert "pets" in result.facets

    def test_when_question_returns_none(self) -> None:
        # Temporal single-answer → bypass K1
        assert classify_k1("When did Melanie start painting?") is None

    def test_why_question_returns_none(self) -> None:
        assert classify_k1("Why did Caroline move cities?") is None

    def test_did_question_returns_none(self) -> None:
        assert classify_k1("Did Jon mention his hobbies?") is None

    def test_no_entity_returns_none(self) -> None:
        assert classify_k1("What are the most common hobbies?") is None

    def test_no_facet_returns_none(self) -> None:
        # Entity present but no facet noun detected → bypass to avoid polluting context
        assert classify_k1("What did Caroline say at the meeting?") is None

    def test_what_did_temporal_returns_none(self) -> None:
        assert classify_k1("What did Melanie do at the beach?") is None

    def test_what_was_returns_none(self) -> None:
        assert classify_k1("What was Caroline's reaction to the news?") is None

    def test_what_are_opener_with_entity(self) -> None:
        result = classify_k1("What are Alice's interests?")
        assert result is not None
        assert result.entity == "Alice"
        assert "interests" in result.facets
