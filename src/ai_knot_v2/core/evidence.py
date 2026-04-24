"""Evidence store protocol and helpers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ai_knot_v2.core.types import EvidencePack, EvidenceSpan


@runtime_checkable
class EvidenceStore(Protocol):
    def get_pack(self, pack_id: str) -> EvidencePack | None: ...
    def save_pack(self, pack: EvidencePack) -> None: ...
    def delete_pack(self, pack_id: str) -> None: ...


def build_empty_pack(pack_id: str, atom_ids: tuple[str, ...]) -> EvidencePack:
    """Return an evidence pack with no spans (Sprint 1 stub)."""
    return EvidencePack(pack_id=pack_id, atoms=atom_ids, spans=())


__all__ = ["EvidenceStore", "EvidenceSpan", "EvidencePack", "build_empty_pack"]
