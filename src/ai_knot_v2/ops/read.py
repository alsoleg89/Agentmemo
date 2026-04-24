"""READ operation: query → intervention → candidates → planner → RecallResult.

Pipeline: extract_intervention → select_candidates (submodular-greedy) →
          plan_evidence_pack (planner) → build RecallResult.

No LLM. All selection is deterministic rule-based.
"""

from __future__ import annotations

import re

from ai_knot_v2.core.action_calculus import (
    action_distance,
    canonical_action_signature,
    compute_action_affect_mask,
    predict_action,
)
from ai_knot_v2.core.action_taxonomy import ActionClass
from ai_knot_v2.core.atom import MemoryAtom
from ai_knot_v2.core.library import AtomLibrary
from ai_knot_v2.core.types import (
    Intervention,
    ReaderBudget,
    RecallResult,
)

# ---------------------------------------------------------------------------
# Default budget
# ---------------------------------------------------------------------------

DEFAULT_BUDGET = ReaderBudget(
    max_atoms=20,
    max_tokens=2000,
    require_dependency_closure=True,
)

# ---------------------------------------------------------------------------
# Intervention extraction
# ---------------------------------------------------------------------------

# Keyword → variable (causal do-calculus variable name)
_INTERVENTION_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bmedical|doctor|diagnosis|symptom|medication|treatment\b", re.I), "health"),
    (re.compile(r"\bschedule|appointment|meeting|event|calendar\b", re.I), "schedule"),
    (re.compile(r"\bprefer|like|enjoy|want|favorite|interest\b", re.I), "preference"),
    (re.compile(r"\bname|age|address|identity|lives|occupation\b", re.I), "identity"),
    (re.compile(r"\bsalary|income|budget|earn|money|finance\b", re.I), "finance"),
    (re.compile(r"\bpromise|commit|guarantee|agreement|contract\b", re.I), "commitment"),
    (re.compile(r"\bdanger|hazard|emergency|unsafe|accident\b", re.I), "safety"),
]


def extract_intervention(query: str) -> tuple[Intervention, ActionClass]:
    """Extract a do-calculus intervention variable and predicted action from a query.

    Returns (Intervention(variable, value), predicted_action_class).
    Intervention.value is the normalized query text.
    """
    q_lower = query.lower().strip()
    variable = "general"
    for pattern, var in _INTERVENTION_KEYWORDS:
        if pattern.search(q_lower):
            variable = var
            break

    # Build signature for action prediction (no atoms available here)

    sig = canonical_action_signature([], query)
    predicted = predict_action(sig)

    return Intervention(variable=variable, value=q_lower), predicted


# ---------------------------------------------------------------------------
# Candidate selection (submodular-greedy with action_distance diversity)
# ---------------------------------------------------------------------------

_MIN_DIVERSITY_EPSILON = 0.1  # Minimum action_distance to add a diverse atom

# ---------------------------------------------------------------------------
# Query preprocessing helpers
# ---------------------------------------------------------------------------

_STRIP_PUNCT = re.compile(r"[?.!,;:\"']+$")
_POSSESSIVE = re.compile(r"'s?$|s'$")


def _normalize_qword(w: str) -> str:
    """Strip trailing punctuation and possessives ('s / s') from a query word."""
    w = _STRIP_PUNCT.sub("", w)
    w = _POSSESSIVE.sub("", w)
    return w.lower()


# Words that look like proper nouns (capitalized) but are not entity names
_GRAMMAR_WORDS: frozenset[str] = frozenset(
    {
        "what",
        "where",
        "when",
        "who",
        "why",
        "how",
        "which",
        "did",
        "does",
        "is",
        "was",
        "were",
        "has",
        "had",
        "will",
        "would",
        "could",
        "should",
        "the",
        "this",
        "that",
        "their",
        "there",
        "these",
        "those",
        "then",
        "than",
        "they",
        "them",
        "tell",
        "give",
        "list",
        "show",
        "find",
        "describe",
        "explain",
        "do",
        "have",
        "be",
        "are",
        "can",
        "may",
        "must",
        "shall",
        "and",
        "but",
        "or",
        "not",
        "any",
        "all",
        "some",
        "few",
        "yes",
        "no",
        "very",
        "much",
        "many",
        "more",
        "most",
        "in",
        "on",
        "at",
        "to",
        "from",
        "with",
        "for",
        "about",
        "of",
        "by",
        "if",
        "as",
        "so",
        "up",
        "out",
        "into",
        "onto",
    }
)


