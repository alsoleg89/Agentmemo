"""Temporal anchor helpers for dated-mode recall.

Pure functions: no side effects, no knowledge-base deps.
"""

from __future__ import annotations

import re
from calendar import month_name
from collections.abc import Callable
from datetime import datetime, timedelta

_DATE_PREFIX_RE = re.compile(r"\[(\d{1,2}\s+\w+,?\s*\d{4})\]")
_DATE_FORMATS = ["%d %B, %Y", "%d %B %Y", "%B %d, %Y", "%B %Y", "%Y"]

# Query tokens that signal a temporal question.
# "when" is only matched at question-start or after "did/was/is/will/has/have",
# not as a conjunction mid-sentence ("who supports X when Y happens").
_TEMPORAL_TOKENS = re.compile(
    r"(?:"
    r"^when\b"  # "When did..." at start
    r"|when\s+(?:did|was|is|will|has|have|does|do)\b"  # "when did/was/is..."
    r"|what\s+(?:date|day|year|month)\b"
    r"|which\s+day\b"
    r"|how\s+long\s+ago\b"
    r"|since\s+when\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_date(s: str) -> datetime | None:
    s = s.strip().replace(",", "")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _fmt_day(dt: datetime) -> str:
    return dt.strftime("%-d %B %Y")


def _fmt_month(dt: datetime, delta: int) -> str:
    m = dt.month + delta
    y = dt.year + (m - 1) // 12
    m = ((m - 1) % 12) + 1
    return f"{month_name[m]} {y}"


def is_temporal_query(query: str) -> bool:
    """Return True if query is asking about a date or time."""
    return bool(_TEMPORAL_TOKENS.search(query))


def extract_session_date(fact_lines: list[str]) -> datetime | None:
    """Return the first parseable date found in fact surface prefixes."""
    for line in fact_lines:
        m = _DATE_PREFIX_RE.search(line)
        if m:
            dt = _parse_date(m.group(1))
            if dt:
                return dt
    return None


def resolve_relative(text: str, session_dt: datetime) -> str:
    """Replace relative temporal phrases with absolute dates anchored to session_dt."""
    d = session_dt

    def _sub_fn(pattern: str, fn: Callable[..., str]) -> None:
        nonlocal text

        def _replacer(m: re.Match) -> str:  # type: ignore[type-arg]
            return str(fn(d, *m.groups()))

        text = re.sub(pattern, _replacer, text, flags=re.IGNORECASE)

    def _sub(pattern: str, repl: str) -> None:
        nonlocal text
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    # Longest patterns first. `(?!')` prevents matching possessives like "yesterday's".
    _sub_fn(r"\b(\d+)\s+days?\s+ago\b(?!')", lambda d, n: _fmt_day(d - timedelta(days=int(n))))
    _sub_fn(r"\b(\d+)\s+weeks?\s+ago\b(?!')", lambda d, n: _fmt_day(d - timedelta(weeks=int(n))))
    _sub_fn(r"\b(\d+)\s+months?\s+ago\b(?!')", lambda d, n: _fmt_month(d, -int(n)))
    _sub(r"\byesterday\b(?!')", _fmt_day(d - timedelta(days=1)))
    _sub(r"\btoday\b(?!')", _fmt_day(d))
    _sub(r"\btomorrow\b(?!')", _fmt_day(d + timedelta(days=1)))
    _sub(r"\blast\s+week\b(?!')", _fmt_day(d - timedelta(weeks=1)))
    _sub(r"\bnext\s+week\b(?!')", _fmt_day(d + timedelta(weeks=1)))
    _sub(r"\blast\s+month\b(?!')", _fmt_month(d, -1))
    _sub(r"\bnext\s+month\b(?!')", _fmt_month(d, +1))
    _sub(r"\bthis\s+month\b(?!')", _fmt_month(d, 0))
    _sub(r"\blast\s+year\b(?!')", str(d.year - 1))
    _sub(r"\bnext\s+year\b(?!')", str(d.year + 1))
    return text


def resolve_fact_line(line: str) -> str:
    """Resolve relative temporal phrases in a single recall fact line.

    Extracts the `[D Month, YYYY]` prefix from the line (dated-mode format),
    then replaces relative phrases like "yesterday" or "next month" with their
    absolute equivalents anchored to that session date.

    Lines without a date prefix are returned unchanged.
    """
    m = _DATE_PREFIX_RE.search(line)
    if not m:
        return line
    dt = _parse_date(m.group(1))
    if dt is None:
        return line
    return resolve_relative(line, dt)
