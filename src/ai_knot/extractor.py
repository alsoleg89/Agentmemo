"""LLM-based fact extraction from conversations.

Supports any LLM provider via the :class:`LLMProvider` protocol.
The LLM is instructed to return structured JSON with extracted facts.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any, Literal

from ai_knot._similarity import tfidf_cosine
from ai_knot.providers import LLMProvider, call_with_retry, create_provider
from ai_knot.types import ConversationTurn, Fact, MemoryType

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM_PROMPT = """You are a knowledge extraction engine.
Given a conversation, extract ONLY meaningful facts worth remembering.

Rules:
- Skip greetings, thanks, filler ("ok", "got it", "thanks").
- Each fact must be a single, self-contained statement.
- Classify each fact as: semantic (about user/world), procedural (preferences/how-to),
  episodic (specific events).
- Rate importance from 0.0 to 1.0.

Return a JSON array. Example:
[
  {"content": "User works at Sber", "type": "semantic", "importance": 0.9},
  {"content": "User prefers Python over Java", "type": "procedural", "importance": 0.85}
]

If no meaningful facts exist, return an empty array: []
Return ONLY the JSON array, no other text."""

_VERBATIM_SYSTEM_PROMPT = """You are a knowledge extraction engine.
Given a conversation, extract ONLY meaningful facts worth remembering.

Rules:
- Skip greetings, thanks, filler ("ok", "got it", "thanks").
- Each fact must be a single, self-contained statement.
- VERBATIM mode: preserve EXACT numbers, character limits, deadlines, platform names,
  and specific constraints. Do NOT paraphrase or summarise specific values.
  Good: "Telegram: лонгриды до 4000 знаков, структурировать через подзаголовки H2/H3"
  Bad:  "использовать подзаголовки"
- Classify each fact as: semantic (about user/world), procedural (preferences/how-to),
  episodic (specific events).
- Rate importance from 0.0 to 1.0.

Return a JSON array. Example:
[
  {"content": "User works at Sber", "type": "semantic", "importance": 0.9},
  {
    "content": "Telegram: посты до 4000 знаков, подзаголовки H2/H3",
    "type": "procedural",
    "importance": 0.95
  }
]