_PRONOUNS: frozenset[str] = frozenset(
    {
        "i",
        "me",
        "my",
        "mine",
        "myself",
        "you",
        "your",
        "yours",
        "yourself",
        "he",
        "him",
        "his",
        "himself",
        "she",
        "her",
        "hers",
        "herself",
        "it",
        "its",
        "itself",
        "we",
        "us",
        "our",
        "ours",
        "ourselves",
        "they",
        "them",
        "their",
        "theirs",
        "themselves",
    }
)


def _extract_proper_nouns(query: str) -> list[str]:
    """Return normalized proper nouns from query, excluding grammar words.

    A proper noun is a token that starts uppercase and is not a known
    grammar or question word. Used for single-entity routing.
    """
    nouns = []
    for w in query.split():
        if not w or not w[0].isupper():
            continue
        norm = _normalize_qword(w)
        if len(norm) >= 3 and norm not in _GRAMMAR_WORDS:
            nouns.append(norm)
    return nouns


# Generic question-vocabulary → canonical predicate hints.
# Boosts atoms whose predicate matches a concept implied by the query word.
_SEMANTIC_HINTS: dict[str, list[str]] = {
    "job": ["works_at"],
    "work": ["works_at"],
    "career": ["works_at", "is"],
    "employer": ["works_at"],
    "company": ["works_at"],
    "occupation": ["works_at", "is"],
    "profession": ["works_at", "is"],
    "live": ["lives_in"],
    "lives": ["lives_in"],
    "home": ["lives_in"],
    "city": ["lives_in", "moved_to"],
    "town": ["lives_in"],
    "neighborhood": ["lives_in"],
    "sport": ["prefers"],
    "food": ["prefers"],
    "hobby": ["prefers"],
    "interest": ["prefers"],
    "activity": ["prefers"],
    "married": ["is"],
    "husband": ["has", "is"],
    "wife": ["has", "is"],
    "partner": ["has", "is"],
    "child": ["has"],
    "children": ["has"],
    "kid": ["has"],
    "kids": ["has"],
    "salary": ["has", "has_salary"],
    "income": ["has", "has_salary"],
    "earn": ["has_salary"],
    "degree": ["has", "is"],
    "school": ["attended", "has"],
    "study": ["studied", "has"],
    "health": ["has", "is"],
    "condition": ["has", "is"],
    "diagnosis": ["has", "is"],
    "pet": ["has"],
    "dog": ["has"],
    "cat": ["has"],
}


