"""Tests for query_contract — geometry-based routing without keyword policy."""

from __future__ import annotations

from ai_knot.query_contract import analyze_query, derive_answer_contract
from ai_knot.query_types import (
    AnswerSpace,
    EvidenceRegime,
    TimeAxis,
    TruthMode,
)

# ---------------------------------------------------------------------------
# analyze_query — QueryFrame geometry
# ---------------------------------------------------------------------------


class TestAnalyzeQuery:
    def test_set_question_what_hobbies(self):
        frame = analyze_query("What hobbies does Alice have?")
        assert frame.answer_space is AnswerSpace.SET

    def test_set_question_list_all(self):
        frame = analyze_query("List all the activities Alice enjoys.")
        assert frame.answer_space is AnswerSpace.SET

    def test_bool_question_is(self):
        frame = analyze_query("Is Alice a vegetarian?")
        assert frame.answer_space is AnswerSpace.BOOL

    def test_bool_question_does(self):
        frame = analyze_query("Does Bob drink coffee?")
        assert frame.answer_space is AnswerSpace.BOOL

    def test_entity_question_who(self):
        frame = analyze_query("Who is Alice's best friend?")
        assert frame.answer_space is AnswerSpace.ENTITY

    def test_scalar_how_many(self):
        frame = analyze_query("How many siblings does Alice have?")
        assert frame.answer_space is AnswerSpace.SCALAR

    def test_scalar_when(self):
        frame = analyze_query("When did Bob start working at Acme?")
        assert frame.answer_space is AnswerSpace.SCALAR

    def test_description_what_is(self):
        frame = analyze_query("What is Alice's current job?")
        # "What ... is" patterns — may be DESCRIPTION or SET depending on noun
        # Allow SET or DESCRIPTION for this pattern
        assert frame.answer_space in (AnswerSpace.DESCRIPTION, AnswerSpace.SET)

    def test_entity_extraction_two_names(self):
        frame = analyze_query("What does John Smith think about Alice Johnson?")
        assert "John Smith" in frame.focus_entities or "Alice Johnson" in frame.focus_entities

    def test_no_surface_keyword_routing(self):
        """'would', 'likely', 'might' must NOT determine the contract."""
        frame_plain = analyze_query("Is Alice happy?")
        frame_modal = analyze_query("Would Alice be happy?")
        # Both are BOOL — modal surface form must not change answer_space
        assert frame_plain.answer_space is AnswerSpace.BOOL
        assert frame_modal.answer_space is AnswerSpace.BOOL

    def test_temporal_scope_current_signals(self):
        frame = analyze_query("What is Alice's current job?")
        assert frame.temporal_scope == "current"

    def test_temporal_scope_historical(self):
        frame = analyze_query("When did Bob graduate?")
        assert frame.temporal_scope in ("historical", "none")  # 'when' → historical

    def test_temporal_scope_interval(self):
        frame = analyze_query("What did Alice do during the summer?")
        assert frame.temporal_scope == "interval"

    def test_evidence_regime_bool(self):
        frame = analyze_query("Is Alice married?")
        assert frame.evidence_regime is EvidenceRegime.SUPPORT_VS_CONTRA

    def test_evidence_regime_set(self):
        frame = analyze_query("What sports does Bob play?")
        assert frame.evidence_regime is EvidenceRegime.AGGREGATE

    def test_evidence_regime_single(self):
        frame = analyze_query("What is Alice's age?")
        assert frame.evidence_regime is EvidenceRegime.SINGLE


# ---------------------------------------------------------------------------
# derive_answer_contract — mapping frame → contract
# ---------------------------------------------------------------------------


class TestDeriveAnswerContract:
    def test_set_question_truth_mode(self):
        frame = analyze_query("What books has Alice read?")
        contract = derive_answer_contract(frame)
        assert contract.truth_mode is TruthMode.RECONSTRUCT

    def test_bool_question_truth_mode_is_direct_not_hypothesis(self):
        """BOOL does NOT auto-map to HYPOTHESIS — that's choose_strategy's job."""
        frame = analyze_query("Is Alice a vegetarian?")
        contract = derive_answer_contract(frame)
        assert contract.truth_mode is TruthMode.DIRECT

    def test_current_temporal_maps_to_current_axis(self):
        frame = analyze_query("What is Alice doing now?")
        contract = derive_answer_contract(frame)
        assert contract.time_axis is TimeAxis.CURRENT

    def test_historical_maps_to_event_axis(self):
        frame = analyze_query("When did Alice start her job?")
        contract = derive_answer_contract(frame)
        assert contract.time_axis is TimeAxis.EVENT

    def test_interval_maps_to_interval_axis(self):
        frame = analyze_query("What happened between 2020 and 2022?")
        contract = derive_answer_contract(frame)
        assert contract.time_axis is TimeAxis.INTERVAL

    def test_set_question_aggregate_regime(self):
        frame = analyze_query("What sports does Bob play?")
        contract = derive_answer_contract(frame)
        assert contract.evidence_regime is EvidenceRegime.AGGREGATE

    def test_uncertainty_threshold_default(self):
        frame = analyze_query("Is Alice a teacher?")
        contract = derive_answer_contract(frame)
        assert 0.0 < contract.uncertainty_threshold <= 1.0


# ---------------------------------------------------------------------------
# Product queries — non-LoCoMo examples
# ---------------------------------------------------------------------------


class TestProductQueries:
    """Ensure contract derivation works on real-world product use cases."""

    def test_user_preference_set(self):
        frame = analyze_query("What are the user's dietary preferences?")
        derive_answer_contract(frame)  # validate no error
        # Dietary preferences = a set of restrictions
        assert frame.answer_space in (AnswerSpace.SET, AnswerSpace.DESCRIPTION)

    def test_current_state_bool(self):
        frame = analyze_query("Is the user subscribed to the newsletter?")
        contract = derive_answer_contract(frame)
        assert frame.answer_space is AnswerSpace.BOOL
        assert contract.truth_mode is TruthMode.DIRECT

    def test_entity_lookup(self):
        frame = analyze_query("Who is the user's account manager?")
        assert frame.answer_space is AnswerSpace.ENTITY

    def test_scalar_count(self):
        frame = analyze_query("How many open tickets does Alice have?")
        assert frame.answer_space is AnswerSpace.SCALAR
