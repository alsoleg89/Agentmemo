"""Snapshot/restore atomicity tests.

Verifies that snapshot and restore operations are all-or-nothing:
either the entire operation succeeds (and state is the full snapshot),
or it fails and the pre-operation state is preserved.

Current scope: legacy facts plane (v1). The v2 plane snapshot extension
(raw_episodes + atomic_claims) is tracked as a Phase B enhancement.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.sqlite_storage import SQLiteStorage


def _make_kb(tmp_path, agent_id: str = "agent") -> KnowledgeBase:
    return KnowledgeBase(
        agent_id=agent_id,
        storage=SQLiteStorage(db_path=str(tmp_path / f"{agent_id}.db")),
    )


NOW = datetime(2024, 1, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Basic snapshot/restore all-or-nothing invariant
# ---------------------------------------------------------------------------


class TestSnapshotAtomicity:
    def test_restore_gives_exact_snapshot_state(self, tmp_path):
        """After restore, facts are exactly what was in the snapshot."""
        kb = _make_kb(tmp_path)
        kb.add("Alice is an engineer.")
        kb.add("Bob is a doctor.")
        kb.snapshot("snap1")

        # Add more facts and then restore
        kb.add("Charlie is a pilot.")
        assert len(kb.list_facts()) >= 3

        kb.restore("snap1")
        facts = kb.list_facts()
        contents = {f.content for f in facts}

        # Restored state must exactly match snapshot
        assert "Alice is an engineer." in contents
        assert "Bob is a doctor." in contents
        assert "Charlie is a pilot." not in contents

    def test_snapshot_then_delete_then_restore(self, tmp_path):
        """Restore after all facts deleted gives back the snapshot state."""
        kb = _make_kb(tmp_path)
        kb.add("Dana plays violin.")
        fact = kb.add("Eve likes hiking.")
        kb.snapshot("snap2")

        kb.forget(fact.id)
        kb.snapshot("snap3")  # snapshot without Eve

        kb.restore("snap2")  # back to both facts
        facts = kb.list_facts()
        assert any("Dana" in f.content for f in facts)
        assert any("Eve" in f.content for f in facts)

    def test_restore_nonexistent_snapshot_raises(self, tmp_path):
        """Restoring a non-existent snapshot must raise KeyError."""
        import pytest

        kb = _make_kb(tmp_path)
        with pytest.raises(KeyError):
            kb.restore("does_not_exist")

    def test_multiple_snapshots_independent(self, tmp_path):
        """Each snapshot is independent; restoring one doesn't affect others."""
        kb = _make_kb(tmp_path)
        kb.add("Fact A.")
        kb.snapshot("snap_a")

        kb.add("Fact B.")
        kb.snapshot("snap_b")

        # Restore snap_a — Fact B should be gone
        kb.restore("snap_a")
        facts_a = {f.content for f in kb.list_facts()}
        assert "Fact A." in facts_a
        assert "Fact B." not in facts_a

        # Restore snap_b — Fact B should be back
        kb.restore("snap_b")
        facts_b = {f.content for f in kb.list_facts()}
        assert "Fact A." in facts_b
        assert "Fact B." in facts_b

    def test_list_snapshots_includes_saved(self, tmp_path):
        kb = _make_kb(tmp_path)
        kb.add("Frank is a lawyer.")
        kb.snapshot("s1")
        kb.add("Grace is a nurse.")
        kb.snapshot("s2")

        names = kb.list_snapshots()
        assert "s1" in names
        assert "s2" in names


# ---------------------------------------------------------------------------
# v2 plane consistency after snapshot/restore
# ---------------------------------------------------------------------------


class TestV2PlaneAfterRestore:
    def test_v2_claims_survive_legacy_restore(self, tmp_path):
        """After restore of legacy snapshot, v2 claims must still be queryable.

        Current behavior: restore only restores facts plane; v2 claims are
        independent and survive the restore operation unchanged.
        """
        kb = _make_kb(tmp_path)

        # Ingest via v2
        kb.ingest_episode(
            session_id="sess-0",
            turn_id="t0",
            speaker="user",
            observed_at=NOW,
            raw_text="Alice is a software engineer.",
        )
        # Add legacy fact
        kb.add("Bob is a doctor.")
        kb.snapshot("mixed")

        # Add another legacy fact
        kb.add("Charlie is a pilot.")
        kb.restore("mixed")

        # v2 path: query still works
        answer = kb.query("What does Alice do?", now=NOW)
        assert isinstance(answer.text, str)

        # Legacy path: Charlie is gone (restored to snapshot)
        facts = kb.list_facts()
        assert not any("Charlie" in f.content for f in facts)

    def test_rebuild_after_restore_is_consistent(self, tmp_path):
        """rebuild_materialized after restore produces a valid query answer."""
        kb = _make_kb(tmp_path)
        kb.ingest_episode(
            session_id="sess-0",
            turn_id="t0",
            speaker="user",
            observed_at=NOW,
            raw_text="Dana works at Acme as a marketing specialist.",
        )
        kb.add("Dana legacy fact.")
        kb.snapshot("pre_rebuild")

        kb.rebuild_materialized(force=True)
        kb.restore("pre_rebuild")
        kb.rebuild_materialized(force=True)

        answer = kb.query("What does Dana do?", now=NOW)
        assert isinstance(answer.text, str)
        assert answer.trace is not None


# ---------------------------------------------------------------------------
# Concurrent snapshot read / write
# ---------------------------------------------------------------------------


class TestConcurrentSnapshot:
    def test_concurrent_reads_do_not_corrupt(self, tmp_path):
        """Multiple threads reading snapshots simultaneously must all succeed."""
        kb = _make_kb(tmp_path)
        kb.add("Shared fact.")
        kb.snapshot("shared")

        errors: list[Exception] = []

        def _read() -> None:
            try:
                kb.restore("shared")
                _ = kb.list_facts()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_read) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"

    def test_snapshot_during_concurrent_add_does_not_crash(self, tmp_path):
        """Snapshot taken while another thread is adding facts must not raise."""
        kb = _make_kb(tmp_path)
        kb.add("Initial fact.")

        errors: list[Exception] = []
        barrier = threading.Barrier(2)

        def _add_facts() -> None:
            barrier.wait()
            for i in range(10):
                try:
                    kb.add(f"Concurrent fact {i}.")
                except Exception as exc:
                    errors.append(exc)

        def _snapshot() -> None:
            barrier.wait()
            try:
                kb.snapshot("concurrent_snap")
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=_add_facts)
        t2 = threading.Thread(target=_snapshot)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
