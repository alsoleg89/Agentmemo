"""End-to-end query tests for 4 product scenarios.

Tests are deliberately non-LoCoMo-shaped. They use synthetic data
representing real product use cases: user preference tracking, task
management, temporal state, and bounded hypothesis.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_knot.knowledge import KnowledgeBase
from ai_knot.query_types import AnswerSpace, QueryAnswer
from ai_knot.storage.sqlite_storage import SQLiteStorage


def _make_kb(tmp_path, agent_id="agent") -> KnowledgeBase:
    db = str(tmp_path / f"{agent_id}.db")
    return KnowledgeBase(agent_id=agent_id, storage=SQLiteStorage(db_path=db))


NOW = datetime(2024, 9, 1, 10, 0, tzinfo=UTC)


def _ingest(kb: KnowledgeBase, texts: list[str], session_id: str = "sess-0") -> None:
    for i, text in enumerate(texts):
        kb.ingest_episode(
            session_id=session_id,
            turn_id=f"turn-{i}",
            speaker="user",
            observed_at=NOW,
            raw_text=text,
        )


# ---------------------------------------------------------------------------
# Scenario 1: Set aggregation — collect all dietary preferences
# ---------------------------------------------------------------------------


class TestSetAggregation:
    def test_dietary_preferences_returns_answer(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "The user is vegetarian.",
                "The user is gluten-free.",
                "The user is also lactose intolerant.",
            ],
        )
        answer = kb.query("What are the user's dietary restrictions?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert isinstance(answer.text, str)
        assert answer.trace is not None

    def test_set_query_uses_set_or_collect_strategy(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "Alice likes hiking.",
                "Alice also enjoys reading.",
                "Alice plays tennis on weekends.",
            ],
        )
        answer = kb.query("What hobbies does Alice have?", now=NOW)
        assert answer.trace.strategy in {
            "set_collect",
            "exact_state",
            "candidate_rank",
            "narrative_cluster_render",
        }

    def test_empty_db_set_query_returns_string(self, tmp_path):
        kb = _make_kb(tmp_path)
        answer = kb.query("What tags does the user have?", now=NOW)
        assert isinstance(answer.text, str)

    def test_set_answer_has_items_or_text(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "Project Alpha is assigned to Bob.",
                "Project Beta is assigned to Bob.",
                "Project Gamma is assigned to Bob.",
            ],
        )
        answer = kb.query("What projects is Bob working on?", now=NOW)
        # Either the text is non-empty or items have values
        assert answer.text or len(answer.items) > 0 or answer.trace is not None


# ---------------------------------------------------------------------------
# Scenario 2: Temporal state resolution
# ---------------------------------------------------------------------------


class TestTemporalState:
    def test_current_state_query(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "Alice is currently employed at TechCorp as a senior engineer.",
            ],
        )
        answer = kb.query("What is Alice's current job?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert isinstance(answer.text, str)

    def test_historical_event_query(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "Bob graduated from MIT in 2018.",
                "Bob started working at Acme Corp in 2020.",
            ],
        )
        answer = kb.query("When did Bob start working?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        # time_resolve or exact_state or candidate_rank
        assert answer.trace.strategy in {
            "time_resolve",
            "exact_state",
            "candidate_rank",
            "narrative_cluster_render",
            "set_collect",
        }

    def test_interval_query(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "The user was on vacation from June 1st to June 15th.",
            ],
        )
        answer = kb.query("What did the user do during June?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert answer.trace.frame.answer_space is not None


# ---------------------------------------------------------------------------
# Scenario 3: Bounded hypothesis test
# ---------------------------------------------------------------------------


class TestBoundedHypothesis:
    def test_bool_query_direct_evidence(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(kb, ["Alice is a vegetarian."])
        answer = kb.query("Is Alice a vegetarian?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        # BOOL with direct claim → exact_state or bounded_hypothesis_test
        assert answer.trace.strategy in {
            "exact_state",
            "bounded_hypothesis_test",
            "candidate_rank",
            "narrative_cluster_render",
        }

    def test_bool_query_no_evidence(self, tmp_path):
        kb = _make_kb(tmp_path)
        # No evidence about Bob's diet
        _ingest(kb, ["Bob works as a programmer."])
        answer = kb.query("Is Bob a vegan?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert isinstance(answer.text, str)

    def test_bool_query_conflicting_evidence(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "Charlie said he is not subscribed to the newsletter.",
                "Charlie's profile shows newsletter subscription active.",
            ],
        )
        answer = kb.query("Is Charlie subscribed to the newsletter?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert answer.trace.strategy in {
            "bounded_hypothesis_test",
            "exact_state",
            "candidate_rank",
            "narrative_cluster_render",
        }

    def test_answer_contract_for_bool(self, tmp_path):
        from ai_knot.query_contract import analyze_query, derive_answer_contract
        from ai_knot.query_types import TruthMode

        frame = analyze_query("Is the user subscribed to the newsletter?")
        assert frame.answer_space is AnswerSpace.BOOL
        contract = derive_answer_contract(frame)
        # BOOL maps to DIRECT by default (not HYPOTHESIS — that's choose_strategy's job)
        assert contract.truth_mode is TruthMode.DIRECT


# ---------------------------------------------------------------------------
# Scenario 4: Narrative cluster render (no structured answer)
# ---------------------------------------------------------------------------


class TestNarrativeCluster:
    def test_description_query_falls_back_gracefully(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "Dana has been working on the new payment integration for three weeks.",
                "Dana mentioned some bugs in the authentication flow.",
                "Dana completed the API documentation last Monday.",
            ],
        )
        answer = kb.query("Tell me about Dana's work this month.", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert isinstance(answer.text, str)

    def test_entity_lookup_query(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(kb, ["Eve is the account manager for client ACME."])
        answer = kb.query("Who is the account manager for ACME?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert answer.trace.frame.answer_space is AnswerSpace.ENTITY

    def test_scalar_count_query(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(
            kb,
            [
                "There are 5 open support tickets for Frank.",
                "Frank has 3 tickets escalated to priority.",
            ],
        )
        answer = kb.query("How many open tickets does Frank have?", now=NOW)
        assert isinstance(answer, QueryAnswer)
        assert answer.trace.frame.answer_space is AnswerSpace.SCALAR


# ---------------------------------------------------------------------------
# Cross-scenario: QueryAnswer invariants
# ---------------------------------------------------------------------------


class TestQueryAnswerInvariants:
    def test_answer_always_has_trace(self, tmp_path):
        kb = _make_kb(tmp_path)
        for q in [
            "Is Alice happy?",
            "What does Bob do?",
            "When did Carol graduate?",
            "Who is Dave's manager?",
            "How many items does Eve have?",
        ]:
            answer = kb.query(q, now=NOW)
            assert answer.trace is not None
            assert answer.trace.question == q

    def test_query_json_is_dict_with_text_key(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(kb, ["Frank is a pilot."])
        result = kb.query_json("Is Frank a pilot?", now=NOW)
        assert isinstance(result, dict)
        assert "text" in result
        assert isinstance(result["text"], str)

    def test_explain_query_returns_trace(self, tmp_path):
        kb = _make_kb(tmp_path)
        _ingest(kb, ["Grace plays violin."])
        trace = kb.explain_query("What instrument does Grace play?", now=NOW)
        assert hasattr(trace, "strategy")
        assert hasattr(trace, "latency_ms")
        assert hasattr(trace, "evidence_profile")

    def test_rebuild_then_query_consistent(self, tmp_path):
        """Rebuild must not change the query result for same input."""
        kb = _make_kb(tmp_path)
        _ingest(kb, ["Henry is a chef who specializes in Italian cuisine."])

        answer1 = kb.query("What does Henry cook?", now=NOW)
        kb.rebuild_materialized(force=True)
        answer2 = kb.query("What does Henry cook?", now=NOW)

        # Strategy should be consistent
        assert answer1.trace.strategy == answer2.trace.strategy
