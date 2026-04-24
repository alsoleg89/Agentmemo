"""Deterministic atomizer: RawEpisode → list[MemoryAtom].

No LOCOMO-specific patterns. No LLM calls.
All extraction is rule-based and reproducible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

from ai_knot_v2.core._ulid import new_ulid
from ai_knot_v2.core.atom import MemoryAtom
from ai_knot_v2.core.episode import RawEpisode
from ai_knot_v2.core.groupoid import EntityGroupoid, resolve_speaker_entity
from ai_knot_v2.core.risk import classify_risk
from ai_knot_v2.core.temporal import resolve_temporal


@dataclass(frozen=True, slots=True)
class ClauseCandidate:
    subject_raw: str
    predicate_raw: str
    object_raw: str | None
    polarity: Literal["pos", "neg"]
    temporal_expr: str | None
    source_span: tuple[int, int]


# ---------------------------------------------------------------------------
# Regex extraction patterns
# ---------------------------------------------------------------------------

_NEGATION = re.compile(
    r"\b(not|never|no|don't|doesn't|didn't|won't|isn't|aren't|wasn't|weren't|can't)\b", re.I
)

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Alice's salary is 120k  /  My job is engineering
    (
        "possession",
        re.compile(
            r"([\w\s]+?)'s\s+([\w\s]+?)\s+(is|are|was|were)\s+(not\s+)?([\w\s,.$€£\d]+)",
            re.I,
        ),
    ),
    # I work(s/ed) at/for Company
    (
        "work_at",
        re.compile(
            r"([\w\s]+?)\s+(work(?:s|ed|ing)?)\s+(?:at|for|in)\s+([\w\s&,.-]+)",
            re.I,
        ),
    ),
    # Alice lives/lived/moved in/to City
    (
        "location",
        re.compile(
            r"([\w\s]+?)\s+(live[sd]?s?|lives?|moved?|stay(?:s|ed)?|reside[sd]?)\s+(?:in|to|at|near|from)?\s*([\w\s,.-]+)",
            re.I,
        ),
    ),
    # I like/love/prefer/enjoy/hate X
    (
        "preference",
        re.compile(
            r"([\w\s]+?)\s+(like[sd]?|love[sd]?|prefer[sd]?|enjoy[sd]?|hate[sd]?|dislike[sd]?|adore[sd]?)\s+([\w\s,.!'-]+)",
            re.I,
        ),
    ),
    # Alice has/had a dog / I have a meeting
    (
        "has_obj",
        re.compile(
            r"([\w\s]+?)\s+(have|has|had)\s+(?:a\s+|an\s+|the\s+)?([\w\s]+)",
            re.I,
        ),
    ),
    # Alice is/was a doctor / I am tired
    (
        "copula",
        re.compile(
            r"([\w\s]+?)\s+(is|am|are|was|were)\s+(not\s+)?(?:a\s+|an\s+|the\s+)?([\w\s,.-]+)",
            re.I,
        ),
    ),
    # I earn/make/get X per (year|month|week)
    (
        "income",
        re.compile(
            r"([\w\s]+?)\s+(?:earn|make|get|make|receive[sd]?)\s+([\w\s$€£,.\d]+(?:per|a|each)\s+(?:year|month|week|day))",
            re.I,
        ),
    ),
]

_STRIP_RE = re.compile(r"[.!?,;:]+$")


def _clean(s: str) -> str:
    return _STRIP_RE.sub("", s).strip()


def _detect_polarity(group: str | None, surrounding: str) -> Literal["pos", "neg"]:
    if group and re.search(r"\bnot\b", group, re.I):
        return "neg"
    if _NEGATION.search(surrounding[:30]):
        return "neg"
    return "pos"


def _sentence_split(text: str) -> list[str]:
    """Rough sentence splitter (no NLTK dependency)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _extract_clauses(text: str) -> list[ClauseCandidate]:
    candidates: list[ClauseCandidate] = []
    seen_predicates: set[str] = set()

    for sent in _sentence_split(text):
        for pattern_name, pattern in _PATTERNS:
            for m in pattern.finditer(sent):
                if pattern_name == "possession":
                    subj = f"{_clean(m.group(1))}'s {_clean(m.group(2))}"
                    pred = m.group(3).lower()
                    neg_grp = m.group(4)
                    obj = _clean(m.group(5)) if (m.lastindex or 0) >= 5 else None
                    polarity = _detect_polarity(neg_grp, sent)
                elif pattern_name in ("work_at", "location", "preference", "income"):
                    subj = _clean(m.group(1))
                    pred = _clean(m.group(2)).lower()
                    obj = _clean(m.group(3)) if (m.lastindex or 0) >= 3 else None
                    polarity = _detect_polarity(None, sent)
                elif pattern_name == "has_obj":
                    subj = _clean(m.group(1))
                    pred = "has"
                    obj = _clean(m.group(3))
                    polarity = _detect_polarity(None, sent)
                elif pattern_name == "copula":
                    subj = _clean(m.group(1))
                    pred = "is"
                    neg_grp = m.group(3)
                    obj = _clean(m.group(4)) if (m.lastindex or 0) >= 4 else None
                    polarity = _detect_polarity(neg_grp, sent)
                else:
                    continue

                if not subj or not pred or not obj:
                    continue

                # Skip overly generic/trivial subjects
                if re.match(r"^(that|this|it|there|here)$", subj, re.I):
                    continue

                # Deduplicate within sentence
                key = f"{subj.lower()}:{pred}:{(obj or '').lower()}"
                if key in seen_predicates:
                    continue
                seen_predicates.add(key)

                span = (m.start(), m.end())
                candidates.append(
                    ClauseCandidate(
                        subject_raw=subj,
                        predicate_raw=pred,
                        object_raw=obj,
                        polarity=polarity,
                        temporal_expr=sent if sent != m.group(0) else None,
                        source_span=span,
                    )
                )

    return candidates


