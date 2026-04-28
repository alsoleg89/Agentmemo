"""In-memory profile index: (entity, facet) → cited fact rows.

Built incrementally during KnowledgeBase.add() when AI_KNOT_PROFILE_INDEX=1.
Lookup prepends cited rows as front-matter in recall() when AI_KNOT_K1_ROUTER=1
routes a question to a profile/list/count intent.

Values always cite source fact_id — no synthetic claims are generated.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from ai_knot.types import Fact, MemoryType

logger = logging.getLogger(__name__)

# [date] [source=observation|session_summary ...] Speaker: statement
_OBS_RE = re.compile(
    r"^\[[^\]]+\]\s+\[source=(?:observation|session_summary)[^\]]*\]\s+([A-Z][a-zA-Z]+):\s*(.+)$",
    re.DOTALL,
)
# [date] Speaker: statement  (raw / dated turns)
_DATED_RE = re.compile(
    r"^\[[^\]]+\]\s+([A-Z][a-zA-Z]+):\s*(.+)$",
    re.DOTALL,
)

# Multi-speaker detection: old 3-turn window join used " / Speaker: " separators.
_MULTI_SPEAKER_RE = re.compile(r"\s/\s[A-Z][a-zA-Z]+:\s")

# Verb/noun stems → canonical facet.  Generic English vocabulary, no proper nouns.
_STEM_TO_FACET: dict[str, str] = {
    # Activities / hobbies
    "hobb": "hobbies",
    "interest": "interests",
    "activit": "activities",
    "passion": "interests",
    # Pets / animals
    "pet": "pets",
    " dog": "pets",
    " cat": "pets",
    "horse": "pets",
    "rabbit": "pets",
    "hamster": "pets",
    # Art / creative
    "paint": "art",
    " draw": "art",
    "sketch": "art",
    "sculpt": "art",
    "pottery": "art",
    "ceramics": "art",
    "craft": "art",
    # Music
    "music": "music",
    "sing": "music",
    "guitar": "music",
    "piano": "music",
    "instrument": "music",
    # Sports / fitness
    "sport": "sports",
    " run": "fitness",
    "hike": "outdoor_activities",
    "hiking": "outdoor_activities",
    "climbing": "outdoor_activities",
    "swim": "fitness",
    "yoga": "fitness",
    "gym": "fitness",
    "exercis": "fitness",
    "fitness": "fitness",
    "marshal art": "fitness",
    # Books / reading
    " book": "books",
    "read": "books",
    "novel": "books",
    # Food / cooking
    "cook": "cooking",
    " bak": "cooking",
    "recipe": "cooking",
    # Work / career
    " job": "work",
    "career": "work",
    "profession": "work",
    # Family
    "famil": "family",
    "parent": "family",
    " child": "family",
    " kid": "family",
    "sibling": "family",
    # Goals / plans
    "goal": "goals",
    " plan": "plans",
    "dream": "goals",
    "aspir": "goals",
    # Events / places
    "event": "events",
    "visit": "places_visited",
    "travel": "places_visited",
    # Languages
    "language": "languages",
    "fluent": "languages",
    # Education
    "school": "education",
    "college": "education",
    "universit": "education",
    "degree": "education",
    # Preferences / style
    "prefer": "preferences",
    "favor": "preferences",
    "studio": "preferences",
    # Stress / coping
    "stress": "stress_relief",
    "relax": "stress_relief",
    " cope": "stress_relief",
    "destress": "stress_relief",
    # Volunteering / community
    "volunteer": "volunteering",
    "communit": "community",
    "mentor": "mentoring",
    "teach": "teaching",
}


def _detect_facets(text: str) -> list[str]:
    """Return canonical facets detected in *text* via stem matching."""
    found: set[str] = set()
    for stem, facet in _STEM_TO_FACET.items():
        if stem in text.lower():
            found.add(facet)
    return sorted(found)


def extract_entity_fields(content: str) -> tuple[str, str, str, str] | None:
    """Extract (entity, attribute, value_text, slot_key) from dated/observation content.

    Returns None when content doesn't match the dated or observation format,
    contains multi-speaker patterns, or has no detectable facets.
    Called from KnowledgeBase.add() to populate structured fields so that
    Channel C entity-hop and slot-exact retrieval work on raw/dated facts.
    """
    content = content.strip()
    m = _OBS_RE.match(content) or _DATED_RE.match(content)
    if not m:
        return None
    speaker = m.group(1)
    statement = m.group(2).strip()
    if _MULTI_SPEAKER_RE.search(statement):
        return None
    facets = _detect_facets(statement)
    if not facets:
        return None
    primary_facet = facets[0]
    return speaker, primary_facet, statement[:200], f"{speaker}::{primary_facet}"


@dataclass(frozen=True)
class ProfileRow:
    """One cited row returned by ProfileIndex.lookup()."""

    fact_id: str
    entity: str
    facet: str
    value_snippet: str


@dataclass
class ProfileIndex:
    """In-memory (entity_lower::facet_lower) → [ProfileRow] index.

    Thread-unsafe — designed for single-agent bench runs where all add()
    calls happen before any recall() calls.
    """

    _index: dict[str, list[ProfileRow]] = field(default_factory=dict)
    # entity_lower → list of ALL rows (for broad fallback lookup)
    _by_entity: dict[str, list[ProfileRow]] = field(default_factory=dict)

    @staticmethod
    def _key(entity: str, facet: str) -> str:
        return f"{entity.lower().strip()}::{facet.lower().strip()}"

    def _add_row(self, row: ProfileRow) -> None:
        key = self._key(row.entity, row.facet)
        self._index.setdefault(key, []).append(row)
        self._by_entity.setdefault(row.entity.lower(), []).append(row)

    def index_fact(self, fact: Fact) -> None:
        """Extract (entity, facet, value) tuples from *fact* and index them.

        Priority:
          1. Structured entity + attribute fields (learn-mode / CAS path).
          2. Observation / session_summary tagged content.
          3. Dated turn content (speaker attribution).
        """
        if fact.type not in (MemoryType.SEMANTIC,):
            return

        # Path A: structured fields already populated (learn / CAS path)
        if fact.entity and fact.attribute:
            self._add_row(
                ProfileRow(
                    fact_id=fact.id,
                    entity=fact.entity,
                    facet=fact.attribute,
                    value_snippet=fact.value_text or fact.content[:200],
                )
            )
            return

        # Path B: content-parsed (observation / dated turns)
        content = fact.content.strip()
        m = _OBS_RE.match(content) or _DATED_RE.match(content)
        if not m:
            return

        speaker = m.group(1)
        statement = m.group(2).strip()

        # B1 invariant: per-speaker ingest must produce single-speaker facts.
        # Log a warning when the old multi-speaker window format is detected.
        if _MULTI_SPEAKER_RE.search(statement):
            logger.warning(
                "ProfileIndex.index_fact: multi-speaker content detected in fact %s "
                "(content starts: %r). Expected single-speaker turn after A4-trimmed ingest.",
                fact.id,
                content[:80],
            )

        facets = _detect_facets(statement)
        if not facets:
            return

        for facet in facets:
            self._add_row(
                ProfileRow(
                    fact_id=fact.id,
                    entity=speaker,
                    facet=facet,
                    value_snippet=statement[:200],
                )
            )

    def lookup(self, entity: str, facets: list[str], top_n: int = 10) -> list[ProfileRow]:
        """Return up to *top_n* rows matching *entity* + any of *facets*.

        Falls back to all rows for *entity* when no facet-specific match found.
        Deduplicates by fact_id; preserves insertion order.
        """
        rows: list[ProfileRow] = []
        entity_lower = entity.lower().strip()

        for facet in facets:
            rows.extend(self._index.get(self._key(entity_lower, facet), []))

        # Partial entity name matching (first name in full-name key, etc.)
        if not rows:
            for ent_key, ent_rows in self._by_entity.items():
                if entity_lower in ent_key or ent_key in entity_lower:
                    rows.extend(ent_rows)

        # Facet-agnostic fallback: all rows for this entity
        if not rows:
            rows.extend(self._by_entity.get(entity_lower, []))

        seen: set[str] = set()
        deduped: list[ProfileRow] = []
        for row in rows:
            if row.fact_id not in seen:
                seen.add(row.fact_id)
                deduped.append(row)
        return deduped[:top_n]
