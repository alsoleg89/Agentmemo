"""Regression tests for speaker-prefix BM25 boost in search_episodes_by_entities.

LOCOMO-style corpora prefix every turn with ``<Name>: ...``.  The speaker-
prefix boost lifts turns where the speaker matches a focus entity, so that
a focus entity's own statements rank above mere mentions by the counterparty.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from ai_knot.query_types import RawEpisode, make_episode_id
from ai_knot.storage.sqlite_storage import (
    SQLiteStorage,
    _speaker_prefix_boost,
)


@pytest.fixture
def tmp_store(tmp_path: Path) -> SQLiteStorage:
    db = tmp_path / "knot.db"
    store = SQLiteStorage(
        str(db),
        embed_url="",  # disable embeddings for deterministic BM25-only ranking
        embed_model="",
    )
    return store


def test_boost_returns_1_when_no_match() -> None:
    assert _speaker_prefix_boost("Jon: Hi there", ("Melanie",)) == 1.0
    assert _speaker_prefix_boost("Gina: Hey Jon", ("Jon",)) == 1.0


def test_boost_applies_when_speaker_matches_entity() -> None:
    boost = _speaker_prefix_boost("Jon: Took a trip to Rome.", ("Jon",))
    assert boost > 1.0
    assert boost == float(os.environ.get("AI_KNOT_SPEAKER_PREFIX_BOOST", "1.5"))


def test_boost_handles_empty_text() -> None:
    assert _speaker_prefix_boost("", ("Jon",)) == 1.0


def test_boost_handles_empty_entities() -> None:
    assert _speaker_prefix_boost("Jon: Hi", ()) == 1.0


def test_boost_is_case_sensitive_prefix_match() -> None:
    # Jon: matches "Jon" entity; "jonathan:" does not (different name).
    assert _speaker_prefix_boost("Jonathan: Hi", ("Jon",)) == 1.0
    assert _speaker_prefix_boost("jon: Hi", ("Jon",)) == 1.0  # lowercase speaker != "Jon"


def test_boost_checks_any_entity_in_list() -> None:
    b = _speaker_prefix_boost("Gina: Hi Jon", ("Jon", "Gina"))
    assert b > 1.0  # Gina-speaker matches the Gina entity


def test_boost_respects_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_KNOT_SPEAKER_PREFIX_BOOST", "2.0")
    assert _speaker_prefix_boost("Jon: Hi", ("Jon",)) == 2.0


def _ep(
    store: SQLiteStorage,
    agent_id: str,
    session_id: str,
    turn_id: str,
    speaker_role: str,
    raw_text: str,
    observed_at: datetime,
) -> None:
    store.save_episodes(
        agent_id,
        [
            RawEpisode(
                id=make_episode_id(agent_id, session_id, turn_id),
                agent_id=agent_id,
                session_id=session_id,
                turn_id=turn_id,
                speaker=speaker_role,
                observed_at=observed_at,
                raw_text=raw_text,
                session_date=observed_at,
            )
        ],
    )


def test_speaker_anchored_turn_outranks_counterparty_mention(
    tmp_store: SQLiteStorage,
) -> None:
    """Jon-speaker 'trip' turn should outrank Gina-speaker 'Jon' mention for 'Jon' Q.

    Without boost BM25 alone would tie-break by recency — boost ensures the
    name-prefixed speaker turn wins even when BM25 scores are comparable.
    """
    agent = "test-conv"
    base = datetime(2026, 1, 1, 12, 0, 0)
    _ep(
        tmp_store,
        agent,
        "sess-1",
        "turn-0",
        "user",
        "Gina: Hey Jon, how was the conference you talked about last week?",
        base,
    )
    _ep(
        tmp_store,
        agent,
        "sess-1",
        "turn-1",
        "assistant",
        "Jon: Great conference last week, I gave a talk about architecture.",
        base.replace(hour=12, minute=1),
    )
    _ep(
        tmp_store,
        agent,
        "sess-1",
        "turn-2",
        "user",
        "Gina: That's cool. What else is Jon up to?",
        base.replace(hour=12, minute=2),
    )

    hits = tmp_store.search_episodes_by_entities(
        agent,
        ("Jon",),
        query="What did Jon talk about at the conference?",
        top_k=3,
    )
    assert len(hits) >= 1
    assert hits[0].raw_text.startswith("Jon:"), (
        f"expected Jon-speaker turn first, got: {hits[0].raw_text[:60]}"
    )


def test_boost_disabled_does_not_rerank(
    tmp_store: SQLiteStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Setting AI_KNOT_SPEAKER_PREFIX_BOOST=1.0 disables the boost cleanly."""
    monkeypatch.setenv("AI_KNOT_SPEAKER_PREFIX_BOOST", "1.0")
    agent = "test-conv-2"
    base = datetime(2026, 1, 1, 12, 0, 0)
    # Counterparty mention with stronger BM25 match for "trip":
    _ep(
        tmp_store,
        agent,
        "sess-1",
        "turn-0",
        "user",
        "Gina: That trip you took sounds wonderful Jon — tell me about the trip!",
        base,
    )
    _ep(
        tmp_store,
        agent,
        "sess-1",
        "turn-1",
        "assistant",
        "Jon: Yeah, went to Rome briefly.",
        base.replace(hour=12, minute=1),
    )
    hits = tmp_store.search_episodes_by_entities(
        agent,
        ("Jon",),
        query="Tell me about the trip",
        top_k=2,
    )
    # With boost disabled the counterparty 'trip trip' turn wins on raw BM25
    assert hits[0].raw_text.startswith("Gina:")


def test_boost_enabled_elevates_speaker_turn(tmp_store: SQLiteStorage) -> None:
    """With default boost, Jon-speaker Rome turn should outrank counterparty trip mention."""
    agent = "test-conv-3"
    base = datetime(2026, 1, 1, 12, 0, 0)
    _ep(
        tmp_store,
        agent,
        "sess-1",
        "turn-0",
        "user",
        "Gina: That trip you took sounds wonderful Jon — tell me about the trip!",
        base,
    )
    _ep(
        tmp_store,
        agent,
        "sess-1",
        "turn-1",
        "assistant",
        "Jon: Yeah, the trip to Rome was great.",
        base.replace(hour=12, minute=1),
    )
    hits = tmp_store.search_episodes_by_entities(
        agent,
        ("Jon",),
        query="Tell me about the trip",
        top_k=2,
    )
    assert hits[0].raw_text.startswith("Jon:"), (
        f"expected Jon-speaker turn first with boost, got: {hits[0].raw_text[:60]}"
    )