def _canonical_predicate(predicate_raw: str, pattern_name: str | None = None) -> str:
    """Normalize predicate to a snake_case canonical form."""
    p = predicate_raw.lower().strip()
    mapping = {
        "is": "is",
        "am": "is",
        "are": "is",
        "was": "is",
        "were": "is",
        "has": "has",
        "have": "has",
        "had": "has",
        "likes": "prefers",
        "like": "prefers",
        "loved": "prefers",
        "love": "prefers",
        "prefers": "prefers",
        "prefer": "prefers",
        "enjoyed": "prefers",
        "enjoy": "prefers",
        "hates": "dislikes",
        "hate": "dislikes",
        "dislikes": "dislikes",
        "dislike": "dislikes",
        "works": "works_at",
        "work": "works_at",
        "worked": "works_at",
        "lives": "lives_in",
        "live": "lives_in",
        "lived": "lives_in",
        "moved": "moved_to",
    }
    return mapping.get(p, re.sub(r"[^a-z0-9_]", "_", p))


class Atomizer:
    """Converts RawEpisode objects into MemoryAtom lists."""

    def __init__(self, groupoid: EntityGroupoid | None = None) -> None:
        self._groupoid = groupoid or EntityGroupoid()

    def atomize(
        self,
        episode: RawEpisode,
        session_date: date,
    ) -> list[MemoryAtom]:
        """Extract MemoryAtom list from a single episode."""
        speaker_orbit = resolve_speaker_entity(episode.speaker, episode.user_id, episode.agent_id)
        clauses = _extract_clauses(episode.text)
        atoms: list[MemoryAtom] = []

        for clause in clauses:
            # Entity resolution: first-person → speaker orbit
            subj_raw = clause.subject_raw
            if re.match(r"^(i|me|my|mine|myself)$", subj_raw, re.I):
                entity_orbit_id = speaker_orbit
                subject = episode.user_id or episode.agent_id
            else:
                subject = subj_raw
                entity_orbit_id = self._groupoid.resolve(subj_raw)

            # Temporal resolution
            source_text = clause.temporal_expr or episode.text
            valid_from, valid_until, granularity = resolve_temporal(source_text, session_date)

            # Canonical predicate
            canon_pred = _canonical_predicate(clause.predicate_raw)

            # Risk classification — include subject for better context
            risk_class, risk_severity = classify_risk(
                f"{subject.lower()} {canon_pred}", clause.object_raw
            )

            # Protection energy heuristic: high-risk facts get higher initial energy
            protection_energy = min(1.0, risk_severity * 2.0)

            # Regret charge: risk × irreducibility (Sprint 1 placeholder: 1.0)
            regret_charge = risk_severity * 1.0

            atoms.append(
                MemoryAtom(
                    atom_id=new_ulid(),
                    agent_id=episode.agent_id,
                    user_id=episode.user_id,
                    variables=(subject.lower().replace(" ", "_"),),
                    causal_graph=(),
                    kernel_kind="point",
                    kernel_payload={},
                    intervention_domain=(subject.lower().replace(" ", "_"),),
                    predicate=canon_pred,
                    subject=subject,
                    object_value=clause.object_raw,
                    polarity=clause.polarity,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    observation_time=episode.timestamp,
                    belief_time=episode.timestamp,
                    granularity=granularity,  # type: ignore[arg-type]
                    entity_orbit_id=entity_orbit_id,
                    transport_provenance=(episode.session_id,),
                    depends_on=(),
                    depended_by=(),
                    risk_class=risk_class,
                    risk_severity=risk_severity,
                    regret_charge=regret_charge,
                    irreducibility_score=1.0,
                    protection_energy=protection_energy,
                    action_affect_mask=0,
                    credence=0.9,
                    evidence_episodes=(episode.episode_id,),
                    synthesis_method="regex",
                    validation_tests=(),
                    contradiction_events=(),
                )
            )

        return atoms
