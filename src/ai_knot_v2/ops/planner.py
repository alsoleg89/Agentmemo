"""Evidence Planner — greedy-utility selection within a bounded reader budget.

Core principle: maximize density of correct evidence per token spent.
No broad-context widening. No LLM calls.

Key functions:
- reader_cost(atom)            — token cost estimate for rendering this atom
- reduction_score(atom, ...)   — expected regret reduction from adding atom
- utility(atom, ...)           — reduction_score / reader_cost
- plan_evidence_pack(...)      — greedy selection with dependency-closure
- handle_contradictions(pack)  — sheaf-curvature detection → split or abstain
"""

from __future__ import annotations

from typing import Any

from ai_knot_v2.core._ulid import new_ulid
from ai_knot_v2.core.action_calculus import compute_action_affect_mask
from ai_knot_v2.core.atom import MemoryAtom
from ai_knot_v2.core.library import AtomLibrary
from ai_knot_v2.core.types import EvidencePack, ReaderBudget

# ---------------------------------------------------------------------------
# Token cost estimation
# ---------------------------------------------------------------------------

_BASE_TOKENS_PER_ATOM = 12  # predicate + subject + object in short form
_TOKENS_PER_CHAR = 0.25  # rough approximation


def reader_cost(atom: MemoryAtom) -> int:
    """Estimate token cost to render this atom in a context window.

    Formula: base + len(subject) * factor + len(object) * factor.
    Returns at least 1 token.
    """
    subj_chars = len(atom.subject or "")
    obj_chars = len(atom.object_value or "")
    return max(1, _BASE_TOKENS_PER_ATOM + int((subj_chars + obj_chars) * _TOKENS_PER_CHAR))


# ---------------------------------------------------------------------------
# Reduction score (regret reduction heuristic)
# ---------------------------------------------------------------------------

_POLARITY_WEIGHT = {"pos": 1.0, "neg": 0.9}


def reduction_score(
    atom: MemoryAtom,
    query: str,
    current_pack: list[MemoryAtom],
) -> float:
    """Estimate how much adding this atom reduces expected answer regret.

    Heuristic components:
    1. Risk severity (high-risk facts reduce more regret when recalled)
    2. Text relevance (overlap of atom object/subject with query tokens)
    3. Action diversity (prefer atoms with new action coverage)
    4. Polarity correction (neg polarity slightly less confident)
    5. Credence weight
    6. Recency bias (more recent observations preferred)

    Returns score ∈ [0.0, ∞) (not normalized — higher is better).
    """
    score = 0.0

    # 1. Risk severity contribution
    score += atom.risk_severity * 2.0

    # 2. Text relevance
    q_words = {w.lower() for w in query.split() if len(w) > 3}
    obj_words = {w.lower() for w in (atom.object_value or "").split() if len(w) > 3}
    subj_words = {w.lower() for w in (atom.subject or "").split() if len(w) > 3}
    overlap = len(q_words & (obj_words | subj_words))
    score += overlap * 0.5

    # 3. Action diversity — reward covering new action bits
    if current_pack:
        current_coverage = 0
        for a in current_pack:
            current_coverage |= compute_action_affect_mask(a)
        atom_mask = compute_action_affect_mask(atom)
        new_bits = atom_mask & ~current_coverage
        score += bin(new_bits).count("1") * 0.3
    else:
        # First atom — full action coverage value
        atom_mask = compute_action_affect_mask(atom)
        score += bin(atom_mask).count("1") * 0.3

    # 4. Polarity weight
    score *= _POLARITY_WEIGHT.get(atom.polarity, 1.0)

    # 5. Credence weight
    score *= atom.credence

    # 6. Regret charge contribution (atoms with high regret_charge = more costly to omit)
    score += atom.regret_charge * 0.5

    return score


def utility(
    atom: MemoryAtom,
    query: str,
    current_pack: list[MemoryAtom],
) -> float:
    """Utility = reduction_score / reader_cost (information per token)."""
    cost = reader_cost(atom)
    return reduction_score(atom, query, current_pack) / cost


# ---------------------------------------------------------------------------
# Contradiction detection (sheaf curvature)
# ---------------------------------------------------------------------------

ContradictionPair = tuple[MemoryAtom, MemoryAtom]


def _atoms_contradict(a: MemoryAtom, b: MemoryAtom) -> bool:
    """Return True if two atoms assert contradictory claims about the same entity.

    Contradiction conditions (all must hold):
    1. Same entity orbit
    2. Same predicate
    3. Same subject (normalized)
    4. Different polarity OR different object_value for binary predicates
    """
    if a.entity_orbit_id != b.entity_orbit_id:
        return False
    if a.predicate != b.predicate:
        return False
    if (a.subject or "").lower() != (b.subject or "").lower():
        return False
    # Different polarity = direct contradiction
    if a.polarity != b.polarity:
        return True
    # Same polarity but different object on identity-type predicate = contradiction
    return a.predicate in ("is", "lives_in", "works_at") and a.object_value != b.object_value


