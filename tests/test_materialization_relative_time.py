"""Regression tests for Phase 1E: relative-time anchors + speaker-as-subject fallback.

Exercises `_RELATIVE_DATE_RE`, `_resolve_relative_date`, `_is_past_verb_opener`,
and the widened EVENT fallback path in `_extract_from_sentence`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ai_knot.materialization import (
    _RELATIVE_DATE_RE,
    MATERIALIZATION_VERSION,
    _is_past_verb_opener,
    _resolve_relative_date,
    materialize_episode,
)
from ai_knot.query_types import RawEpisode, make_episode_id

SESSION_DATE = datetime(2026, 4, 20, tzinfo=UTC)
NOW = datetime(2026, 4, 23, tzinfo=UTC)


def _mk_raw(text: str, turn_id: str = "t1") -> RawEpisode:
    eid = make_episode_id("agent-1", "sess-1", turn_id)
    return RawEpisode(
        id=eid,
        agent_id="agent-1",
        session_id="sess-1",
        turn_id=turn_id,
        speaker="user",
        observed_at=NOW,
        raw_text=text,
        session_date=SESSION_DATE,
    )


class TestRelativeDateRegex:
    def test_matches_yesterday(self) -> None:
        assert _RELATIVE_DATE_RE.search("Went hiking yesterday.")

    def test_matches_last_week(self) -> None:
        assert _RELATIVE_DATE_RE.search("Took a trip last week to Rome.")

    def test_matches_last_spring(self) -> None:
        assert _RELATIVE_DATE_RE.search("Painted last spring.")

    def test_matches_recently(self) -> None:
        m = _RELATIVE_DATE_RE.search("Recently I saw a movie.")
        assert m is not None
        assert m.group(0).lower() == "recently"

    def test_matches_days_ago(self) -> None:
        assert _RELATIVE_DATE_RE.search("Went hiking a few days ago.")

    def test_matches_last_friday(self) -> None:
        assert _RELATIVE_DATE_RE.search("Last Friday was fun.")

    def test_matches_this_morning(self) -> None:
        assert _RELATIVE_DATE_RE.search("This morning was peaceful.")

    def test_does_not_match_unrelated(self) -> None:
        assert not _RELATIVE_DATE_RE.search("The meeting went well.")
        assert not _RELATIVE_DATE_RE.search("I love pottery classes.")


class TestResolveRelativeDate:
    def test_yesterday(self) -> None:
        assert _resolve_relative_date("yesterday", SESSION_DATE) == SESSION_DATE - timedelta(days=1)

    def test_last_week(self) -> None:
        assert _resolve_relative_date("last week", SESSION_DATE) == SESSION_DATE - timedelta(days=7)

    def test_last_month(self) -> None:
        assert _resolve_relative_date("last month", SESSION_DATE) == SESSION_DATE - timedelta(
            days=30
        )

    def test_last_year(self) -> None:
        assert _resolve_relative_date("last year", SESSION_DATE) == SESSION_DATE - timedelta(
            days=365
        )

    def test_recently(self) -> None:
        assert _resolve_relative_date("recently", SESSION_DATE) == SESSION_DATE - timedelta(days=3)

    def test_few_days_ago(self) -> None:
        assert _resolve_relative_date("a few days ago", SESSION_DATE) == SESSION_DATE - timedelta(
            days=5
        )

    def test_last_friday(self) -> None:
        assert _resolve_relative_date("last friday", SESSION_DATE) == SESSION_DATE - timedelta(
            days=7
        )

    def test_unknown_returns_none(self) -> None:
        assert _resolve_relative_date("never", SESSION_DATE) is None

    def test_no_session_date_returns_none(self) -> None:
        assert _resolve_relative_date("yesterday", None) is None


class TestPastVerbOpener:
    def test_irregular_forms(self) -> None:
        for w in ("Took", "Went", "Saw", "Met", "Bought", "Made", "Had", "Did"):
            assert _is_past_verb_opener(w), w

    def test_regular_ed_suffix(self) -> None:
        for w in ("Painted", "Visited", "Walked", "Cooked"):
            assert _is_past_verb_opener(w), w

    def test_rejects_proper_names(self) -> None:
        # "Caroline" doesn't end in -ed and isn't in the irregular list.
        assert not _is_past_verb_opener("Caroline")
        assert not _is_past_verb_opener("Melanie")

    def test_rejects_sentence_starters(self) -> None:
        # Question/imperative openers must not be treated as past verbs.
        assert not _is_past_verb_opener("The")
        assert not _is_past_verb_opener("Are")
        assert not _is_past_verb_opener("Yeah")

    def test_rejects_empty(self) -> None:
        assert not _is_past_verb_opener("")
        assert not _is_past_verb_opener("   ")

    def test_strips_punctuation(self) -> None:
        assert _is_past_verb_opener("Took,")
        assert _is_past_verb_opener("Painted.")


class TestIntegration:
    def test_jon_rome_emits_event_with_speaker_subject(self) -> None:
        raw = _mk_raw(
            "Jon: Hey Gina, hope you're doing great! "
            "Still working on my biz. "
            "Took a short trip last week to Rome to clear my mind a little."
        )
        claims = materialize_episode(raw)
        event_claims = [c for c in claims if c.kind.value == "event"]
        assert len(event_claims) == 1
        c = event_claims[0]
        assert c.subject == "Jon"
        assert c.relation == "occurred"
        assert "Rome" in c.value_text
        assert c.qualifiers.get("date_token") == "last week"
        # session_date=2026-04-20, "last week" = -7d = 2026-04-13
        assert c.event_time is not None
        assert c.event_time.date() == (SESSION_DATE - timedelta(days=7)).date()

    def test_melanie_painting_yesterday(self) -> None:
        raw = _mk_raw("Melanie: Painted a sunset yesterday. It was so relaxing.", turn_id="t2")
        claims = materialize_episode(raw)
        event_claims = [c for c in claims if c.kind.value == "event"]
        assert len(event_claims) == 1
        c = event_claims[0]
        assert c.subject == "Melanie"
        assert c.event_time is not None
        assert c.event_time.date() == (SESSION_DATE - timedelta(days=1)).date()

    def test_speaker_fallback_does_not_override_proper_name_subject(self) -> None:
        # "Bob: Alice went to Paris last week" — subject should stay "Alice",
        # NOT be replaced by the speaker "Bob".
        raw = _mk_raw("Bob: Alice went to Paris last week with her sister.", turn_id="t3")
        claims = materialize_episode(raw)
        event_claims = [c for c in claims if c.kind.value == "event"]
        assert len(event_claims) == 1
        assert event_claims[0].subject == "Alice"

    def test_no_date_anchor_no_event_emission(self) -> None:
        # No explicit or relative date → EVENT fallback must not fire.
        # "Took a short trip to Rome" — no time anchor.
        raw = _mk_raw("Jon: Took a short trip to Rome to clear my mind.", turn_id="t4")
        claims = materialize_episode(raw)
        # No claim expected from the fallback path for this sentence.
        # (Other paths may emit unrelated claims, but no speaker-anchored EVENT.)
        event_claims = [c for c in claims if c.kind.value == "event" and c.subject == "Jon"]
        assert len(event_claims) == 0

    def test_explicit_date_still_works(self) -> None:
        # Absolute date path must not regress.
        raw = _mk_raw("Melanie: Visited the museum on March 5, 2026.", turn_id="t5")
        claims = materialize_episode(raw)
        event_claims = [c for c in claims if c.kind.value == "event"]
        assert len(event_claims) == 1
        assert event_claims[0].subject == "Melanie"
        assert event_claims[0].event_time is not None
        assert event_claims[0].event_time.date() == datetime(2026, 3, 5).date()

    def test_no_speaker_no_fallback(self) -> None:
        # Text without "Name: " prefix → speaker=None → fallback cannot fire.
        raw = _mk_raw("Took a short trip last week to Rome.", turn_id="t6")
        claims = materialize_episode(raw)
        event_claims = [c for c in claims if c.kind.value == "event"]
        assert len(event_claims) == 1
        # Subject falls back to _extract_simple_subject → "Took" (no replacement
        # because no known speaker).
        assert event_claims[0].subject == "Took"

    def test_version_bumped(self) -> None:
        assert MATERIALIZATION_VERSION == 7

    def test_deictic_guard_still_fires(self) -> None:
        # "This is fantastic" — deictic "This" + evaluative predicate.
        # Should skip emission even with relative-time anchor.
        raw = _mk_raw("Alice: This went really well yesterday.", turn_id="t7")
        claims = materialize_episode(raw)
        event_claims = [c for c in claims if c.kind.value == "event"]
        # Either no event emitted, or subject is not "This".
        for c in event_claims:
            assert c.subject != "This"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