def select_candidates(
    library: AtomLibrary,
    intervention: Intervention,
    query: str,
    budget: ReaderBudget,
) -> list[MemoryAtom]:
    """Select atoms from library via submodular-greedy diversity selection.

    1. Score atoms by relevance to intervention variable (risk_class match).
    2. Greedily add atoms that maximize marginal utility (relevance + diversity).
    3. Stop when max_atoms reached.
    """
    # Map intervention variable → relevant risk classes
    _VAR_TO_RISK: dict[str, list[str]] = {
        "health": ["medical", "safety"],
        "schedule": ["scheduling", "commitment"],
        "preference": ["preference"],
        "identity": ["identity"],
        "finance": ["finance"],
        "commitment": ["commitment", "legal"],
        "safety": ["safety", "medical"],
        "general": [
            "medical",
            "scheduling",
            "preference",
            "identity",
            "finance",
            "commitment",
            "safety",
            "legal",
            "ambient",
        ],
    }

    relevant_risk = _VAR_TO_RISK.get(intervention.variable, ["ambient"])

    # Gather all atoms from library, score by risk class match
    all_atoms = library.all_atoms()
    if not all_atoms:
        return []

    # Normalize query words: strip possessives and trailing punctuation
    normalized_qwords = [_normalize_qword(w) for w in query.split() if _normalize_qword(w)]
    # Main overlap word set (4+ chars to avoid common stop words)
    words = {w for w in normalized_qwords if len(w) > 3}
    # Semantic predicate hints from all query words ≥ 3 chars
    hint_predicates: set[str] = set()
    for qw in normalized_qwords:
        if len(qw) >= 3 and qw in _SEMANTIC_HINTS:
            hint_predicates.update(_SEMANTIC_HINTS[qw])

    # Query words for subject matching: no length filter but strip pronouns.
    # Allows short proper names (Jim, Bob, Sam) to match; prevents false boost
    # from pronoun atoms (she, he) when query contains pronouns.
    words_nonpron = {w for w in normalized_qwords if w not in _PRONOUNS}

    scored: list[tuple[float, MemoryAtom]] = []
    for atom in all_atoms:
        base_score = 0.0
        if atom.risk_class in relevant_risk:
            base_score += 1.0
        # Text overlap bonus: subject, object, AND predicate.
        # Subject uses non-pronoun normalized words (catches short names like Jim).
        # Obj/pred use 4+ char words.
        obj = (atom.object_value or "").lower()
        subj = (atom.subject or "").lower()
        pred = atom.predicate.replace("_", " ")
        # Exclude pronoun subjects from subject matching (unresolved references)
        subj_nonpron = {w for w in subj.split() if w not in _PRONOUNS}
        obj_words = {w for w in obj.split() if len(w) > 3}
        pred_words = {w for w in pred.split() if len(w) > 3}
        overlap = len(words_nonpron & subj_nonpron) + len(words & (obj_words | pred_words))
        base_score += overlap * 0.3
        # Semantic hint: boost atoms whose predicate is implied by a query concept
        if atom.predicate in hint_predicates:
            base_score += 0.4
        # High-risk atoms get priority
        base_score += atom.risk_severity * 0.5
        scored.append((base_score, atom))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Submodular-greedy: add atoms with diversity constraint
    selected: list[MemoryAtom] = []
    selected_masks: list[int] = []
    selected_pred_obj: set[tuple[str, str | None]] = set()

    for _, atom in scored:
        if len(selected) >= budget.max_atoms:
            break

        atom_mask = compute_action_affect_mask(atom)

        if not selected:
            selected.append(atom)
            selected_masks.append(atom_mask)
            selected_pred_obj.add((atom.predicate, atom.object_value))
            continue

        # Compute minimum distance to already-selected atoms
        min_dist = min(action_distance(atom_mask, m) for m in selected_masks)

        # Distinct (predicate, object_value) pairs are genuinely different facts
        # even when action_affect_mask is identical (e.g. two lives_in atoms).
        distinct_content = (atom.predicate, atom.object_value) not in selected_pred_obj

        # Accept if diverse enough, ambient (mask=0), or carries distinct content
        if min_dist >= _MIN_DIVERSITY_EPSILON or atom_mask == 0 or distinct_content:
            selected.append(atom)
            selected_masks.append(atom_mask)
            selected_pred_obj.add((atom.predicate, atom.object_value))

    return selected


# ---------------------------------------------------------------------------
# Main recall function
# ---------------------------------------------------------------------------


def recall(
    query: str,
    library: AtomLibrary,
    budget: ReaderBudget | None = None,
) -> RecallResult:
    """Full read path: query → intervention → select → planner → RecallResult."""
    from ai_knot_v2.ops.planner import plan_evidence_pack

    if budget is None:
        budget = DEFAULT_BUDGET

    intervention, _action = extract_intervention(query)
    candidates = select_candidates(library, intervention, query, budget)

    # Evidence planner: greedy-utility selection with contradiction resolution
    pack = plan_evidence_pack(candidates, query, budget, library)

    # Resolve atom objects from pack (after planner may have filtered some)
    pack_atom_ids = set(pack.atoms)
    result_atoms = [a for a in candidates if a.atom_id in pack_atom_ids]

    return RecallResult(
        atoms=result_atoms,
        evidence_pack_id=pack.pack_id,
        intervention=intervention,
    )
