"""SQLite schema migration v2: raw_episodes / atomic_claims / support_bundles.

Idempotent: uses CREATE TABLE IF NOT EXISTS throughout.
Does NOT create the manifests table — that is Track B (v3_manifest_plane.py).

schema_version=2 is written into materialization_meta after a successful
apply, so the migration is not re-run on subsequent startups.
"""

from __future__ import annotations

import sqlite3

# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------

_RAW_EPISODES_TABLE = """
CREATE TABLE IF NOT EXISTS raw_episodes (
    id                TEXT NOT NULL,
    agent_id          TEXT NOT NULL,
    session_id        TEXT NOT NULL,
    turn_id           TEXT NOT NULL,
    speaker           TEXT NOT NULL,
    observed_at       TEXT NOT NULL,
    session_date      TEXT,
    raw_text          TEXT NOT NULL,
    source_meta       TEXT NOT NULL DEFAULT '{}',
    parent_episode_id TEXT,
    PRIMARY KEY (agent_id, id)
)
"""

_RAW_EPISODES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_raw_session ON raw_episodes(agent_id, session_id, observed_at)",
    "CREATE INDEX IF NOT EXISTS idx_raw_parent   ON raw_episodes(agent_id, parent_episode_id)",
]

_ATOMIC_CLAIMS_TABLE = """
CREATE TABLE IF NOT EXISTS atomic_claims (
    id                       TEXT NOT NULL,
    agent_id                 TEXT NOT NULL,
    kind                     TEXT NOT NULL,
    subject                  TEXT NOT NULL,
    relation                 TEXT NOT NULL,
    value_text               TEXT NOT NULL,
    value_tokens             TEXT NOT NULL DEFAULT '[]',
    qualifiers               TEXT NOT NULL DEFAULT '{}',
    polarity                 TEXT NOT NULL DEFAULT 'support',
    event_time               TEXT,
    observed_at              TEXT NOT NULL,
    valid_from               TEXT NOT NULL,
    valid_until              TEXT,
    confidence               REAL NOT NULL DEFAULT 1.0,
    salience                 REAL NOT NULL DEFAULT 1.0,
    source_episode_id        TEXT NOT NULL,
    source_spans             TEXT NOT NULL DEFAULT '[]',
    materialization_version  INTEGER NOT NULL DEFAULT 1,
    materialized_at          TEXT NOT NULL,
    slot_key                 TEXT NOT NULL DEFAULT '',
    version                  INTEGER NOT NULL DEFAULT 0,
    origin_agent_id          TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (agent_id, id)
)
"""

_ATOMIC_CLAIMS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_claim_entity  ON atomic_claims(agent_id, subject, relation)",
    "CREATE INDEX IF NOT EXISTS idx_claim_kind    ON atomic_claims(agent_id, kind)",
    "CREATE INDEX IF NOT EXISTS idx_claim_source  ON atomic_claims(agent_id, source_episode_id)",
    "CREATE INDEX IF NOT EXISTS idx_claim_slot ON atomic_claims(agent_id, slot_key, valid_until)",
    "CREATE INDEX IF NOT EXISTS idx_claim_event   ON atomic_claims(agent_id, event_time)",
]

_SUPPORT_BUNDLES_TABLE = """
CREATE TABLE IF NOT EXISTS support_bundles (
    id                                TEXT NOT NULL,
    agent_id                          TEXT NOT NULL,
    kind                              TEXT NOT NULL,
    topic                             TEXT NOT NULL,
    bundle_score                      REAL NOT NULL DEFAULT 0.0,
    score_formula                     TEXT NOT NULL DEFAULT '',
    built_from_materialization_version INTEGER NOT NULL DEFAULT 0,
    built_at                          TEXT NOT NULL,
    PRIMARY KEY (agent_id, id)
)
"""

_SUPPORT_BUNDLES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_bundle_topic ON support_bundles(agent_id, topic, kind)",
    "CREATE INDEX IF NOT EXISTS idx_bundle_kind  ON support_bundles(agent_id, kind)",
]

_BUNDLE_MEMBERS_TABLE = """
CREATE TABLE IF NOT EXISTS bundle_members (
    agent_id    TEXT NOT NULL,
    bundle_id   TEXT NOT NULL,
    claim_id    TEXT NOT NULL,
    member_rank INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (agent_id, bundle_id, claim_id)
)
"""

_BUNDLE_MEMBERS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_bm_claim ON bundle_members(agent_id, claim_id)",
]

_MATERIALIZATION_META_TABLE = """
CREATE TABLE IF NOT EXISTS materialization_meta (
    agent_id                 TEXT NOT NULL PRIMARY KEY,
    schema_version           INTEGER NOT NULL DEFAULT 2,
    materialization_version  INTEGER NOT NULL DEFAULT 0,
    last_rebuild_at          TEXT,
    dirty_keys_json          TEXT NOT NULL DEFAULT '[]',
    rebuild_status           TEXT NOT NULL DEFAULT 'ready'
)
"""


def apply_v2_migration(conn: sqlite3.Connection) -> None:
    """Apply v2 schema to an open SQLite connection.

    Safe to call multiple times — all DDL uses IF NOT EXISTS.
    Call within an existing transaction or let this function manage it.
    """
    for ddl in [
        _RAW_EPISODES_TABLE,
        _ATOMIC_CLAIMS_TABLE,
        _SUPPORT_BUNDLES_TABLE,
        _BUNDLE_MEMBERS_TABLE,
        _MATERIALIZATION_META_TABLE,
    ]:
        conn.execute(ddl)

    for stmt in (
        _RAW_EPISODES_INDEXES
        + _ATOMIC_CLAIMS_INDEXES
        + _SUPPORT_BUNDLES_INDEXES
        + _BUNDLE_MEMBERS_INDEXES
    ):
        conn.execute(stmt)