def detect_contradictions(pack: list[MemoryAtom]) -> list[ContradictionPair]:
    """Return all pairs of contradicting atoms in pack."""
    pairs: list[ContradictionPair] = []
    for i, a in enumerate(pack):
        for b in pack[i + 1 :]:
            if _atoms_contradict(a, b):
                pairs.append((a, b))
    return pairs


def handle_contradictions(
    pack: list[MemoryAtom],
) -> tuple[list[MemoryAtom], list[str]]:
    """Apply sheaf-curvature contradiction resolution.

    Strategy:
    - For each contradicting pair: keep the higher-credence atom (split).
    - If credences are equal: remove both (safe-abstain).
    - Returns (resolved_pack, abstain_atom_ids).

    Never averages — always split or abstain.
    """
    contradictions = detect_contradictions(pack)
    if not contradictions:
        return pack, []

    remove_ids: set[str] = set()
    abstain_ids: list[str] = []

    for a, b in contradictions:
        if a.atom_id in remove_ids or b.atom_id in remove_ids:
            continue
        if a.credence > b.credence:
            remove_ids.add(b.atom_id)
        elif b.credence > a.credence:
            remove_ids.add(a.atom_id)
        else:
            # Equal credence → safe-abstain: remove both
            remove_ids.add(a.atom_id)
            remove_ids.add(b.atom_id)
            abstain_ids.extend([a.atom_id, b.atom_id])

    resolved = [a for a in pack if a.atom_id not in remove_ids]
    return resolved, abstain_ids


# ---------------------------------------------------------------------------
# Dependency closure within planner
# ---------------------------------------------------------------------------


def _close_dependencies(
    atoms: list[MemoryAtom],
    library: AtomLibrary,
    budget: ReaderBudget,
    token_budget: int,
) -> tuple[list[MemoryAtom], int]:
    """Add dependency atoms up to token budget. Returns (extended_list, tokens_used)."""
    atom_ids = {a.atom_id for a in atoms}
    result = list(atoms)
    tokens = token_budget

    for atom in list(atoms):
        for dep_id in atom.depends_on:
            if dep_id in atom_ids:
                continue
            dep = library.get(dep_id)
            if dep is None:
                continue
            cost = reader_cost(dep)
            if tokens - cost >= 0 and len(result) < budget.max_atoms:
                result.append(dep)
                atom_ids.add(dep_id)
                tokens -= cost

    return result, tokens


# ---------------------------------------------------------------------------
# Main: plan_evidence_pack
# ---------------------------------------------------------------------------


def plan_evidence_pack(
    atoms: list[MemoryAtom],
    query: str,
    budget: ReaderBudget,
    library: AtomLibrary | None = None,
) -> EvidencePack:
    """Greedy-utility selection within reader budget.

    1. Score all atoms by utility(atom, query, current_pack).
    2. Greedily select highest-utility atom within token budget.
    3. Repeat until budget exhausted or no atoms left.
    4. Apply dependency closure (if library provided).
    5. Handle contradictions (split or abstain).
    6. Return EvidencePack with utility_scores metadata.
    """
    if not atoms:
        return EvidencePack(pack_id=new_ulid(), atoms=(), spans=())

    token_budget = budget.max_tokens
    selected: list[MemoryAtom] = []
    remaining = list(atoms)
    utility_scores: dict[str, Any] = {}

    while remaining and len(selected) < budget.max_atoms and token_budget > 0:
        # Score all remaining atoms
        scored = [(utility(a, query, selected), a) for a in remaining]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_util, best_atom = scored[0]
        cost = reader_cost(best_atom)

        if cost > token_budget:
            # Skip if too expensive — try next
            skip_idx = next(
                (i for i, (_, a) in enumerate(scored) if reader_cost(a) <= token_budget),
                None,
            )
            if skip_idx is None:
                break
            best_util, best_atom = scored[skip_idx]
            cost = reader_cost(best_atom)

        selected.append(best_atom)
        utility_scores[best_atom.atom_id] = round(best_util, 4)
        token_budget -= cost
        remaining.remove(best_atom)

    # Dependency closure
    if library is not None and budget.require_dependency_closure:
        selected, _ = _close_dependencies(selected, library, budget, token_budget)

    # Contradiction resolution
    resolved, abstain_ids = handle_contradictions(selected)

    return EvidencePack(
        pack_id=new_ulid(),
        atoms=tuple(a.atom_id for a in resolved),
        spans=(),
        utility_scores={
            "atom_utilities": utility_scores,
            "abstain_atom_ids": abstain_ids,
            "tokens_used": budget.max_tokens - token_budget,
            "contradiction_count": len(abstain_ids) // 2,
        },
    )
