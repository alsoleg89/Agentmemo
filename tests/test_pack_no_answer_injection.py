"""Anti-overfit test: pack must never contain a final answer sentence.

Validates that EvidencePackBuilder only emits raw evidence facts, not
synthesized or inferred answers. This guards against accidentally encoding
the benchmark's gold answers into the pack format.
"""

from __future__ import annotations

import re

from ai_knot.pack import EvidencePackBuilder
from ai_knot.types import Fact

# Patterns that indicate a synthesized answer rather than raw evidence.
_ANSWER_PATTERNS = [
    # Declarative summary conclusions
    re.compile(r"\btherefore\b", re.IGNORECASE),
    re.compile(r"\bin conclusion\b", re.IGNORECASE),
    re.compile(r"\bthe answer is\b", re.IGNORECASE),
    re.compile(r"\bto summarize\b", re.IGNORECASE),
    re.compile(r"\bbased on the (above|evidence)\b", re.IGNORECASE),
]

# Synthetic "answer" texts that should never appear verbatim in pack ribbons.
_INJECTED_ANSWERS = [
    "The total is 42.",
    "Alice's favorite color is blue.",
    "The answer is Paris.",
    "In conclusion, Bob left on Monday.",
    "Therefore, the meeting was on Friday.",
]


def _make_fact(content: str, fact_id: str = "id01") -> Fact:
    return Fact(content=content, id=fact_id)


class TestNoAnswerInjection:
    def test_raw_evidence_passes(self) -> None:
        facts = [
            _make_fact("Alice said she likes the color blue", "id01"),
            _make_fact("Meeting was scheduled for Friday", "id02"),
            _make_fact("Bob mentioned he would leave Monday morning", "id03"),
        ]
        pairs = [(f, 1.0) for f in facts]
        pack = EvidencePackBuilder().build(pairs, intent="FACTUAL")
        rendered = pack.render()
        for pattern in _ANSWER_PATTERNS:
            assert not pattern.search(rendered), (
                f"Answer-injection pattern '{pattern.pattern}' found in pack: {rendered}"
            )

    def test_injected_answers_not_present(self) -> None:
        """Injected answer strings must not appear in pack ribbons."""
        for answer in _INJECTED_ANSWERS:
            fact = _make_fact(answer)
            pack = EvidencePackBuilder().build([(fact, 1.0)], intent="FACTUAL")
            # The pack ribbon is the raw fact text — this is expected to be present
            # because the pack stores verbatim facts.  What we verify is that
            # the pack itself does NOT ADD answer sentences beyond the raw facts.
            ribbon = pack.raw_ribbons[0] if pack.raw_ribbons else ""
            # ribbon should equal the raw fact text (no synthesis appended)
            assert ribbon == answer, (
                f"Pack modified fact content. Expected: {answer!r}, Got: {ribbon!r}"
            )

    def test_note_rail_is_hedging_not_answer(self) -> None:
        from ai_knot.types import Fact as F

        all_pairs = [(F(content="x" * 200, id=f"id{i}"), 1.0) for i in range(10)]
        pack = EvidencePackBuilder(token_budget=1).build(all_pairs, intent="FACTUAL")
        if pack.what_we_dont_know is not None:
            for pattern in _ANSWER_PATTERNS:
                assert not pattern.search(pack.what_we_dont_know), (
                    f"Answer pattern in what_we_dont_know: {pack.what_we_dont_know}"
                )

    def test_entity_attribute_prefix_not_answer(self) -> None:
        fact = Fact(
            content="Alice works at Acme Corp",
            id="id01",
            entity="Alice",
            attribute="employer",
            value_text="Acme Corp",
        )
        pack = EvidencePackBuilder().build([(fact, 1.0)], intent="FACTUAL")
        ribbon = pack.raw_ribbons[0] if pack.raw_ribbons else ""
        # entity:attribute prefix is structural metadata, not an inferred answer
        assert "Acme Corp" in ribbon
        for pattern in _ANSWER_PATTERNS:
            assert not pattern.search(ribbon)
