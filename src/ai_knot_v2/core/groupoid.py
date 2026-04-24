"""EntityGroupoid — entity identity and canonical orbit resolution.

Sprint 3: canonical string-based identity.
Sprint 3b+: holonomy detection for identity evolution.
"""

from __future__ import annotations

import re
import unicodedata


def _normalize_str(s: str) -> str:
    """Lowercase, strip articles, collapse whitespace, remove non-word chars."""
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = re.sub(r"\b(the|a|an)\b\s*", "", s)
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", "_", s.strip())


class EntityGroupoid:
    """Maps surface entity strings to canonical orbit IDs.

    Sprint 3: exact string matching after normalization.
    Sprint 3b: holonomy detection (detect identity loops / merges).
    """

    def __init__(self) -> None:
        self._orbits: dict[str, str] = {}  # normalized_form -> orbit_id

    def resolve(self, surface: str) -> str:
        """Return canonical orbit_id for the given surface form.

        Creates a new orbit if the surface has not been seen before.
        """
        norm = _normalize_str(surface)
        if norm not in self._orbits:
            self._orbits[norm] = f"entity:{norm}"
        return self._orbits[norm]

    def merge(self, surface_a: str, surface_b: str) -> str:
        """Declare that two surface forms refer to the same entity.

        Returns the canonical orbit_id (the one from surface_a wins).
        Sprint 3b: records holonomy edge; for now just aliases.
        """
        orbit_a = self.resolve(surface_a)
        norm_b = _normalize_str(surface_b)
        self._orbits[norm_b] = orbit_a
        return orbit_a

    def known_orbits(self) -> set[str]:
        return set(self._orbits.values())


def resolve_speaker_entity(speaker: str, user_id: str | None, agent_id: str) -> str:
    """Map first-person pronouns to the appropriate entity orbit."""
    if speaker == "user":
        return f"entity:{user_id}" if user_id else "entity:unknown_user"
    if speaker == "agent":
        return f"entity:{agent_id}"
    return "entity:system"


_FIRST_PERSON = re.compile(r"^(i|me|my|myself|mine|we|us|our|ours)$", re.I)
_THIRD_PERSON_MASC = re.compile(r"^(he|him|his|himself)$", re.I)
_THIRD_PERSON_FEM = re.compile(r"^(she|her|hers|herself)$", re.I)
_THIRD_PERSON_NEUT = re.compile(r"^(they|them|their|theirs|themselves|it|its|itself)$", re.I)


def pronoun_entity(pronoun: str, speaker_orbit: str, last_mentioned: str | None) -> str:
    """Resolve a pronoun to an entity orbit (best-effort, Sprint 3 level)."""
    if _FIRST_PERSON.match(pronoun):
        return speaker_orbit
    if _THIRD_PERSON_MASC.match(pronoun) or _THIRD_PERSON_FEM.match(pronoun):
        return last_mentioned or "entity:unknown"
    if _THIRD_PERSON_NEUT.match(pronoun):
        return last_mentioned or "entity:unknown"
    return "entity:unknown"
