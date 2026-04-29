"""K1 intent router: vocabulary-based, no LLM calls.

Identifies profile/list/count questions and extracts (entity, facets)
for ProfileIndex lookup injection in recall().

Activated by AI_KNOT_K1_ROUTER=1 (env flag, default OFF).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Words that are NOT person-name entities even when capitalized
_NON_ENTITY: frozenset[str] = frozenset(
    {
        "what",
        "when",
        "where",
        "why",
        "who",
        "which",
        "how",
        "is",
        "are",
        "was",
        "were",
        "did",
        "do",
        "does",
        "has",
        "have",
        "had",
        "can",
        "could",
        "will",
        "would",
        "should",
        "may",
        "might",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "be",
        "been",
        "being",
        "it",
        "its",
        "he",
        "she",
        "they",
        "their",
        "them",
        "his",
        "her",
        "this",
        "that",
        "these",
        "those",
        "there",
        "name",
        "all",
        "any",
        "some",
        "many",
        "much",
        "more",
        "most",
        "list",
        "tell",
        "give",
        "mention",
        "describe",
    }
)

# Facet noun/verb stems mapped to canonical facet names.
# Must stay generic (no proper nouns, no dataset-specific values).
_FACET_STEMS: dict[str, str] = {
    "hobb": "hobbies",
    "interest": "interests",
    "activit": "activities",
    "passion": "interests",
    "pet": "pets",
    "animal": "pets",
    "sport": "sports",
    " book": "books",
    "read": "books",
    "paint": "art",
    " draw": "art",
    "pottery": "art",
    "ceramics": "art",
    "craft": "art",
    "music": "music",
    "sing": "music",
    "instrument": "music",
    " run": "fitness",
    "hike": "outdoor_activities",
    "climb": "outdoor_activities",
    "swim": "fitness",
    "yoga": "fitness",
    "exercis": "fitness",
    "cook": "cooking",
    " bak": "cooking",
    " job": "work",
    "career": "work",
    "famil": "family",
    " child": "family",
    " kid": "family",
    "goal": "goals",
    " plan": "plans",
    "event": "events",
    "visit": "places_visited",
    "travel": "places_visited",
    "language": "languages",
    "school": "education",
    "degree": "education",
    "prefer": "preferences",
    "favor": "preferences",
    "studio": "preferences",
    "stress": "stress_relief",
    "relax": "stress_relief",
    "destress": "stress_relief",
    "volunteer": "volunteering",
    "mentor": "mentoring",
    "teach": "teaching",
    "communit": "community",
}

# Single-answer question openers — bypass K1 routing entirely.
# Includes "what did/was/were" because those signal temporal/event questions
# even though they start with "what".
_SINGLE_RE = re.compile(
    r"^(?:when\b|why\b|how\s+did\b|how\s+was\b|how\s+has\b|how\s+have\b|"
    r"how\s+long\b|how\s+old\b|how\s+much\b|who\s+is\b|who\s+was\b|who\s+did\b|"
    r"did\b|was\b|were\b|is\b|are\s+you\b|do\s+you\b|which\b|"
    r"what\s+did\b|what\s+was\b|what\s+were\b|what\s+happened\b|what\s+made\b)",
    re.IGNORECASE,
)

# Profile/list/count openers that benefit from ProfileIndex injection
_PROFILE_RE = re.compile(
    r"^(?:what\b|list\b|name\s+all\b|how\s+many\b|what\s+are\b|what\s+were\b)",
    re.IGNORECASE,
)


@dataclass
class K1Query:
    """Parsed K1 intent: a person entity and candidate facets."""

    entity: str
    facets: list[str] = field(default_factory=list)


def _extract_entity(question: str) -> str:
    """Return the first capitalized word that looks like a person name."""
    for word in re.findall(r"[A-Z][a-zA-Z]+", question):
        if word.lower() not in _NON_ENTITY and len(word) > 2:
            return str(word)
    return ""


def _extract_facets(question: str) -> list[str]:
    """Return canonical facets detected in *question* via stem matching."""
    q = question.lower()
    found: set[str] = set()
    for stem, facet in _FACET_STEMS.items():
        if stem in q:
            found.add(facet)
    return sorted(found)


def classify_k1(question: str) -> K1Query | None:
    """Classify a question for K1 profile/list routing.

    Returns a :class:`K1Query` with entity + candidate facets when the
    question is a profile/list/count question about a named person.
    Returns ``None`` for temporal, causal, yes/no, and entity-free questions.
    """
    q = question.strip()

    if _SINGLE_RE.match(q):
        return None

    if not _PROFILE_RE.match(q):
        return None

    entity = _extract_entity(q)
    if not entity:
        return None

    facets = _extract_facets(q)
    if not facets:
        return None

    return K1Query(entity=entity, facets=facets)
