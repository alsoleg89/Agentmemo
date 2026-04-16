"""SQLite migration v3: add embedding columns to raw_episodes and atomic_claims."""

from __future__ import annotations

import sqlite3


def apply_v3_migration(conn: sqlite3.Connection) -> None:
    """Add embedding / embedding_model columns to raw_episodes and atomic_claims.

    Idempotent: uses PRAGMA table_info guard before each ALTER TABLE.
    """
    for table in ("raw_episodes", "atomic_claims"):
        cur = conn.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}
        if "embedding" not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN embedding BLOB")
        if "embedding_model" not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN embedding_model TEXT")
