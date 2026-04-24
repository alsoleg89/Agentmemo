"""Sprint 1 — MemoryAtom behavioral tests."""

from __future__ import annotations

import dataclasses

import pytest

from ai_knot_v2.core.atom import MemoryAtom


def _make_atom() -> MemoryAtom:
    return MemoryAtom(
        atom_id="01ABCDEFGHJKMNPQRSTVWXYZ01",
        agent_id="agent-1",
        user_id="user-42",
        variables=("income", "tax_rate"),
        causal_graph=(("income", "tax_rate"),),
        kernel_kind="point",
        kernel_payload={"mu": 0.5, "sigma": 0.1},
        intervention_domain=("income",),
        predicate="has_salary",
        subject="user-42",
        object_value="120000",
        polarity="pos",
        valid_from=1_700_000_000,
        valid_until=None,
        observation_time=1_700_000_100,
        belief_time=1_700_000_100,
        granularity="day",
        entity_orbit_id="entity:user-42",
        transport_provenance=("session-1",),
        depends_on=(),
        depended_by=(),
        risk_class="finance",
        risk_severity=0.3,
        regret_charge=0.1,
        irreducibility_score=0.8,
        protection_energy=0.5,
        action_affect_mask=0b00000001,
        credence=0.95,
        evidence_episodes=("01EPISODE1",),
        synthesis_method="regex",
        validation_tests=(),
        contradiction_events=(),
    )


def test_construct_memory_atom() -> None:
    atom = _make_atom()
    assert isinstance(atom, MemoryAtom)
    assert atom.atom_id == "01ABCDEFGHJKMNPQRSTVWXYZ01"
    assert atom.risk_class == "finance"
    assert atom.credence == 0.95
    assert atom.kernel_kind == "point"
    assert atom.polarity == "pos"


def test_memory_atom_is_hashable() -> None:
    atom = _make_atom()
    h = hash(atom)
    assert isinstance(h, int)


def test_memory_atom_is_immutable() -> None:
    atom = _make_atom()
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(atom, "atom_id", "tampered")  # noqa: B010


def test_memory_atom_asdict() -> None:
    atom = _make_atom()
    d = dataclasses.asdict(atom)
    assert isinstance(d, dict)
    assert d["atom_id"] == atom.atom_id
    assert d["kernel_payload"] == atom.kernel_payload
    assert d["risk_class"] == atom.risk_class
    assert len(d) == len(dataclasses.fields(atom))


def test_two_atoms_with_same_fields_are_equal() -> None:
    atom1 = _make_atom()
    atom2 = _make_atom()
    assert atom1 == atom2
    assert hash(atom1) == hash(atom2)


def test_memory_atom_different_ids_not_equal() -> None:
    atom1 = _make_atom()
    atom2 = MemoryAtom(**{**dataclasses.asdict(atom1), "atom_id": "DIFFERENT000000000000000000"})
    assert atom1 != atom2
