"""Verbatim extraction mode — LLM is instructed to preserve exact values.

Tests that:
1. extraction_detail="verbatim" selects the verbatim system prompt.
2. The verbatim prompt contains the key instruction keywords.
3. Extractor passes extraction_detail correctly to _call_llm.
4. KnowledgeBase.learn() forwards extraction_detail to Extractor.
"""

from __future__ import annotations

import pathlib
from unittest.mock import patch

from ai_knot.extractor import (
    _EXTRACTION_SYSTEM_PROMPT,
    _VERBATIM_SYSTEM_PROMPT,
    Extractor,
)
from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.yaml_storage import YAMLStorage
from ai_knot.types import ConversationTurn

_TOV_TURNS = [
    ConversationTurn(
        role="user",
        content="Telegram: лонгриды до 4000 знаков, структурировать через подзаголовки H2/H3",
    ),
    ConversationTurn(role="assistant", content="Понял, запомнил правило."),
]

_VERBATIM_FACT = {
    "content": "Telegram: лонгриды до 4000 знаков, структурировать через подзаголовки H2/H3",
    "type": "procedural",
    "importance": 0.95,
}

_COMPACT_FACT = {
    "content": "использовать подзаголовки",
    "type": "procedural",
    "importance": 0.7,
}


class TestVerbatimSystemPrompt:
    """The verbatim prompt contains the right instructions."""

    def test_verbatim_prompt_contains_verbatim_keyword(self) -> None:
        assert "VERBATIM" in _VERBATIM_SYSTEM_PROMPT

    def test_verbatim_prompt_preserves_numbers_instruction(self) -> None:
        lower = _VERBATIM_SYSTEM_PROMPT.lower()
        assert "numbers" in lower or "числ" in lower or "4000" in lower

    def test_compact_prompt_does_not_mention_verbatim(self) -> None:
        assert "VERBATIM" not in _EXTRACTION_SYSTEM_PROMPT

    def test_prompts_are_different(self) -> None:
        assert _VERBATIM_SYSTEM_PROMPT != _EXTRACTION_SYSTEM_PROMPT


class TestExtractorVerbatimMode:
    """Extractor selects the correct prompt based on extraction_detail."""

    def test_compact_extractor_uses_compact_prompt(self) -> None:
        extractor = Extractor(api_key="fake", provider="openai", extraction_detail="compact")
        calls: list[str] = []

        def fake_call_with_retry(
            provider: object,
            system_prompt: str,
            user_content: str,
            model: str,
            *,
            timeout: float | None = None,
        ) -> str:
            calls.append(system_prompt)
            return "[]"

        with patch("ai_knot.extractor.call_with_retry", side_effect=fake_call_with_retry):
            extractor.extract(_TOV_TURNS)

        assert len(calls) == 1
        assert calls[0] == _EXTRACTION_SYSTEM_PROMPT

    def test_verbatim_extractor_uses_verbatim_prompt(self) -> None:
        extractor = Extractor(api_key="fake", provider="openai", extraction_detail="verbatim")
        calls: list[str] = []

        def fake_call_with_retry(
            provider: object,
            system_prompt: str,
            user_content: str,
            model: str,
            *,
            timeout: float | None = None,
        ) -> str:
            calls.append(system_prompt)
            return "[]"

        with patch("ai_knot.extractor.call_with_retry", side_effect=fake_call_with_retry):
            extractor.extract(_TOV_TURNS)

        assert len(calls) == 1
        assert calls[0] == _VERBATIM_SYSTEM_PROMPT

    def test_verbatim_fact_content_preserved(self) -> None:
        """When LLM returns a verbatim fact, the content is stored as-is."""
        extractor = Extractor(api_key="fake", provider="openai", extraction_detail="verbatim")
        with patch.object(extractor, "_call_llm", return_value=[_VERBATIM_FACT]):
            facts = extractor.extract(_TOV_TURNS)

        assert len(facts) == 1
        assert "4000" in facts[0].content
        assert "H2" in facts[0].content or "H2/H3" in facts[0].content


class TestKnowledgeBaseVerbatimForwarding:
    """KnowledgeBase.learn() forwards extraction_detail to Extractor."""

    def test_learn_forwards_extraction_detail(self, tmp_path: pathlib.Path) -> None:
        storage = YAMLStorage(base_dir=str(tmp_path))
        kb = KnowledgeBase(agent_id="test", storage=storage, provider="openai", api_key="fake")

        captured: list[str] = []

        original_init = Extractor.__init__

        def patched_init(self: Extractor, *args: object, **kwargs: object) -> None:
            captured.append(str(kwargs.get("extraction_detail", "compact")))
            original_init(self, *args, **kwargs)  # type: ignore[call-arg]

        with (
            patch.object(Extractor, "__init__", patched_init),
            patch.object(Extractor, "extract", return_value=[]),
        ):
            kb.learn(_TOV_TURNS, extraction_detail="verbatim")

        assert "verbatim" in captured

    def test_compact_is_default(self, tmp_path: pathlib.Path) -> None:
        storage = YAMLStorage(base_dir=str(tmp_path))
        kb = KnowledgeBase(agent_id="test", storage=storage, provider="openai", api_key="fake")

        captured: list[str] = []

        original_init = Extractor.__init__

        def patched_init(self: Extractor, *args: object, **kwargs: object) -> None:
            captured.append(str(kwargs.get("extraction_detail", "compact")))
            original_init(self, *args, **kwargs)  # type: ignore[call-arg]

        with (
            patch.object(Extractor, "__init__", patched_init),
            patch.object(Extractor, "extract", return_value=[]),
        ):
            kb.learn(_TOV_TURNS)  # no extraction_detail → default "compact"

        assert "compact" in captured
