"""Sprint 4 — end-to-end CLI smoke tests.

Verifies the full pipeline: learn → recall → explain → trace → inspect-memory.
All tests run against an in-memory SQLite store (no persistence between tests).
"""

from __future__ import annotations

from ai_knot_v2.api.product import MemoryAPI
from ai_knot_v2.api.sdk import EpisodeIn, LearnRequest, RecallRequest


def _api() -> MemoryAPI:
    return MemoryAPI(db_path=":memory:")


class TestLearnRecallPipeline:
    def test_learn_returns_atom_ids(self) -> None:
        api = _api()
        resp = api.learn(LearnRequest(episodes=[EpisodeIn(text="Alice is a doctor.")]))
        assert resp.atom_ids  # at least one atom extracted

    def test_recall_returns_atoms(self) -> None:
        api = _api()
        api.learn(LearnRequest(episodes=[EpisodeIn(text="Alice is a doctor.")]))
        resp = api.recall(RecallRequest(query="What is Alice's profession?"))
        assert isinstance(resp.atoms, list)
        assert resp.evidence_pack_id != ""
        assert resp.intervention_variable != ""

    def test_recall_preference_retrieves_relevant(self) -> None:
        api = _api()
        api.learn(
            LearnRequest(
                episodes=[
                    EpisodeIn(text="I love hiking and outdoor activities."),
                    EpisodeIn(text="Alice is a software engineer."),
                ]
            )
        )
        resp = api.recall(RecallRequest(query="What does the user enjoy?"))
        atom_predicates = {a.predicate for a in resp.atoms}
        # At least some atoms should be returned
        assert len(resp.atoms) > 0
        assert "prefers" in atom_predicates or "is" in atom_predicates

    def test_recall_medical_context(self) -> None:
        api = _api()
        api.learn(
            LearnRequest(
                episodes=[
                    EpisodeIn(text="I have a doctor appointment next week."),
                    EpisodeIn(text="Alice has diabetes."),
                ]
            )
        )
        resp = api.recall(RecallRequest(query="What medical appointments are scheduled?"))
        assert len(resp.atoms) >= 1
        assert resp.intervention_variable in ("health", "schedule", "general")

    def test_multiple_episodes_all_indexed(self) -> None:
        api = _api()
        texts = [
            "Alice is a teacher.",
            "Bob works at Google.",
            "Carol loves hiking.",
        ]
        resp = api.learn(LearnRequest(episodes=[EpisodeIn(text=t) for t in texts]))
        assert len(resp.atom_ids) >= 3

    def test_learn_idempotent_dedup(self) -> None:
        api = _api()
        ep = EpisodeIn(text="Alice is a doctor.")
        api.learn(LearnRequest(episodes=[ep]))
        resp2 = api.learn(LearnRequest(episodes=[ep]))
        # Second learn should produce no new atoms (dominated)
        assert resp2.atom_ids == [] or resp2.skipped_dominated > 0 or resp2.skipped_duplicate > 0

    def test_recall_empty_library_returns_empty(self) -> None:
        api = _api()
        resp = api.recall(RecallRequest(query="What is Alice's job?"))
        assert resp.atoms == []


class TestExplainTrace:
    def test_explain_returns_provenance(self) -> None:
        api = _api()
        learn_resp = api.learn(LearnRequest(episodes=[EpisodeIn(text="Alice is a doctor.")]))
        assert learn_resp.atom_ids
        atom_id = learn_resp.atom_ids[0]
        explain = api.explain(atom_id)
        assert explain.atom_id == atom_id
        assert explain.predicate != ""
        assert explain.evidence_episodes  # at least 1 source episode

    def test_explain_unknown_atom_raises(self) -> None:
        import pytest

        api = _api()
        with pytest.raises(KeyError):
            api.explain("nonexistent-atom-id")

    def test_trace_returns_audit_events(self) -> None:
        api = _api()
        learn_resp = api.learn(LearnRequest(episodes=[EpisodeIn(text="Alice is a doctor.")]))
        assert learn_resp.atom_ids
        atom_id = learn_resp.atom_ids[0]
        trace = api.trace(atom_id)
        assert trace.atom_id == atom_id
        assert isinstance(trace.events, list)
        assert len(trace.events) >= 1
        assert trace.events[0]["operation"] == "write"

    def test_trace_unknown_atom_returns_empty_events(self) -> None:
        api = _api()
        trace = api.trace("nonexistent-id")
        assert trace.events == []


class TestInspectMemory:
    def test_inspect_all_returns_atoms(self) -> None:
        api = _api()
        api.learn(
            LearnRequest(
                episodes=[
                    EpisodeIn(text="Alice is a doctor."),
                    EpisodeIn(text="I love hiking."),
                ]
            )
        )
        result = api.inspect_memory()
        assert result.total >= 2

    def test_inspect_filter_risk_class(self) -> None:
        api = _api()
        api.learn(
            LearnRequest(
                episodes=[
                    EpisodeIn(text="Alice is a doctor."),
                    EpisodeIn(text="I love hiking."),
                ]
            )
        )
        result = api.inspect_memory({"risk_class": "preference"})
        assert all(a.risk_class == "preference" for a in result.atoms)

    def test_inspect_filter_predicate(self) -> None:
        api = _api()
        api.learn(LearnRequest(episodes=[EpisodeIn(text="I love hiking.")]))
        result = api.inspect_memory({"predicate": "prefers"})
        assert all(a.predicate == "prefers" for a in result.atoms)

    def test_inspect_empty_library(self) -> None:
        api = _api()
        result = api.inspect_memory()
        assert result.total == 0
        assert result.atoms == []
