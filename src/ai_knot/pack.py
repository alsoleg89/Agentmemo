"""Evidence Pack V2 — Lost-in-the-Middle reorder with structured output.

Activated by setting AI_KNOT_PACK_V2=1.  When disabled the caller falls back
to the legacy flat rendering in knowledge.py::recall().
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_knot.types import Fact

PACK_V2_ENABLED: bool = os.environ.get("AI_KNOT_PACK_V2", "").strip() in {"1", "true", "yes"}

DEFAULT_TOKEN_BUDGET: int = 1500
# Rough chars-per-token approximation; used only for budget enforcement.
_CHARS_PER_TOKEN: int = 4


@dataclass
class EvidencePack:
    """Structured evidence pack returned by EvidencePackBuilder."""

    header: str
    raw_ribbons: list[str]
    what_we_dont_know: str | None
    fact_ids: list[str] = field(default_factory=list)

    def render(self) -> str:
        """Render as a flat numbered string for LLM prompt injection."""
        parts: list[str] = []
        if self.header:
            parts.append(self.header)
        for i, line in enumerate(self.raw_ribbons):
            parts.append(f"[{i + 1}] {line}")
        if self.what_we_dont_know:
            parts.append(f"\nNote: {self.what_we_dont_know}")
        return "\n".join(parts)


class EvidencePackBuilder:
    """Build a structured evidence pack with Lost-in-the-Middle reorder.

    Reorder schema (Liu et al. "Lost in the Middle", 2023):
        rank 1  → position 1   (head)
        rank 2  → position N   (tail)
        rank 3  → position 2
        rank 4  → position N-1
        ...

    High-relevance facts anchor both ends so the LLM attends to them;
    lower-relevance facts fill the middle where attention degrades.
    """

    def __init__(self, token_budget: int = DEFAULT_TOKEN_BUDGET) -> None:
        self._budget = token_budget

    def build(
        self,
        pairs: list[tuple[Fact, float]],
        *,
        intent: str = "FACTUAL",
        uncertainty_signal: bool | None = None,
    ) -> EvidencePack:
        """Build an EvidencePack from ranked (Fact, score) pairs.

        Args:
            pairs: Ranked facts, best-first.
            intent: Query intent string (FACTUAL, AGGREGATIONAL, etc.).
            uncertainty_signal: Override auto-detected uncertainty flag.
                                 If True, emit what_we_dont_know rail.
        """
        if not pairs:
            return EvidencePack(header="", raw_ribbons=[], what_we_dont_know=None, fact_ids=[])

        # Apply Lost-in-the-Middle reorder for evidence-sensitive intents.
        if intent in ("FACTUAL", "AGGREGATIONAL", "TEMPORAL", "NAVIGATIONAL"):
            reordered = self._litm_reorder(pairs)
        else:
            reordered = list(pairs)

        budgeted = self._apply_budget(reordered)

        ribbons: list[str] = []
        fact_ids: list[str] = []
        seen: set[str] = set()
        for f, _ in budgeted:
            text = f.prompt_surface or f.source_verbatim or f.content
            if f.entity and f.attribute:
                text = f"[{f.entity}: {f.attribute}={f.value_text}] {text}"
            if text not in seen:
                seen.add(text)
                ribbons.append(text)
                fact_ids.append(f.id)

        if uncertainty_signal is None:
            uncertainty_signal = self._detect_uncertainty(pairs, budgeted)

        wdnk: str | None = None
        if uncertainty_signal and ribbons:
            wdnk = (
                "The above may be incomplete — some relevant facts may not have been captured yet."
            )

        return EvidencePack(
            header="",
            raw_ribbons=ribbons,
            what_we_dont_know=wdnk,
            fact_ids=fact_ids,
        )

    @staticmethod
    def _litm_reorder(
        pairs: list[tuple[Fact, float]],
    ) -> list[tuple[Fact, float]]:
        """Interleave ranked pairs into head/tail positions.

        rank 1  → head (pos 0)
        rank 2  → tail (pos N-1)
        rank 3  → head+1 (pos 1)
        rank 4  → tail-1 (pos N-2)
        ...
        """
        if len(pairs) <= 2:
            return list(pairs)
        result: list[tuple[Fact, float] | None] = [None] * len(pairs)
        head = 0
        tail = len(pairs) - 1
        for rank_idx, pair in enumerate(pairs):
            if rank_idx % 2 == 0:
                result[head] = pair
                head += 1
            else:
                result[tail] = pair
                tail -= 1
        return [p for p in result if p is not None]

    def _apply_budget(
        self,
        pairs: list[tuple[Fact, float]],
    ) -> list[tuple[Fact, float]]:
        """Trim pairs to stay within the token budget."""
        char_budget = self._budget * _CHARS_PER_TOKEN
        out: list[tuple[Fact, float]] = []
        chars_used = 0
        for f, s in pairs:
            text = f.prompt_surface or f.source_verbatim or f.content or ""
            chars_used += len(text) + 6  # [N] prefix + space + newline
            if chars_used > char_budget and out:
                break
            out.append((f, s))
        return out

    @staticmethod
    def _detect_uncertainty(
        all_pairs: list[tuple[Fact, float]],
        budgeted: list[tuple[Fact, float]],
    ) -> bool:
        """Emit what_we_dont_know when the pack is sparse relative to what was ranked."""
        if not all_pairs:
            return False
        # Budget trimmed more than half the ranked facts → likely incomplete.
        return len(budgeted) < max(1, len(all_pairs) // 2)
