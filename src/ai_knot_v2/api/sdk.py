"""Pydantic v2 DTOs for the ai-knot v2 public SDK.

These are the serializable request/response models exposed to callers.
All internal types (MemoryAtom, etc.) stay in core — these are wire formats.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class EpisodeIn(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    speaker: str = "user"
    session_id: str = "default"
    agent_id: str = "agent-1"
    user_id: str | None = None
    timestamp: int | None = None
    metadata: dict[str, Any] = {}


class LearnRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    episodes: list[EpisodeIn]
    agent_id: str = "agent-1"
    user_id: str | None = None


class LearnResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_ids: list[str]
    atom_ids: list[str]
    skipped_duplicate: int
    skipped_dominated: int


class RecallRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    agent_id: str = "agent-1"
    user_id: str | None = None
    max_atoms: int = 20
    max_tokens: int = 2000
    require_dependency_closure: bool = True


class AtomDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    atom_id: str
    predicate: str
    subject: str | None
    object_value: str | None
    polarity: str
    risk_class: str
    risk_severity: float
    credence: float
    valid_from: int | None
    valid_until: int | None
    entity_orbit_id: str
    synthesis_method: str


class RecallResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    atoms: list[AtomDTO]
    evidence_pack_id: str
    intervention_variable: str


class ExplainResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    atom_id: str
    predicate: str
    subject: str | None
    object_value: str | None
    evidence_episodes: list[str]
    risk_class: str
    synthesis_method: str


class TraceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    atom_id: str
    events: list[dict[str, Any]]


class InspectResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    atoms: list[AtomDTO]
    total: int
