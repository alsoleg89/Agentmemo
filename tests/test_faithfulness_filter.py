"""Faithfulness filter — marks hallucinated facts as low_confidence=True.

Tests that:
1. Facts whose key words appear in source are marked low_confidence=False.
2. Facts with no source overlap are marked low_confidence=True.
3. faithfulness_filter=False (default) leaves all facts confident.
4. The filter does not drop facts — it only sets the flag.
"""

from __future__ import annotations

from unittest.mock import patch

from ai_knot.extractor import Extractor, _faithfulness_score
from ai_knot.types import ConversationTurn

_SOURCE_TURNS = [
    ConversationTurn(role="user", content="I deploy everything in Docker"),
    ConversationTurn(role="assistant", content="Got it, I'll use Docker examples"),
    ConversationTurn(role="user", content="I really hate async code, prefer sync"),
]


class TestFaithfulnessScore:
    """_faithfulness_score unit tests."""

    def test_grounded_fact_scores_high(self) -> None:
        # "deploy" and "docker" are in source
        score = _faithfulness_score("User deploys in Docker", "I deploy everything in Docker")
        assert score > 0.2

    def test_hallucinated_fact_scores_zero(self) -> None:
        # None of the key words appear in source
        score = _faithfulness_score(
            "User loves GraphQL federation", "I deploy everything in Docker"
        )
        assert score == 0.0

    def test_partial_overlap_intermediate_score(self) -> None:
        score = _faithfulness_score(
            "User uses Docker and Kubernetes", "I deploy everything in Docker"
        )
        assert 0.0 <= score <= 1.0

    def test_empty_content_returns_one(self) -> None:
        assert _faithfulness_score("", "some source text") == 1.0

    def test_short_words_ignored(self) -> None:
        # "in", "a", "is" are under 4 chars — not checked
        assert _faithfulness_score("in a is", "completely different text") == 1.0


class TestExtractorFaithfulnessFilter:
    """Extractor marks low_confidence when faithfulness_filter=True."""

    def test_filter_off_by_default_no_flagging(self) -> None:
        extractor = Extractor(api_key="fake", provider="openai")
        hallucinated_response = [
            {
                "content": "User loves GraphQL federation perfectly",
                "type": "semantic",
                "importance": 0.8,
            }
        ]
        with patch.object(extractor, "_call_llm", return_value=hallucinated_response):
            facts = extractor.extract(_SOURCE_TURNS)

        assert len(facts) == 1
        assert facts[0].low_confidence is False

    def test_hallucinated_fact_flagged_when_filter_on(self) -> None:
        extractor = Extractor(api_key="fake", provider="openai", faithfulness_filter=True)
        hallucinated_response = [
            {
                "content": "User loves GraphQL federation perfectly",
                "type": "semantic",
                "importance": 0.8,
            }
        ]
        with patch.object(extractor, "_call_llm", return_value=hallucinated_response):
            facts = extractor.extract(_SOURCE_TURNS)

        assert len(facts) == 1
        assert facts[0].low_confidence is True

    def test_grounded_fact_not_flagged_when_filter_on(self) -> None:
        extractor = Extractor(api_key="fake", provider="openai", faithfulness_filter=True)
        grounded_response = [
            {"content": "User deploys in Docker", "type": "semantic", "importance": 0.85}
        ]
        with patch.object(extractor, "_call_llm", return_value=grounded_response):
            facts = extractor.extract(_SOURCE_TURNS)

        assert len(facts) == 1
        assert facts[0].low_confidence is False

    def test_filter_does_not_remove_facts(self) -> None:
        """Facts are flagged, not dropped."""
        extractor = Extractor(api_key="fake", provider="openai", faithfulness_filter=True)
        mixed_response = [
            {"content": "User deploys in Docker", "type": "semantic", "importance": 0.85},
            {"content": "User loves quantum blockchain", "type": "semantic", "importance": 0.5},
        ]
        with patch.object(extractor, "_call_llm", return_value=mixed_response):
            facts = extractor.extract(_SOURCE_TURNS)

        assert len(facts) == 2
        confident = [f for f in facts if not f.low_confidence]
        flagged = [f for f in facts if f.low_confidence]
        assert len(confident) >= 1
        assert len(flagged) >= 1

    def test_empty_turns_returns_empty(self) -> None:
        extractor = Extractor(api_key="fake", provider="openai", faithfulness_filter=True)
        assert extractor.extract([]) == []
