"""Sprint 9-10 — recall / read path unit tests."""

from __future__ import annotations

from ai_knot_v2.core._ulid import new_ulid
from ai_knot_v2.core.atom import MemoryAtom
from ai_knot_v2.core.library import AtomLibrary
from ai_knot_v2.core.types import Intervention, ReaderBudget
from ai_knot_v2.ops.read import _extract_proper_nouns, _normalize_qword, select_candidates


def _atom(
    subject: str = "Alice",
    predicate: str = "is",
    object_value: str = "doctor",
    risk_severity: float = 0.5,
    entity_orbit_id: str = "orbit-1",
    observation_time: int = 1000,
) -> MemoryAtom:
    return MemoryAtom(
        atom_id=new_ulid(),
        agent_id="agent-1",
        user_id=None,
        variables=(),
        causal_graph=(),
        kernel_kind="point",
        kernel_payload={},
        intervention_domain=(),
        predicate=predicate,
        subject=subject,
        object_value=object_value,
        polarity="pos",
        valid_from=None,
        valid_until=None,
        observation_time=observation_time,
        belief_time=observation_time,
        granularity="instant",
        entity_orbit_id=entity_orbit_id,
        transport_provenance=(),
        depends_on=(),
        depended_by=(),
        risk_class="preference",
        risk_severity=risk_severity,
        regret_charge=0.0,
        irreducibility_score=0.0,
        protection_energy=1.0,
        action_affect_mask=0,
        credence=0.9,
        evidence_episodes=(),
        synthesis_method="regex",
        validation_tests=(),
        contradiction_events=(),
    )


_DEFAULT_INTERVENTION = Intervention(variable="general", value="")
_DEFAULT_BUDGET = ReaderBudget(max_atoms=20, max_tokens=2000, require_dependency_closure=True)


class TestNormalizeQword:
    def test_strips_possessive(self) -> None:
        assert _normalize_qword("Alice's") == "alice"

    def test_strips_trailing_question_mark(self) -> None:
        assert _normalize_qword("job?") == "job"

    def test_strips_trailing_period(self) -> None:
        assert _normalize_qword("hiking.") == "hiking"

    def test_lowercase(self) -> None:
        assert _normalize_qword("Doctor") == "doctor"

    def test_no_change_plain_word(self) -> None:
        assert _normalize_qword("hiking") == "hiking"

    def test_strips_plural_possessive(self) -> None:
        # "doctors'" → strip trailing apostrophe → "doctors" (no stemming)
        assert _normalize_qword("doctors'") == "doctors"


class TestExtractProperNouns:
    def test_single_proper_noun(self) -> None:
        result = _extract_proper_nouns("What is Alice's job?")
        assert result == ["alice"]

    def test_two_proper_nouns(self) -> None:
        result = _extract_proper_nouns("Did Alice and Bob go hiking?")
        assert len(result) == 2

    def test_question_word_filtered(self) -> None:
        result = _extract_proper_nouns("What did she do?")
        assert result == []

    def test_short_name_included(self) -> None:
        result = _extract_proper_nouns("Where does Jim work?")
        assert "jim" in result


