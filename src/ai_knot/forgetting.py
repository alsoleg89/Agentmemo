"""Ebbinghaus forgetting curve implementation.

Core formula:
    retention(t) = (1 + t / (c * S))^(-decay_exponent)
    S = BASE_STABILITY_HOURS * importance * type_mult * count_factor * spacing_factor

FSRS-inspired spacing effect (Ye, 2022-2024): well-spaced accesses
give stronger reinforcement than cramped ones.

Type-aware decay (Tulving, 1972): episodic memory fades fastest,
semantic slowest.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from ai_knot.types import CONFLICT_POLICIES, Fact, MemoryType

# Base stability in hours (2 weeks). A fact with importance=1.0 and
# access_count=0 will retain ~37% after 2 weeks.
BASE_STABILITY_HOURS: float = 336.0

_POWER_LAW_FACTOR: float = 9.0

# FSRS-inspired type-aware decay exponents (Ye, 2022-2024).
# In FSRS these are trainable per-item; here we use fixed per-type values
# calibrated to Tulving (1972): episodic memory decays fastest,
# semantic knowledge persists longest.
_TYPE_DECAY_EXPONENT: dict[str, float] = {
    "semantic": 0.8,  # core facts: slower power-law decay
    "procedural": 1.0,  # preferences/rules: baseline
    "episodic": 1.3,  # events: steeper decay curve
}
_DEFAULT_DECAY_EXPONENT: float = 1.0

# Tulving (1972): different memory types decay at different rates.
_TYPE_STABILITY_MULTIPLIER: dict[str, float] = {
    "semantic": 1.5,  # core facts persist longest (months)
    "procedural": 1.0,  # preferences/rules: baseline (weeks-months)
    "episodic": 0.5,  # events fade fastest (days-weeks)
}


def calculate_stability(
    importance: float,
    access_count: int,
    access_intervals: list[float] | None = None,
    memory_type: str = "semantic",
) -> float:
    """Compute how long a fact resists forgetting (in hours).

    FSRS-inspired: spaced repetition gives stronger reinforcement.
    Five accesses spread over a month > five accesses in one minute.

    Args:
        importance: Fact importance (0.0-1.0).
        access_count: Number of times the fact has been recalled.
        access_intervals: Hours between consecutive accesses.
        memory_type: Memory type for type-aware decay multiplier.

    Returns:
        Stability in hours. Higher = slower decay.
    """
    type_mult = _TYPE_STABILITY_MULTIPLIER.get(memory_type, 1.0)
    base = BASE_STABILITY_HOURS * importance * type_mult

    if access_count <= 0:
        return base

    # Logarithmic access count factor (unchanged)
    count_factor = 1.0 + math.log(1.0 + access_count)

    # Spacing factor: mean interval normalized to stability scale
    # Well-spaced accesses (mean interval > 24h) get bonus
    # Cramped accesses (mean interval < 1h) get penalty
    spacing_factor = 1.0
    if access_intervals and len(access_intervals) >= 1:
        mean_interval = sum(access_intervals) / len(access_intervals)
        # Logarithmic scaling: diminishing returns for very long intervals
        # 1h -> ~0.7, 24h -> ~1.0, 168h (1w) -> ~1.15, 720h (1mo) -> ~1.3
        spacing_factor = 0.7 + 0.3 * math.log(1.0 + mean_interval / 24.0)
        spacing_factor = max(spacing_factor, 0.5)  # floor

    return base * count_factor * spacing_factor


def calculate_retention(
    fact: Fact,
    *,
    now: datetime | None = None,
    type_exponents: dict[str, float] | None = None,
) -> float:
    """Compute current retention score for a fact.

    Uses a power-law forgetting curve (Wixted & Ebbesen, 1997):
        retention = (1 + t / (c * S)) ** -decay_exponent
    where t is hours since last access, S is stability, and c is
    _POWER_LAW_FACTOR.

    Args:
        fact: The fact to evaluate.
        now: Current time (defaults to UTC now).
        type_exponents: Optional per-type decay exponent overrides.
            When ``None``, uses the built-in defaults.

    Returns:
        Retention score between 0.0 and 1.0.
    """
    now = now or datetime.now(UTC)
    time_hours = (now - fact.last_accessed).total_seconds() / 3600.0

    if time_hours <= 0:
        return 1.0

    stability = calculate_stability(
        fact.importance, fact.access_count, fact.access_intervals, fact.type.value
    )
    if stability <= 0:
        return 0.0

    exponents = type_exponents or _TYPE_DECAY_EXPONENT
    decay_exp = exponents.get(fact.type.value, _DEFAULT_DECAY_EXPONENT)
    return float((1.0 + time_hours / (_POWER_LAW_FACTOR * stability)) ** (-decay_exp))


def apply_decay(
    facts: list[Fact],
    *,
    now: datetime | None = None,
    type_exponents: dict[str, float] | None = None,
) -> list[Fact]:
    """Update retention_score on all facts using the forgetting curve.

    This is a bulk operation — call it periodically or before recall.

    Args:
        facts: Facts to update (modified in place).
        now: Current time (defaults to UTC now).
        type_exponents: Optional per-type decay exponent overrides.
            When ``None``, uses the built-in defaults.

    Returns:
        The same list of facts with updated retention_score values.
    """
    now = now or datetime.now(UTC)
    for fact in facts:
        # ConflictPolicy: decay-immune facts (e.g. PROCEDURAL) keep retention=1.0.
        policy = CONFLICT_POLICIES.get(fact.type, CONFLICT_POLICIES[MemoryType.SEMANTIC])
        if policy.decay_immune(fact):
            fact.retention_score = 1.0
        else:
            fact.retention_score = calculate_retention(fact, now=now, type_exponents=type_exponents)
    return facts


# ---------------------------------------------------------------------------
# New-gen three-axis decay functions (Track A)
# ---------------------------------------------------------------------------


def calculate_truth_validity(
    valid_from: datetime,
    valid_until: datetime | None,
    *,
    now: datetime | None = None,
) -> float:
    """Compute truth validity for an AtomicClaim.

    Truth validity encodes the logical truth window of a claim:
    - Before ``valid_from``: always 0.0 (claim hasn't become true yet).
    - Within [valid_from, valid_until]: 1.0 (currently true).
    - After ``valid_until``: 0.0 (claim expired / superseded).
    - ``valid_until=None`` means indefinitely true → 1.0 as long as ``now >= valid_from``.

    This axis is NEVER decayed by the forgetting curve — it reflects logical
    supersession, not memory fading. Raw episodes are never archived by this axis.

    Args:
        valid_from: Timestamp when the claim became true.
        valid_until: Timestamp when the claim expired (None = still valid).
        now: Current time reference (defaults to UTC now).

    Returns:
        1.0 if the claim is currently valid, else 0.0.
    """
    now = now or datetime.now(UTC)
    if now < valid_from:
        return 0.0
    if valid_until is not None and now >= valid_until:
        return 0.0
    return 1.0


def calculate_salience(
    base_salience: float,
    *,
    valid_from: datetime,
    now: datetime | None = None,
    access_count: int = 0,
    importance: float = 1.0,
    memory_type: str = "semantic",
) -> float:
    """Compute current salience score for an AtomicClaim.

    Salience captures how *prominent* a claim is in working memory —
    separate from whether it is logically true (truth_validity).  It
    decays with time using the same Ebbinghaus curve as legacy facts,
    but is boosted by usage and dampened by low importance.

    This is the only axis that the forgetting scheduler updates periodically.
    Truth validity (supersession) and promotion weight (corroboration) are
    updated on ingest events, not on a timer.

    Args:
        base_salience: Starting salience at ingest time (usually 1.0).
        valid_from: Claim inception time — used as the "created at" anchor.
        now: Current time reference (defaults to UTC now).
        access_count: Number of times this claim has been retrieved.
        importance: Importance hint from the source episode (0.0–1.0).
        memory_type: One of "semantic", "procedural", "episodic".

    Returns:
        Salience in [0.0, 1.0].
    """
    now = now or datetime.now(UTC)
    time_hours = (now - valid_from).total_seconds() / 3600.0
    if time_hours <= 0:
        return min(base_salience, 1.0)

    stability = calculate_stability(
        importance=importance,
        access_count=access_count,
        memory_type=memory_type,
    )
    if stability <= 0:
        return 0.0

    exponent = _TYPE_DECAY_EXPONENT.get(memory_type, _DEFAULT_DECAY_EXPONENT)
    curve = float((1.0 + time_hours / (_POWER_LAW_FACTOR * stability)) ** (-exponent))
    return float(min(base_salience * curve, 1.0))


def calculate_promotion_weight(
    current_weight: float,
    *,
    corroboration_count: int = 0,
    contradiction_count: int = 0,
    age_days: float = 0.0,
) -> float:
    """Compute how strongly a claim should be promoted in bundle ranking.

    Promotion weight is a hysteresis-stabilized score that encodes:
    - Corroboration bonus: confirmed by multiple independent episodes.
    - Contradiction penalty: challenged by at least one conflicting claim.
    - Stability bonus: long-lived claims without contradiction are more trusted.

    Unlike salience (which decays continuously), promotion weight is only
    updated when new corroborating or conflicting evidence arrives.

    Args:
        current_weight: Existing promotion weight (0.0–2.0 range).
        corroboration_count: Number of independent episodes supporting this claim.
        contradiction_count: Number of episodes contradicting this claim.
        age_days: Days since the claim was last corroborated.

    Returns:
        Updated promotion weight (clamped to [0.0, 2.0]).
    """
    weight = current_weight

    # Corroboration adds diminishing-returns bonus.
    if corroboration_count > 0:
        weight += 0.1 * math.log1p(corroboration_count)

    # Contradiction subtracts linearly.
    weight -= 0.2 * contradiction_count

    # Stability bonus: every 30 days without contradiction adds a small boost.
    if contradiction_count == 0 and age_days > 0:
        stability_bonus = 0.05 * math.log1p(age_days / 30.0)
        weight += stability_bonus

    return float(max(0.0, min(weight, 2.0)))
