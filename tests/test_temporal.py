"""Unit tests for temporal anchor helpers."""

from datetime import datetime

from ai_knot._temporal import (
    extract_session_date,
    is_temporal_query,
    resolve_fact_line,
    resolve_relative,
)


class TestIsTemporalQuery:
    def test_when_did(self):
        assert is_temporal_query("When did Melanie sign up for pottery?")

    def test_when_was(self):
        assert is_temporal_query("When was Caroline at the conference?")

    def test_when_is(self):
        assert is_temporal_query("When is Melanie going camping?")

    def test_what_date(self):
        assert is_temporal_query("What date did Jon go to Paris?")

    def test_what_year(self):
        assert is_temporal_query("What year did they move?")

    def test_what_month(self):
        assert is_temporal_query("What month is the conference?")

    def test_not_temporal(self):
        assert not is_temporal_query("What does Melanie do to destress?")

    def test_not_temporal_why(self):
        assert not is_temporal_query("Why did Gina start her clothing store?")

    def test_when_conjunction_not_temporal(self):
        # "when" as conditional mid-sentence should not trigger
        assert not is_temporal_query("Who supports Caroline when she has a negative experience?")

    def test_when_conjunction_mid_sentence(self):
        assert not is_temporal_query("What does Melanie do when she feels stressed?")


class TestExtractSessionDate:
    def test_extracts_day_month_year(self):
        lines = ["[1] [3 July, 2023] Melanie: I signed up yesterday."]
        dt = extract_session_date(lines)
        assert dt == datetime(2023, 7, 3)

    def test_extracts_without_comma(self):
        lines = ["[1] [20 January 2023] Jon: I lost my job yesterday."]
        dt = extract_session_date(lines)
        assert dt == datetime(2023, 1, 20)

    def test_returns_first_date(self):
        lines = [
            "[1] [3 July, 2023] Melanie: text",
            "[2] [25 August, 2023] Melanie: other",
        ]
        dt = extract_session_date(lines)
        assert dt == datetime(2023, 7, 3)

    def test_no_date_returns_none(self):
        lines = ["[1] Melanie: I signed up yesterday."]
        assert extract_session_date(lines) is None

    def test_empty_returns_none(self):
        assert extract_session_date([]) is None


class TestResolveRelative:
    def test_yesterday(self):
        dt = datetime(2023, 7, 3)
        assert resolve_relative("I went there yesterday", dt) == "I went there 2 July 2023"

    def test_next_month_no_fake_day(self):
        dt = datetime(2023, 7, 3)
        result = resolve_relative("I'm going camping next month", dt)
        assert "August 2023" in result
        assert "3 August" not in result

    def test_last_year(self):
        dt = datetime(2023, 7, 3)
        assert resolve_relative("I read it last year", dt) == "I read it 2022"

    def test_year_boundary_next_month(self):
        dt = datetime(2023, 12, 15)
        result = resolve_relative("next month", dt)
        assert "January 2024" in result

    def test_year_boundary_last_month(self):
        dt = datetime(2023, 1, 10)
        result = resolve_relative("last month", dt)
        assert "December 2022" in result

    def test_n_days_ago(self):
        dt = datetime(2023, 7, 10)
        result = resolve_relative("3 days ago", dt)
        assert "7 July 2023" in result

    def test_possessive_today_not_resolved(self):
        dt = datetime(2023, 7, 3)
        result = resolve_relative("today's class was great", dt)
        assert "today's" in result
        assert "July" not in result

    def test_possessive_yesterday_not_resolved(self):
        dt = datetime(2023, 7, 3)
        result = resolve_relative("yesterday's results showed progress", dt)
        assert "yesterday's" in result

    def test_possessive_last_week_not_resolved(self):
        dt = datetime(2023, 7, 3)
        result = resolve_relative("last week's meeting was cancelled", dt)
        assert "last week's" in result

    def test_non_possessive_resolved(self):
        dt = datetime(2023, 7, 3)
        assert "3 July 2023" in resolve_relative("I went there today.", dt)
        assert "2 July 2023" in resolve_relative("I went there yesterday.", dt)


class TestResolveFactLine:
    def test_resolves_yesterday_in_dated_fact(self):
        line = "[1] [3 July, 2023] Melanie: I signed up for pottery yesterday."
        result = resolve_fact_line(line)
        assert "2 July 2023" in result
        assert "yesterday" not in result

    def test_no_date_prefix_unchanged(self):
        line = "[1] Melanie: I signed up for pottery yesterday."
        assert resolve_fact_line(line) == line

    def test_preserves_date_prefix_in_output(self):
        line = "[1] [3 July, 2023] Melanie: I went to the park yesterday."
        result = resolve_fact_line(line)
        assert "[3 July, 2023]" in result
        assert "2 July 2023" in result

    def test_next_month_resolved_per_fact(self):
        line = "[2] [25 May, 2023] Melanie: I'm going camping next month."
        result = resolve_fact_line(line)
        assert "June 2023" in result

    def test_multiple_facts_different_dates(self):
        line1 = "[1] [3 July, 2023] A: I signed up yesterday."
        line2 = "[2] [25 August, 2023] B: I made a plate yesterday."
        r1 = resolve_fact_line(line1)
        r2 = resolve_fact_line(line2)
        assert "2 July 2023" in r1
        assert "24 August 2023" in r2
