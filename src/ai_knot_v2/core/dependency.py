"""Dependency graph types and stub utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_knot_v2.core.atom import MemoryAtom

DependencyMap = dict[str, set[str]]


def build_dependency_map(atoms: list[MemoryAtom]) -> DependencyMap:
    """Build a dependency map from atoms' declared depends_on fields."""
    return {atom.atom_id: set(atom.depends_on) for atom in atoms}


def transitive_closure(atom_ids: set[str], dep_map: DependencyMap) -> set[str]:
    """Sprint 1 stub: returns input unchanged. Full BFS in Sprint 2."""
    return atom_ids