If no meaningful facts exist, return an empty array: []
Return ONLY the JSON array, no other text."""


def deduplicate_facts(facts: list[Fact], *, threshold: float = 0.75) -> list[Fact]:
    """Remove near-duplicate facts by TF-IDF cosine similarity.

    Args:
        facts: List of facts to deduplicate.
        threshold: Similarity threshold above which facts are considered duplicates.
            Default 0.75 is tuned for TF-IDF cosine (was 0.8 for Jaccard).

    Returns:
        Deduplicated list, keeping the first occurrence.
    """
    if not facts:
        return []

    unique: list[Fact] = []
    for fact in facts:
        is_dup = False
        for existing in unique:
            if tfidf_cosine(fact.content, existing.content) >= threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(fact)
    return unique


def resolve_against_existing(
    new_facts: list[Fact],
    existing: list[Fact],
    *,
    threshold: float = 0.65,
) -> tuple[list[Fact], list[Fact]]:
    """Separate new facts into inserts and updates relative to existing facts.

    For each new fact, if a similar existing fact is found (TF-IDF cosine >=
    threshold), the existing fact is updated in-place: importance is bumped by
    0.05 (capped at 1.0) and ``last_accessed`` is set to UTC now. Otherwise the
    new fact is collected for insertion.

    Args:
        new_facts: Facts extracted from the latest conversation.
        existing: Facts already stored for this agent.
        threshold: TF-IDF cosine similarity threshold to consider two facts
            duplicates.  Default 0.65 (was 0.7 for Jaccard) catches more
            paraphrase-style duplicates.

    Returns:
        A 2-tuple ``(to_insert, updated_existing)`` where:
        - ``to_insert``: new facts with no match in existing.
        - ``updated_existing``: existing facts that were updated in place.
    """
    to_insert: list[Fact] = []
    updated: list[Fact] = []

    for new in new_facts:
        matched: Fact | None = None
        for old in existing:
            if tfidf_cosine(new.content, old.content) >= threshold:
                matched = old
                break
        if matched is not None:
            matched.importance = min(1.0, matched.importance + 0.05)
            matched.last_accessed = datetime.now(UTC)
            updated.append(matched)
        else:
            to_insert.append(new)

    return to_insert, updated


def _faithfulness_score(content: str, source_text: str) -> float:
    """Fraction of key words (>= 4 chars) from content found in source_text.

    A simple substring-match check that flags complete hallucinations while
    tolerating normal LLM reformulation (first→third person, word order changes).

    Args:
        content: The extracted fact content.
        source_text: Full concatenated text of source conversation turns.

    Returns:
        Score in [0.0, 1.0].  Returns 1.0 when no key words can be checked.
    """
    key_words = re.findall(r"[a-zA-Z\u0400-\u04FF]{4,}", content.lower())
    if not key_words:
        return 1.0
    source_lower = source_text.lower()
    found = sum(1 for w in key_words if w in source_lower)
    return found / len(key_words)


class Extractor:
    """Extract structured facts from conversations using an LLM.

    Args:
        provider: An LLM provider instance, or a provider name string.
            If a string, ``api_key`` is required.
        api_key: API key (used only when ``provider`` is a string).
        model: Model name (defaults to provider's default model).
        timeout: Per-request timeout in seconds. ``None`` uses the provider default.
        batch_size: Maximum number of conversation turns per LLM call. Long
            conversations are automatically split into chunks of this size and
            results are merged. Prevents JSON truncation on large inputs.
        extraction_detail: ``"compact"`` (default) — LLM summarises facts to their
            essence.  ``"verbatim"`` — LLM is instructed to preserve exact numbers,
            limits, platform names, and specific constraints without paraphrasing.
            Use ``"verbatim"`` for ToV rules, editorial guidelines, or any fact
            where specific values matter downstream.
        faithfulness_filter: When ``True``, each extracted fact is checked for
            token overlap with the source conversation.  Facts where fewer than
            20 % of key words (≥ 4 characters) appear in the source are marked
            ``low_confidence=True``.  Callers can then filter: ``[f for f in
            facts if not f.low_confidence]``.
    """

    def __init__(
        self,
        provider: LLMProvider | str = "openai",
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        batch_size: int = 20,
        extraction_detail: Literal["compact", "verbatim"] = "compact",
        faithfulness_filter: bool = False,
        **provider_kwargs: str,
    ) -> None:
        if isinstance(provider, str):
            self._provider = create_provider(provider, api_key, **provider_kwargs)
        else:
            self._provider = provider
        self._model = model or self._provider.default_model
        self._timeout = timeout
        self._batch_size = batch_size
        self._extraction_detail = extraction_detail
        self._faithfulness_filter = faithfulness_filter

    def extract(self, turns: list[ConversationTurn]) -> list[Fact]:
        """Extract facts from a conversation.

        Long conversations are automatically split into chunks of ``batch_size``
        turns so that the LLM never receives more than that at once, preventing
        silent fact loss due to JSON truncation.

        When ``faithfulness_filter=True`` was set at init, facts whose key words
        have less than 20 % overlap with the source text are marked
        ``low_confidence=True``.

        Args:
            turns: List of conversation messages.

        Returns:
            List of extracted Facts. Returns [] on any LLM error.
        """
        if not turns:
            return []

        all_raw: list[dict[str, Any]] = []
        for i in range(0, len(turns), self._batch_size):
            chunk = turns[i : i + self._batch_size]
            all_raw.extend(self._call_llm(chunk))

        facts = [self._parse_fact(entry) for entry in all_raw if isinstance(entry, dict)]
        facts = deduplicate_facts(facts)

        if self._faithfulness_filter and facts:
            source_text = " ".join(t.content for t in turns)
            for fact in facts:
                if _faithfulness_score(fact.content, source_text) < 0.2:
                    fact.low_confidence = True

        return facts

    def _call_llm(self, turns: list[ConversationTurn]) -> list[dict[str, Any]]:
        """Call the LLM to extract facts. Returns parsed JSON array."""
        system_prompt = (
            _VERBATIM_SYSTEM_PROMPT
            if self._extraction_detail == "verbatim"
            else _EXTRACTION_SYSTEM_PROMPT
        )
        conversation_text = "\n".join(f"{t.role}: {t.content}" for t in turns)
        content = call_with_retry(
            self._provider,
            system_prompt,
            conversation_text,
            self._model,
            timeout=self._timeout,
        )
        if not content:
            return []
        return self._parse_json_response(content)

    @staticmethod
    def _parse_json_response(content: str) -> list[dict[str, Any]]:
        """Parse a JSON array from LLM response, handling markdown fences."""
        content = content.strip()
        # Strip markdown code fences if present.
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            content = match.group(1)
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse LLM response as JSON: %s", content[:200])
        return []

    @staticmethod
    def _parse_fact(entry: dict[str, Any]) -> Fact:
        """Convert a raw dict from LLM output into a Fact."""
        memory_type = MemoryType.SEMANTIC
        raw_type = entry.get("type", "semantic")
        with contextlib.suppress(ValueError):
            memory_type = MemoryType(raw_type)

        # Clamp importance to valid range regardless of what LLM returned.
        importance = max(0.0, min(1.0, float(entry.get("importance", 0.8))))

        return Fact(
            content=str(entry.get("content", "")),
            type=memory_type,
            importance=importance,
        )
