"""MemoryAtom — the core memory primitive.

Schema is permanent from Sprint 1. No fields are added, removed, or renamed
in later sprints. Only computation functions evolve.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal


@dataclasses.dataclass(frozen=True, slots=True)
class MemoryAtom:
    # === Identity ===
    atom_id: str
    agent_id: str
    user_id: str | None

    # === Causal structure ===
    variables: tuple[str, ...]
    causal_graph: tuple[tuple[str, str], ...]
    kernel_kind: Literal["point", "categorical", "structural"]
    kernel_payload: dict[str, Any] = dataclasses.field(hash=False)
    intervention_domain: tuple[str, ...]

    # === Constraint triple ===
    predicate: str
    subject: str
    object_value: str | None
    polarity: Literal["pos", "neg"]

    # === Tri-temporal ===
    valid_from: int | None
    valid_until: int | None
    observation_time: int
    belief_time: int
    granularity: Literal["instant", "day", "month", "year", "interval"]

    # === Identity / groupoid ===
    entity_orbit_id: str
    transport_provenance: tuple[str, ...]

    # === Dependency boundary ===
    depends_on: tuple[str, ...]
    depended_by: tuple[str, ...]

    # === Risk / protection ===
    risk_class: Literal[
        "safety",
        "identity",
        "finance",
        "legal",
        "medical",
        "commitment",
        "scheduling",
        "preference",
        "ambient",
    ]
    risk_severity: float
    regret_charge: float
    irreducibility_score: float
    protection_energy: float
    action_affect_mask: int

    # === Credence + provenance ===
    credence: float
    evidence_episodes: tuple[str, ...]
    synthesis_method: Literal["regex", "llm", "fusion", "oracle", "manual"]
    validation_tests: tuple[str, ...]
    contradiction_events: tuple[str, ...]
