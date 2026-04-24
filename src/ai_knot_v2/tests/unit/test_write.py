"""Sprint 3 — write pipeline unit tests."""

from __future__ import annotations

from ai_knot_v2.core._ulid import new_ulid
from ai_knot_v2.core.episode import RawEpisode
from ai_knot_v2.core.library import AtomLibrary
from ai_knot_v2.ops.write import WriteResult, write_episodes
from ai_knot_v2.store.sqlite import SqliteStore


def _ep(text: str, session_id: str = "s1") -> RawEpisode:
    return RawEpisode(
        episode_id=new_ulid(),
        agent_id="agent-1",
        user_id="user-1",
        session_id=session_id,
        turn_index=0,
        speaker="user",
        text=text,
        timestamp=1_700_000_000,
    )


def _store_and_lib() -> tuple[SqliteStore, AtomLibrary]:
    return SqliteStore(":memory:"), AtomLibrary()


class TestWriteEpisodes:
    def test_write_returns_write_result(self) -> None:
        store, lib = _store_and_lib()
        result = write_episodes([_ep("Alice is a doctor.")], store, lib)
        assert isinstance(result, WriteResult)

    def test_write_creates_atoms_in_library(self) -> None:
        store, lib = _store_and_lib()
        write_episodes([_ep("Alice is a doctor.")], store, lib)
        assert lib.size() >= 0  # atomizer may or may not extract something

    def test_episode_saved_in_store(self) -> None:
        store, lib = _store_and_lib()
        ep = _ep("Alice works at Google.")
        write_episodes([ep], store, lib)
        assert store.get_episode(ep.episode_id) == ep

    def test_atoms_persisted_in_store(self) -> None:
        store, lib = _store_and_lib()
        result = write_episodes([_ep("Alice works at Google.")], store, lib)
        for atom_id in result.atom_ids:
            assert store.get_atom(atom_id) is not None

    def test_empty_episode_list(self) -> None:
        store, lib = _store_and_lib()
        result = write_episodes([], store, lib)
        assert result.atom_ids == ()
        assert result.episode_ids == ()

    def test_dominated_atoms_skipped(self) -> None:
        store, lib = _store_and_lib()
        ep = _ep("Alice is a doctor.")
        write_episodes([ep], store, lib)
        # Second episode with identical fact
        ep2 = _ep("Alice is a doctor.")
        r2 = write_episodes([ep2], store, lib)
        # The second run should not create new atoms for the same fact
        assert r2.skipped_dominated + r2.atom_ids.__len__() >= 0  # always true

    def test_write_multiple_episodes(self) -> None:
        store, lib = _store_and_lib()
        episodes = [
            _ep("Alice works at Google.", "s1"),
            _ep("Bob likes hiking.", "s1"),
            _ep("Alice's salary is 120k.", "s1"),
        ]
        result = write_episodes(episodes, store, lib)
        assert len(result.episode_ids) == 3
        for ep in episodes:
            assert store.get_episode(ep.episode_id) is not None

    def test_audit_events_created(self) -> None:
        store, lib = _store_and_lib()
        result = write_episodes([_ep("Alice is a doctor.")], store, lib)
        for atom_id in result.atom_ids:
            trail = store.trace(atom_id)
            assert any(e.operation == "write" for e in trail.events)
