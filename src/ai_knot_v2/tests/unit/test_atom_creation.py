"""Sprint 1 — failing-red placeholder.

These tests will pass once core/atom.py, core/types.py, core/episode.py,
core/evidence.py, core/dependency.py, and core/library.py are implemented.
"""


def test_memory_atom_import() -> None:
    """MemoryAtom must be importable from core.atom."""
    from ai_knot_v2.core.atom import MemoryAtom  # noqa: F401


def test_raw_episode_import() -> None:
    """RawEpisode must be importable from core.episode."""
    from ai_knot_v2.core.episode import RawEpisode  # noqa: F401


def test_recall_query_import() -> None:
    """RecallQuery, ReaderBudget, RecallResult must be importable from core.types."""
    from ai_knot_v2.core.types import ReaderBudget, RecallQuery, RecallResult  # noqa: F401


def test_evidence_pack_import() -> None:
    """EvidencePack must be importable from core.evidence."""
    from ai_knot_v2.core.evidence import EvidencePack  # noqa: F401


def test_atom_library_import() -> None:
    """AtomLibrary must be importable from core.library."""
    from ai_knot_v2.core.library import AtomLibrary  # noqa: F401


def test_memory_atom_construction() -> None:
    """MemoryAtom can be constructed with all required fields."""
    from ai_knot_v2.core.atom import MemoryAtom

    atom = MemoryAtom(
        atom_id="01HXYZ00000000000000000000",
        agent_id="agent-1",
        user_id="user-1",
        variables=("name",),
        causal_graph=(),
        kernel_kind="point",
        kernel_payload={},
        intervention_domain=("name",),
        predicate="has_name",
        subject="alice",
        object_value="Alice",
        polarity="pos",
        valid_from=None,
        valid_until=None,
        observation_time=1700000000,
        belief_time=1700000000,
        granularity="instant",
        entity_orbit_id="entity:alice",
        transport_provenance=(),
        depends_on=(),
        depended_by=(),
        risk_class="identity",
        risk_severity=0.5,
        regret_charge=0.0,
        irreducibility_score=1.0,
        protection_energy=1.0,
        action_affect_mask=0,
        credence=1.0,
        evidence_episodes=("ep-001",),
        synthesis_method="regex",
        validation_tests=(),
        contradiction_events=(),
    )
    assert atom.atom_id == "01HXYZ00000000000000000000"
    assert atom.subject == "alice"
