"""Ebbinghaus forgetting curve implementation.

Core formula:
    retention(t) = exp(-time_hours / stability)
    stability    = base_hours * importance * (1 + ln(1 + access_count))

High importance + frequently accessed = remembered for months.
Low importance + never accessed = forgotten in days.

The ``base_hours`` parameter controls how aggressively facts decay:
- ``48`` (default in KnowledgeBase): decay visible within a day
- ``336`` (conservative, ~2 weeks): slower forgetting curve
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from ai_knot.types import Fact

# Conservative preset — a fact with importance=1.0 and access_count=0
# retains ~37 % after 2 weeks.  Kept for backward compatibility.
BASE_STABILITY_HOURS: float = 336.0


def calculate_stability(
    importance: float, access_count: int, *, base_hours: float = BASE_STABILITY_HOURS
) -> float:
    """Compute how long a fact resists forgetting (in hours).

    Args:
        importance: Fact importance (0.0-1.0).
        access_count: Number of times the fact has been recalled.
        base_hours: Base stability constant in hours.  Defaults to
            BASE_STABILITY_HOURS (336 h ≈ 2 weeks).  Pass a smaller
            value for more aggressive forgetting.

    Returns:
        Stability in hours. Higher = slower decay.
    """
    return base_hours * importance * (1.0 + math.log(1.0 + access_count))


def calculate_retention(
    fact: Fact, *, now: datetime | None = None, base_hours: float = BASE_STABILITY_HOURS
) -> float:
    """Compute current retention score for a fact.

    Uses the Ebbinghaus exponential decay: retention = exp(-t / S)
    where t is hours since last access and S is stability.

    Args:
        fact: The fact to evaluate.
        now: Current time (defaults to UTC now).
        base_hours: Forwarded to :func:`calculate_stability`.

    Returns:
        Retention score between 0.0 and 1.0.
    """
    now = now or datetime.now(UTC)
    time_hours = (now - fact.last_accessed).total_seconds() / 3600.0

    if time_hours <= 0:
        return 1.0

    stability = calculate_stability(fact.importance, fact.access_count, base_hours=base_hours)
    if stability <= 0:
        return 0.0

    return math.exp(-time_hours / stability)


def apply_decay(
    facts: list[Fact], *, now: datetime | None = None, base_hours: float = BASE_STABILITY_HOURS
) -> list[Fact]:
    """Update retention_score on all facts using the forgetting curve.

    This is a bulk operation — call it periodically or before recall.

    Args:
        facts: Facts to update (modified in place).
        now: Current time (defaults to UTC now).
        base_hours: Forwarded to :func:`calculate_retention`.  Use a
            smaller value (e.g. 48) to make forgetting visible sooner.

    Returns:
        The same list of facts with updated retention_score values.
    """
    now = now or datetime.now(UTC)
    for fact in facts:
        fact.retention_score = calculate_retention(fact, now=now, base_hours=base_hours)
    return facts