class TestSelectCandidates:
    def _library(self, atoms: list[MemoryAtom]) -> AtomLibrary:
        lib = AtomLibrary()
        for a in atoms:
            lib.add(a)
        return lib

    def test_returns_empty_for_empty_library(self) -> None:
        lib = AtomLibrary()
        result = select_candidates(lib, _DEFAULT_INTERVENTION, "anything", _DEFAULT_BUDGET)
        assert result == []

    def test_possessive_query_matches_subject(self) -> None:
        """Alice's job? should still match atom with subject=Alice (possessive bug fix)."""
        alice_atom = _atom(subject="Alice", predicate="works_at", object_value="Google")
        jim_atom = _atom(
            subject="Jim", predicate="works_at", object_value="Amazon", entity_orbit_id="orbit-2"
        )
        lib = self._library([alice_atom, jim_atom])
        result = select_candidates(
            lib, _DEFAULT_INTERVENTION, "What is Alice's job?", _DEFAULT_BUDGET
        )
        result_ids = {a.atom_id for a in result}
        assert alice_atom.atom_id in result_ids

    def test_semantic_hint_boosts_works_at(self) -> None:
        """Query with 'job' should boost works_at atoms above same-subject is atoms."""
        alice_job = _atom(
            subject="Alice", predicate="works_at", object_value="Google", entity_orbit_id="orbit-1"
        )
        alice_is = _atom(
            subject="Alice", predicate="is", object_value="happy", entity_orbit_id="orbit-1"
        )
        lib = self._library([alice_job, alice_is])
        budget = ReaderBudget(max_atoms=1, max_tokens=2000, require_dependency_closure=False)
        result = select_candidates(lib, _DEFAULT_INTERVENTION, "What is Alice's job?", budget)
        assert len(result) == 1
        assert result[0].predicate == "works_at"

    def test_short_name_subject_matches(self) -> None:
        """Jim (3-char name) should match when query asks about Jim."""
        jim_atom = _atom(
            subject="Jim", predicate="works_at", object_value="Amazon", entity_orbit_id="orbit-jim"
        )
        bob_atom = _atom(
            subject="Bob", predicate="is", object_value="engineer", entity_orbit_id="orbit-bob"
        )
        lib = self._library([jim_atom, bob_atom])
        budget = ReaderBudget(max_atoms=1, max_tokens=2000, require_dependency_closure=False)
        result = select_candidates(lib, _DEFAULT_INTERVENTION, "Where does Jim work?", budget)
        assert len(result) == 1
        assert result[0].atom_id == jim_atom.atom_id

    def test_pronoun_subject_not_boosted_by_pronoun_query(self) -> None:
        """Pronoun-subject atoms should score lower than named-entity atoms.

        When query has 'Alice', Alice atom gets subject-match boost.
        Even though query also has 'she', 'she'-subject atom is NOT boosted
        because 'she' is in _PRONOUNS and excluded from subject matching.
        """
        she_atom = _atom(
            subject="she", predicate="went", object_value="hospital", entity_orbit_id="orbit-she"
        )
        alice_atom = _atom(
            subject="Alice",
            predicate="went",
            object_value="hospital",
            entity_orbit_id="orbit-alice",
        )
        lib = self._library([she_atom, alice_atom])
        budget = ReaderBudget(max_atoms=1, max_tokens=2000, require_dependency_closure=False)
        # Query mentions "Alice" explicitly — Alice atom should rank first
        result = select_candidates(
            lib, _DEFAULT_INTERVENTION, "Where did Alice go? She went to the hospital.", budget
        )
        assert len(result) == 1
        assert result[0].atom_id == alice_atom.atom_id


class TestPlannerRecentyTiebreaker:
    """Tests for planner contradiction resolution with recency tiebreaker."""

    def test_more_recent_atom_kept_on_equal_credence(self) -> None:
        from ai_knot_v2.core.types import ReaderBudget
        from ai_knot_v2.ops.planner import plan_evidence_pack

        older = _atom(
            subject="Alice", predicate="works_at", object_value="Google", observation_time=1000
        )
        newer = _atom(
            subject="Alice", predicate="works_at", object_value="Amazon", observation_time=2000
        )

        budget = ReaderBudget(max_atoms=10, max_tokens=2000, require_dependency_closure=False)
        pack = plan_evidence_pack([older, newer], "Where does Alice work?", budget)
        pack_ids = set(pack.atoms)

        # newer should be kept, older removed (observation_time tiebreaker)
        assert newer.atom_id in pack_ids
        assert older.atom_id not in pack_ids

    def test_simultaneous_contradiction_abstains(self) -> None:
        from ai_knot_v2.core.types import ReaderBudget
        from ai_knot_v2.ops.planner import plan_evidence_pack

        a = _atom(subject="Alice", predicate="is", object_value="doctor", observation_time=1000)
        b = _atom(
            subject="Alice", predicate="is", object_value="nurse", observation_time=1000
        )  # same time → abstain

        budget = ReaderBudget(max_atoms=10, max_tokens=2000, require_dependency_closure=False)
        pack = plan_evidence_pack([a, b], "What is Alice?", budget)
        pack_ids = set(pack.atoms)

        # Both should be abstained (same observation_time = simultaneous contradiction)
        assert a.atom_id not in pack_ids
        assert b.atom_id not in pack_ids
