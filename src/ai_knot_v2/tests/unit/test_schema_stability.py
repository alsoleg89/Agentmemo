"""Schema stability gate — fails if MemoryAtom field names or types change.

Update GOLDEN_HASH only after a deliberate schema review; the hash encodes
the exact field ordering, names, and type annotation strings.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

from ai_knot_v2.core.atom import MemoryAtom

GOLDEN_HASH = "7ea10bbf15945043a89a70268377a552627e83d6c6cefdde8f042888ab9f8ffe"


def _compute_schema_hash() -> str:
    fields = dataclasses.fields(MemoryAtom)
    sig = [(f.name, str(f.type)) for f in fields]
    return hashlib.sha256(json.dumps(sig).encode()).hexdigest()


def test_schema_stability() -> None:
    computed = _compute_schema_hash()
    assert computed == GOLDEN_HASH, (
        f"MemoryAtom schema has changed!\n"
        f"  expected: {GOLDEN_HASH}\n"
        f"  computed: {computed}\n"
        "Update GOLDEN_HASH only after deliberate schema review."
    )


def test_schema_has_expected_field_count() -> None:
    assert len(dataclasses.fields(MemoryAtom)) == 32


def test_schema_field_names() -> None:
    names = {f.name for f in dataclasses.fields(MemoryAtom)}
    required = {
        "atom_id",
        "agent_id",
        "user_id",
        "variables",
        "causal_graph",
        "kernel_kind",
        "kernel_payload",
        "intervention_domain",
        "predicate",
        "subject",
        "object_value",
        "polarity",
        "valid_from",
        "valid_until",
        "observation_time",
        "belief_time",
        "granularity",
        "entity_orbit_id",
        "transport_provenance",
        "depends_on",
        "depended_by",
        "risk_class",
        "risk_severity",
        "regret_charge",
        "irreducibility_score",
        "protection_energy",
        "action_affect_mask",
        "credence",
        "evidence_episodes",
        "synthesis_method",
        "validation_tests",
        "contradiction_events",
    }
    assert required <= names, f"Missing fields: {required - names}"
