"""Supporting types for the v2 memory kernel.

All types are frozen dataclasses (stdlib only, no pydantic in core).
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from ai_knot_v2.core.atom import MemoryAtom


@dataclasses.dataclass(frozen=True, slots=True)
class Query:
    text: str
    context: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Intervention:
    variable: str
    value: str


@dataclasses.dataclass(frozen=True, slots=True)
class ReaderBudget:
    max_atoms: int
    max_tokens: int
    require_dependency_closure: bool


@dataclasses.dataclass(frozen=True, slots=True)
class RecallQuery:
    query: Query
    agent_id: str
    user_id: str | None
    budget: ReaderBudget


@dataclasses.dataclass(frozen=True, slots=True)
class RecallResult:
    atoms: list[MemoryAtom] = dataclasses.field(hash=False)
    evidence_pack_id: str = ""
    intervention: Intervention | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class ContradictionEvent:
    atom_id_a: str
    atom_id_b: str
    detected_at: int
    resolution: Literal["split", "abstain", "merged"] | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class ActionPrediction:
    predicted_action_class: str
    confidence: float
    supporting_atoms: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class EvidenceSpan:
    episode_id: str
    start_char: int
    end_char: int
    text: str
    relevance_score: float


@dataclasses.dataclass(frozen=True, slots=True)
class EvidencePack:
    pack_id: str
    atoms: tuple[str, ...]
    spans: tuple[EvidenceSpan, ...]
    utility_scores: dict[str, Any] = dataclasses.field(default_factory=dict, hash=False)
