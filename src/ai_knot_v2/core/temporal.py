"""Allen interval algebra (13 relations) and temporal utilities.

All relations are between closed intervals [start, end] where start ≤ end.
Epoch-seconds throughout.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from enum import Enum


class AllenRelation(Enum):
    PRECEDES = "precedes"  # A entirely before B
    MEETS = "meets"  # A ends exactly where B starts
    OVERLAPS = "overlaps"  # A starts before B, overlaps
    FINISHED_BY = "finished_by"  # B finishes inside A
    CONTAINS = "contains"  # B inside A
    STARTS = "starts"  # A starts at same time as B, ends earlier
    EQUALS = "equals"  # A == B
    STARTED_BY = "started_by"  # B starts inside A, A ends first
    DURING = "during"  # A inside B
    FINISHES = "finishes"  # A finishes at same time as B
    OVERLAPPED_BY = "overlapped_by"  # B starts before A, overlaps
    MET_BY = "met_by"  # B ends exactly where A starts
    PRECEDED_BY = "preceded_by"  # A entirely after B


def allen_relation(a_start: int, a_end: int, b_start: int, b_end: int) -> AllenRelation:
    """Compute the Allen relation of interval A relative to interval B."""
    if a_end < b_start:
        return AllenRelation.PRECEDES
    if a_end == b_start:
        return AllenRelation.MEETS
    if a_start < b_start and a_end < b_end and a_end > b_start:
        return AllenRelation.OVERLAPS
    if a_start < b_start and a_end == b_end:
        return AllenRelation.FINISHED_BY
    if a_start < b_start and a_end > b_end:
        return AllenRelation.CONTAINS
    if a_start == b_start and a_end < b_end:
        return AllenRelation.STARTS
    if a_start == b_start and a_end == b_end:
        return AllenRelation.EQUALS
    if a_start == b_start and a_end > b_end:
        return AllenRelation.STARTED_BY
    if a_start > b_start and a_end < b_end:
        return AllenRelation.DURING
    if a_start > b_start and a_end == b_end:
        return AllenRelation.FINISHES
    if a_start > b_start and a_start < b_end and a_end > b_end:
        return AllenRelation.OVERLAPPED_BY
    if a_start == b_end:
        return AllenRelation.MET_BY
    return AllenRelation.PRECEDED_BY


def interval_overlaps(a_start: int | None, a_end: int | None, query_time: int) -> bool:
    """Return True if query_time falls within [a_start, a_end] (open-ended if None)."""
    if a_start is not None and query_time < a_start:
        return False
    return not (a_end is not None and query_time > a_end)


# ---------------------------------------------------------------------------
# Relative-time expression resolution
# ---------------------------------------------------------------------------

_DAY_SEC = 86_400
_WEEK_SEC = 7 * _DAY_SEC
_MONTH_APPROX_SEC = 30 * _DAY_SEC

_RELATIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\byesterday\b", re.I), "yesterday"),
    (re.compile(r"\btoday\b", re.I), "today"),
    (re.compile(r"\btomorrow\b", re.I), "tomorrow"),
    (re.compile(r"\blast\s+week\b", re.I), "last_week"),
    (re.compile(r"\bthis\s+week\b", re.I), "this_week"),
    (re.compile(r"\bnext\s+week\b", re.I), "next_week"),
    (re.compile(r"\blast\s+month\b", re.I), "last_month"),
    (re.compile(r"\bthis\s+month\b", re.I), "this_month"),
    (re.compile(r"\blast\s+year\b", re.I), "last_year"),
    (re.compile(r"\bthis\s+year\b", re.I), "this_year"),
    (
        re.compile(
            r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I
        ),
        "next_weekday",
    ),
    (
        re.compile(
            r"\blast\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I
        ),
        "last_weekday",
    ),
    (re.compile(r"\b(\d+)\s+days?\s+ago\b", re.I), "n_days_ago"),
    (re.compile(r"\b(\d+)\s+weeks?\s+ago\b", re.I), "n_weeks_ago"),
    (re.compile(r"\b(\d+)\s+months?\s+ago\b", re.I), "n_months_ago"),
    (re.compile(r"\bin\s+(\d{4})\b", re.I), "year"),
    (
        re.compile(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)"
            r"(?:\s+(\d{4}))?\b",
            re.I,
        ),
        "month_year",
    ),
]

_MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _date_to_epoch(d: date) -> int:
    from datetime import UTC, datetime

    return int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp())


def resolve_temporal(text: str, session_date: date) -> tuple[int | None, int | None, str]:
    """Try to resolve a temporal expression from text.

    Returns (valid_from_epoch, valid_until_epoch, granularity).
    Returns (None, None, 'instant') if no expression found.
    """
    sd = session_date

    for pattern, key in _RELATIVE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue

        if key == "today":
            t = _date_to_epoch(sd)
            return t, t + _DAY_SEC - 1, "day"
        if key == "yesterday":
            d = sd - timedelta(days=1)
            t = _date_to_epoch(d)
            return t, t + _DAY_SEC - 1, "day"
        if key == "tomorrow":
            d = sd + timedelta(days=1)
            t = _date_to_epoch(d)
            return t, t + _DAY_SEC - 1, "day"
        if key == "last_week":
            monday = sd - timedelta(days=sd.weekday() + 7)
            t = _date_to_epoch(monday)
            return t, t + _WEEK_SEC - 1, "interval"
        if key == "this_week":
            monday = sd - timedelta(days=sd.weekday())
            t = _date_to_epoch(monday)
            return t, t + _WEEK_SEC - 1, "interval"
        if key == "next_week":
            monday = sd + timedelta(days=7 - sd.weekday())
            t = _date_to_epoch(monday)
            return t, t + _WEEK_SEC - 1, "interval"
        if key in ("last_month", "this_month"):
            if key == "last_month":
                d = date(sd.year - 1, 12, 1) if sd.month == 1 else date(sd.year, sd.month - 1, 1)
            else:
                d = date(sd.year, sd.month, 1)
            t = _date_to_epoch(d)
            return t, t + _MONTH_APPROX_SEC - 1, "month"
        if key == "last_year":
            t = _date_to_epoch(date(sd.year - 1, 1, 1))
            return t, _date_to_epoch(date(sd.year, 1, 1)) - 1, "year"
        if key == "this_year":
            t = _date_to_epoch(date(sd.year, 1, 1))
            return t, _date_to_epoch(date(sd.year + 1, 1, 1)) - 1, "year"
        if key == "n_days_ago":
            n = int(m.group(1))
            d = sd - timedelta(days=n)
            t = _date_to_epoch(d)
            return t, t + _DAY_SEC - 1, "day"
        if key == "n_weeks_ago":
            n = int(m.group(1))
            d = sd - timedelta(weeks=n)
            t = _date_to_epoch(d)
            return t, t + _WEEK_SEC - 1, "interval"
        if key == "n_months_ago":
            n = int(m.group(1))
            month = sd.month - n
            year = sd.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            d = date(year, month, 1)
            t = _date_to_epoch(d)
            return t, t + _MONTH_APPROX_SEC - 1, "month"
        if key == "year":
            y = int(m.group(1))
            t = _date_to_epoch(date(y, 1, 1))
            return t, _date_to_epoch(date(y + 1, 1, 1)) - 1, "year"
        if key == "month_year":
            month_name = m.group(1).lower()
            month_num = _MONTH_NAMES.get(month_name, 1)
            year_str = m.group(2)
            year_num = int(year_str) if year_str else sd.year
            d = date(year_num, month_num, 1)
            t = _date_to_epoch(d)
            return t, t + _MONTH_APPROX_SEC - 1, "month"

    return None, None, "instant"
