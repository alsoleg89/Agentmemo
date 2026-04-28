"""Canonical surface enrichment for Fact objects.

Appends normalized vocabulary tokens to fact.canonical_surface so BM25F
can bridge vocabulary gaps between stored facts and query terms.

All lexicons use generic English vocabulary — no proper nouns, no dataset-
specific values.  Each lexicon is a frozen module; changes require an oracle
re-pass before production use.

Activated by AI_KNOT_NORMALIZERS=1 (env flag, default OFF).
"""

from __future__ import annotations

from ai_knot._purpose_lexicon import STEM_TO_PURPOSE
from ai_knot._routine_lexicon import STEM_TO_ROUTINE
from ai_knot._visual_object_lexicon import STEM_TO_OBJECT
from ai_knot.types import Fact

_ALL_LEXICONS: tuple[dict[str, str], ...] = (
    STEM_TO_PURPOSE,
    STEM_TO_OBJECT,
    STEM_TO_ROUTINE,
)


def _collect_canonical_terms(text: str) -> list[str]:
    """Return canonical labels detected in *text* across all lexicons."""
    low = text.lower()
    found: set[str] = set()
    for lexicon in _ALL_LEXICONS:
        for stem, label in lexicon.items():
            if stem in low:
                found.add(label)
    return sorted(found)


def enrich_canonical_surface(fact: Fact) -> Fact:
    """Append normalized vocabulary tokens to fact.canonical_surface in-place.

    Scans fact.content (and existing canonical_surface) for known stems from
    the purpose, visual-object, and routine lexicons.  Detected labels are
    appended to canonical_surface so BM25F retrieval can match queries that
    use the canonical forms.

    Returns the same Fact object (modified in place).
    """
    if not fact.content:
        return fact

    sources = [fact.content]
    if fact.canonical_surface:
        sources.append(fact.canonical_surface)

    terms = _collect_canonical_terms(" ".join(sources))
    if not terms:
        return fact

    new_terms = " ".join(terms)
    if fact.canonical_surface:
        fact.canonical_surface = f"{fact.canonical_surface} {new_terms}"
    else:
        fact.canonical_surface = new_terms

    return fact
