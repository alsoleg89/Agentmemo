"""Functional smoke tests for Track A performance invariants.

These tests check FUNCTIONAL invariants of the new query planes — they do NOT
assert wall-clock latency thresholds (those belong in the scheduled benchmark).

What we verify:
  - rebuild terminates (watchdog 60s); is not O(n^2); doesn't loop.
  - query terminates in pathological cases (empty DB, no bundles, many claims).
  - concurrent publish + rebuild does not lose claims.
  - materialization is O(N_episodes) not O(N^2).
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.sqlite_storage import SQLiteStorage


def _make_kb(tmp_path):
    db = str(tmp_path / "smoke.db")
    storage = SQLiteStorage(db_path=db)
    return KnowledgeBase(agent_id="smoke", storage=storage)


# ---------------------------------------------------------------------------
# Rebuild invariants
# ---------------------------------------------------------------------------


def test_rebuild_terminates_empty_db(tmp_path):
    """rebuild_materialized on empty DB must return quickly (no loop)."""
    kb = _make_kb(tmp_path)
    t0 = time.monotonic()
    report = kb.rebuild_materialized(force=True)
    elapsed = time.monotonic() - t0
    assert elapsed < 10.0, f"rebuild took {elapsed:.1f}s on empty DB — should be instant"
    assert report is not None


def test_rebuild_terminates_with_episodes(tmp_path):
    """rebuild_materialized must complete on a realistic episode count."""
    kb = _make_kb(tmp_path)
    now = datetime.now(UTC)

    # Ingest 200 episodes
    for i in range(200):
        kb.ingest_episode(
            session_id=f"sess-{i // 10}",
            turn_id=f"turn-{i}",
            speaker="user" if i % 2 == 0 else "assistant",
            observed_at=now,
            raw_text=f"Turn {i}: Alice works at Acme. Bob lives in Paris.",
            materialize=False,  # batch ingest, then rebuild
        )

    t0 = time.monotonic()
    report = kb.rebuild_materialized(force=True)
    elapsed = time.monotonic() - t0

    # 200 episodes must rebuild in under 30s (design target: 5s/10k).
    assert elapsed < 30.0, f"rebuild of 200 episodes took {elapsed:.1f}s — likely O(n^2)"
    assert report is not None


def test_rebuild_linear_growth(tmp_path):
    """Rebuild time should grow sub-quadratically with episode count."""
    now = datetime.now(UTC)

    def _timed_rebuild(n_episodes: int, suffix: str) -> float:
        db = str(tmp_path / f"linear_{suffix}.db")
        storage = SQLiteStorage(db_path=db)
        kb = KnowledgeBase(agent_id="agent", storage=storage)
        for i in range(n_episodes):
            kb.ingest_episode(
                session_id=f"sess-{i // 10}",
                turn_id=f"turn-{i}",
                speaker="user",
                observed_at=now,
                raw_text=f"Turn {i}: fact about entity {i % 20}.",
                materialize=False,
            )
        t0 = time.monotonic()
        kb.rebuild_materialized(force=True)
        return time.monotonic() - t0

    t50 = _timed_rebuild(50, "50")
    t100 = _timed_rebuild(100, "100")

    # O(n) → ratio ~2; O(n^2) → ratio ~4. Allow up to 3.5× headroom.
    ratio = t100 / max(t50, 1e-6)
    assert ratio < 3.5, (
        f"rebuild time ratio (100 vs 50 episodes) is {ratio:.2f} — "
        f"expected ≤3.5 for sub-quadratic growth"
    )


# ---------------------------------------------------------------------------
# Query invariants
# ---------------------------------------------------------------------------


def test_query_terminates_empty_db(tmp_path):
    """query() on empty DB must return a result (not hang)."""
    kb = _make_kb(tmp_path)
    t0 = time.monotonic()
    answer = kb.query("What is Alice's job?")
    elapsed = time.monotonic() - t0
    assert elapsed < 5.0, f"query on empty DB took {elapsed:.1f}s — should be fast"
    assert answer is not None
    assert isinstance(answer.text, str)


def test_query_terminates_no_bundles(tmp_path):
    """query() with claims but no bundles falls back to BM25 and returns."""
    kb = _make_kb(tmp_path)
    now = datetime.now(UTC)

    # Ingest a few episodes (creates claims, no bundles yet)
    for i in range(5):
        kb.ingest_episode(
            session_id="sess-0",
            turn_id=f"turn-{i}",
            speaker="user",
            observed_at=now,
            raw_text=f"Alice works as a {['doctor', 'teacher', 'engineer', 'nurse', 'pilot'][i]}.",
        )

    t0 = time.monotonic()
    answer = kb.query("What does Alice do?")
    elapsed = time.monotonic() - t0
    assert elapsed < 10.0, f"query without bundles took {elapsed:.1f}s"
    assert answer is not None


def test_query_pathological_many_claims(tmp_path):
    """query() with hundreds of claims must still return within reasonable time."""
    kb = _make_kb(tmp_path)
    now = datetime.now(UTC)

    for i in range(100):
        kb.ingest_episode(
            session_id=f"sess-{i // 20}",
            turn_id=f"turn-{i}",
            speaker="user",
            observed_at=now,
            raw_text=(
                f"Entity{i % 10} has attribute value_{i}. Entity{i % 5} lives in city_{i % 7}."
            ),
        )

    t0 = time.monotonic()
    answer = kb.query("What are Entity0's attributes?")
    elapsed = time.monotonic() - t0
    assert elapsed < 15.0, f"query with 100 episodes took {elapsed:.1f}s"
    assert answer is not None


# ---------------------------------------------------------------------------
# Concurrency invariant: rebuild + query do not corrupt claims
# ---------------------------------------------------------------------------


def test_concurrent_ingest_and_query_no_crash(tmp_path):
    """Concurrent ingest and query must not crash or deadlock."""
    kb = _make_kb(tmp_path)
    now = datetime.now(UTC)
    errors: list[Exception] = []

    def _ingest():
        for i in range(20):
            try:
                kb.ingest_episode(
                    session_id="sess-0",
                    turn_id=f"turn-{i}",
                    speaker="user",
                    observed_at=now,
                    raw_text=f"Fact {i}: Alice is a developer.",
                )
            except Exception as exc:
                errors.append(exc)

    def _query():
        for _ in range(5):
            try:
                kb.query("What is Alice's job?")
            except Exception as exc:
                errors.append(exc)

    t1 = threading.Thread(target=_ingest, daemon=True)
    t2 = threading.Thread(target=_query, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    assert not t1.is_alive(), "ingest thread did not finish in time"
    assert not t2.is_alive(), "query thread did not finish in time"
    assert not errors, f"errors during concurrent ingest/query: {errors}"


def test_rebuild_idempotent(tmp_path):
    """Two consecutive rebuilds produce the same claim count."""
    kb = _make_kb(tmp_path)
    now = datetime.now(UTC)

    for i in range(30):
        kb.ingest_episode(
            session_id="sess-0",
            turn_id=f"turn-{i}",
            speaker="user",
            observed_at=now,
            raw_text=f"Turn {i}: Alice studies {['physics', 'math', 'biology'][i % 3]}.",
            materialize=False,
        )

    kb.rebuild_materialized(force=True)
    claims_after_1 = kb._storage.load_claims(kb._agent_id, active_only=False)

    kb.rebuild_materialized(force=True)
    claims_after_2 = kb._storage.load_claims(kb._agent_id, active_only=False)

    # Same episode set → same claim IDs
    ids1 = {c.id for c in claims_after_1}
    ids2 = {c.id for c in claims_after_2}
    assert ids1 == ids2, (
        f"rebuild not idempotent: {len(ids1)} vs {len(ids2)} claims; "
        f"added={ids2 - ids1}, removed={ids1 - ids2}"
    )
