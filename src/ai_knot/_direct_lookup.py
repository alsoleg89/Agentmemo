"""Direct lookup: entity-filtered + cosine-ranked retrieval channel.

Controlled by AI_KNOT_DIRECT_LOOKUP env flag (default OFF).

Design decisions (from Phase 0 embedding audit, 2026-04-29):
- top-K per entity, NOT absolute threshold — Phase 0 showed gold/irr overlap
  in 0.38-0.55 range makes fixed threshold structurally fragile.
- Multi-entity: union of top-K per entity, dedup across entities.
- Substring match in content (not only Fact.entity field) — ~30% of facts
  have empty entity field due to upstream extraction gap.
"""

from __future__ import annotations

import re
from typing import Any

from ai_knot.types import Fact

_WH_SKIP: frozenset[str] = frozenset(
    {
        "What",
        "When",
        "Where",
        "Which",
        "Who",
        "Why",
        "How",
        "Did",
        "Does",
        "Has",
        "Have",
        "Was",
        "Were",
        "Are",
        "Do",
        "The",
        "Also",
        "Both",
        "Each",
        "They",
        "Their",
        "This",
        "That",
        "Some",
        "Most",
        "More",
        "Many",
        "All",
    }
)


def extract_all_entities(question: str) -> list[str]:
    """Extract all proper-noun entities from a question (generic, no hardcoded names)."""
    return sorted(set(re.findall(r"\b[A-Z][a-z]{2,}\b", question)) - _WH_SKIP)


class DirectLookup:
    """Entity-filtered + cosine-ranked retrieval.

    Returns top-K facts per named entity (per-entity, not cross-entity ranking),
    enabling list-style retrieval for cat1 enumeration questions without competing
    against the main RRF pack for slots.
    """

    def __init__(self, top_k: int = 8) -> None:
        self.top_k = top_k

    def lookup(
        self,
        query_vector: list[float],
        question: str,
        candidate_facts: list[Fact],
        dense_vectors: dict[str, list[float]],
    ) -> tuple[dict[str, list[Fact]], dict[str, Any]]:
        """Entity-filter then cosine-rank candidate facts.

        Args:
            query_vector: Embedding of the query (already computed by _embed_for_recall).
            question: Original question string (used for entity extraction).
            candidate_facts: All active non-episodic facts for this agent.
            dense_vectors: Fact-id → embedding vector (from DenseRetriever._vectors).

        Returns:
            per_entity: {entity_name: [Fact, ...]} ordered by score (top-K per entity).
            trace: Diagnostic dict with applied/entities/counts/top_k.
        """
        entities = extract_all_entities(question)
        if not entities:
            return {}, {
                "applied": False,
                "entities": [],
                "facts_per_entity": {},
                "top_k": self.top_k,
                "reason": "no_entity",
            }

        per_entity: dict[str, list[Fact]] = {}
        seen_ids: set[str] = set()

        for entity in entities:
            entity_lower = entity.lower()
            candidates = [f for f in candidate_facts if entity_lower in f.content.lower()]
            if not candidates:
                continue

            # Score by cosine similarity to query_vector (0.0 for unembedded facts).
            scored = sorted(
                candidates,
                key=lambda f: _cosine_from_map(query_vector, dense_vectors, f.id),
                reverse=True,
            )
            # Top-K per entity; dedup across entities (first entity wins).
            top = [f for f in scored if f.id not in seen_ids][: self.top_k]
            for f in top:
                seen_ids.add(f.id)
            if top:
                per_entity[entity] = top

        return per_entity, {
            "applied": bool(per_entity),
            "entities": entities,
            "facts_per_entity": {e: len(v) for e, v in per_entity.items()},
            "top_k": self.top_k,
        }


def _cosine_from_map(
    query_vec: list[float],
    dense_vectors: dict[str, list[float]],
    fact_id: str,
) -> float:
    fact_vec = dense_vectors.get(fact_id)
    if not fact_vec:
        return 0.0
    dot = 0.0
    nq = 0.0
    nf = 0.0
    for q, f in zip(query_vec, fact_vec, strict=False):
        dot += q * f
        nq += q * q
        nf += f * f
    denom = (nq**0.5) * (nf**0.5)
    return dot / denom if denom > 0 else 0.0
