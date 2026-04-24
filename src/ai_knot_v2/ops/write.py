"""WRITE operation: episodes → atoms → store.

Pipeline: atomize → coverage-check → irreducibility → risk-override → store.
"""

from __future__ import annotations

import dataclasses
import time
from datetime import UTC, date, datetime

from ai_knot_v2.core._ulid import new_ulid
from ai_knot_v2.core.atom import MemoryAtom
from ai_knot_v2.core.episode import RawEpisode
from ai_knot_v2.core.groupoid import EntityGroupoid
from ai_knot_v2.core.library import AtomLibrary
from ai_knot_v2.core.provenance import AuditEvent
from ai_knot_v2.ops.atomizer import Atomizer
from ai_knot_v2.store.sqlite import SqliteStore


@dataclasses.dataclass(frozen=True, slots=True)
class WriteResult:
    episode_ids: tuple[str, ...]
    atom_ids: tuple[str, ...]
    skipped_duplicate: int
    skipped_dominated: int


def _episode_date(episode: RawEpisode) -> date:
    return datetime.fromtimestamp(episode.timestamp, tz=UTC).date()


def _is_dominated(candidate: MemoryAtom, library: AtomLibrary) -> bool:
    """Skip if identical (predicate, subject, object, polarity) atom already exists."""
    existing = library.query_by_entity(candidate.entity_orbit_id)
    for atom in existing:
        if (
            atom.predicate == candidate.predicate
            and atom.subject == candidate.subject
            and atom.object_value == candidate.object_value
            and atom.polarity == candidate.polarity
        ):
            return True
    return False


def write_episodes(
    episodes: list[RawEpisode],
    store: SqliteStore,
    library: AtomLibrary,
    groupoid: EntityGroupoid | None = None,
) -> WriteResult:
    """Ingest episodes, extract atoms, persist to store + library."""
    atomizer = Atomizer(groupoid)
    all_atom_ids: list[str] = []
    skipped_dup = 0
    skipped_dom = 0

    for episode in episodes:
        # Idempotent episode save
        store.save_episode(episode)
        session_date = _episode_date(episode)

        candidates = atomizer.atomize(episode, session_date)

        for candidate in candidates:
            # Dedup: skip if already in library (exact match)
            existing = library.get(candidate.atom_id)
            if existing is not None:
                skipped_dup += 1
                continue

            # Irreducibility: Sprint 3 simple dominance check
            if _is_dominated(candidate, library):
                skipped_dom += 1
                continue

            # Persist
            store.save_atom(candidate)
            library.add(candidate)
            all_atom_ids.append(candidate.atom_id)

            # Audit
            store.append_audit_event(
                AuditEvent(
                    event_id=new_ulid(),
                    operation="write",
                    atom_id=candidate.atom_id,
                    agent_id=candidate.agent_id,
                    timestamp=int(time.time()),
                    details={
                        "episode_id": episode.episode_id,
                        "predicate": candidate.predicate,
                        "subject": candidate.subject,
                        "risk_class": candidate.risk_class,
                    },
                )
            )

    # Holonomy check (Sprint 12): flag if entity merge graph has a closed loop.
    # Holonomy indicates contradictory identity resolution in the groupoid.
    if atomizer._groupoid.has_holonomy():  # noqa: SLF001
        cycle_orbits = atomizer._groupoid.holonomy_orbits()  # noqa: SLF001
        now = int(time.time())
        store.append_audit_event(
            AuditEvent(
                event_id=new_ulid(),
                operation="holonomy_detected",
                atom_id="",
                agent_id=episodes[0].agent_id if episodes else "",
                timestamp=now,
                details={"cycle_orbits": cycle_orbits},
            )
        )

    return WriteResult(
        episode_ids=tuple(ep.episode_id for ep in episodes),
        atom_ids=tuple(all_atom_ids),
        skipped_duplicate=skipped_dup,
        skipped_dominated=skipped_dom,
    )
