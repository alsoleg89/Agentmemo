"""Tests for SQLite storage backend."""

from __future__ import annotations

import pathlib
from datetime import UTC

import pytest

from ai_knot.storage.sqlite_storage import SQLiteStorage
from ai_knot.types import Fact, MemoryType


class TestSQLiteSaveLoad:
    """Basic save/load round-trip."""

    def test_save_and_load(self, sqlite_storage: SQLiteStorage, sample_facts: list[Fact]) -> None:
        sqlite_storage.save("agent1", sample_facts)
        loaded = sqlite_storage.load("agent1")
        assert len(loaded) == len(sample_facts)
        assert loaded[0].content == sample_facts[0].content

    def test_load_nonexistent_agent(self, sqlite_storage: SQLiteStorage) -> None:
        loaded = sqlite_storage.load("nonexistent")
        assert loaded == []

    def test_overwrite_replaces(self, sqlite_storage: SQLiteStorage) -> None:
        facts_v1 = [Fact(content="version 1")]
        facts_v2 = [Fact(content="version 2"), Fact(content="version 2b")]

        sqlite_storage.save("agent1", facts_v1)
        sqlite_storage.save("agent1", facts_v2)

        loaded = sqlite_storage.load("agent1")
        assert len(loaded) == 2

    def test_preserves_all_fields(self, sqlite_storage: SQLiteStorage) -> None:
        fact = Fact(
            content="Full field test",
            type=MemoryType.EPISODIC,
            importance=0.33,
            retention_score=0.66,
            access_count=7,
            tags=["x", "y"],
        )
        sqlite_storage.save("agent1", [fact])
        loaded = sqlite_storage.load("agent1")[0]

        assert loaded.content == fact.content
        assert loaded.type == fact.type
        assert loaded.importance == pytest.approx(fact.importance)
        assert loaded.retention_score == pytest.approx(fact.retention_score)
        assert loaded.access_count == fact.access_count
        assert loaded.tags == fact.tags
        assert loaded.id == fact.id


class TestSQLiteMultiAgent:
    """Multiple agents in the same database."""

    def test_agents_isolated(self, sqlite_storage: SQLiteStorage) -> None:
        sqlite_storage.save("alice", [Fact(content="Alice fact")])
        sqlite_storage.save("bob", [Fact(content="Bob fact")])

        alice_facts = sqlite_storage.load("alice")
        bob_facts = sqlite_storage.load("bob")

        assert len(alice_facts) == 1
        assert len(bob_facts) == 1
        assert alice_facts[0].content == "Alice fact"
        assert bob_facts[0].content == "Bob fact"

    def test_list_agents(self, sqlite_storage: SQLiteStorage) -> None:
        sqlite_storage.save("agent_a", [Fact(content="a")])
        sqlite_storage.save("agent_b", [Fact(content="b")])

        agents = sqlite_storage.list_agents()
        assert set(agents) == {"agent_a", "agent_b"}


class TestSQLiteDelete:
    """Deleting individual facts."""

    def test_delete_fact(self, sqlite_storage: SQLiteStorage) -> None:
        facts = [Fact(content="keep"), Fact(content="delete me")]
        sqlite_storage.save("agent1", facts)

        sqlite_storage.delete("agent1", facts[1].id)

        loaded = sqlite_storage.load("agent1")
        assert len(loaded) == 1
        assert loaded[0].content == "keep"

    def test_delete_nonexistent_fact(self, sqlite_storage: SQLiteStorage) -> None:
        sqlite_storage.save("agent1", [Fact(content="only")])
        sqlite_storage.delete("agent1", "nonexistent_id")
        loaded = sqlite_storage.load("agent1")
        assert len(loaded) == 1


class TestLoadActiveValidFrom:
    """load_active() must respect valid_from (P1 fix)."""

    def test_load_active_excludes_future_facts(self, sqlite_storage: SQLiteStorage) -> None:
        from datetime import UTC, datetime, timedelta

        future_fact = Fact(content="not yet active")
        future_fact.valid_from = datetime.now(UTC) + timedelta(hours=1)
        sqlite_storage.save("agent1", [future_fact])

        active = sqlite_storage.load_active("agent1")
        assert all(f.id != future_fact.id for f in active)

    def test_load_active_includes_past_valid_from(self, sqlite_storage: SQLiteStorage) -> None:
        from datetime import UTC, datetime, timedelta

        past_fact = Fact(content="already active")
        past_fact.valid_from = datetime.now(UTC) - timedelta(hours=1)
        sqlite_storage.save("agent1", [past_fact])

        active = sqlite_storage.load_active("agent1")
        assert any(f.id == past_fact.id for f in active)


class TestSaveAtomic:
    """save_atomic() correctness and concurrency."""

    def test_save_atomic_round_trip(self, sqlite_storage: SQLiteStorage) -> None:
        facts = [Fact(content="atomic fact A"), Fact(content="atomic fact B")]
        sqlite_storage.save_atomic("agent1", facts)
        loaded = sqlite_storage.load("agent1")
        contents = {f.content for f in loaded}
        assert contents == {"atomic fact A", "atomic fact B"}

    def test_save_atomic_replaces_all(self, sqlite_storage: SQLiteStorage) -> None:
        sqlite_storage.save_atomic("agent1", [Fact(content="v1")])
        sqlite_storage.save_atomic("agent1", [Fact(content="v2a"), Fact(content="v2b")])
        loaded = sqlite_storage.load("agent1")
        assert len(loaded) == 2
        assert all(f.content.startswith("v2") for f in loaded)

    def test_save_atomic_concurrent(self, tmp_dir: pathlib.Path) -> None:
        import threading

        db_path = str(tmp_dir / "concurrent.db")
        storage = SQLiteStorage(db_path=db_path)
        storage.save("agent1", [])
        storage.save("agent2", [])

        errors: list[Exception] = []

        def write(agent_id: str, content: str) -> None:
            try:
                storage.save_atomic(agent_id, [Fact(content=content)])
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=write, args=("agent1", "from thread 1"))
        t2 = threading.Thread(target=write, args=("agent2", "from thread 2"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        assert len(storage.load("agent1")) == 1
        assert len(storage.load("agent2")) == 1


class TestConnectionManagement:
    """_conn() context manager closes connections and emits no ResourceWarning."""

    def test_no_resource_warnings_on_repeated_ops(self, tmp_dir: pathlib.Path) -> None:
        import warnings

        db_path = str(tmp_dir / "leaks.db")
        storage = SQLiteStorage(db_path=db_path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for i in range(50):
                fact = Fact(content=f"fact {i}")
                storage.save("agent1", [fact])
                storage.load("agent1")
                storage.delete("agent1", fact.id)

        resource_warnings = [w for w in caught if issubclass(w.category, ResourceWarning)]
        assert resource_warnings == []


class TestSQLitePersistence:
    """Data survives across SQLiteStorage instances."""

    def test_data_persists_after_reopen(self, tmp_dir: pathlib.Path) -> None:
        db_path = str(tmp_dir / "persist.db")

        # Write with one instance
        storage1 = SQLiteStorage(db_path=db_path)
        storage1.save("agent1", [Fact(content="persistent")])

        # Read with a fresh instance
        storage2 = SQLiteStorage(db_path=db_path)
        loaded = storage2.load("agent1")

        assert len(loaded) == 1
        assert loaded[0].content == "persistent"


def test_search_episodes_window_ranks_cross_turn_match(tmp_path: object) -> None:
    """3-turn window BM25 must rank centre episode first when answer tokens span adjacent turns.

    Turn 0 contains context only; turn 1 contains the answer token "Zephyra";
    turn 2 contains noise. The query asks for "Zephyra".  Without windowing,
    turn 1 wins on its own anyway — but the hit must carry prev_id (turn 0)
    and next_id (turn 2) so the runtime can enrich evidence_text with neighbours.
    """
    from datetime import UTC, datetime

    from ai_knot.storage.sqlite_storage import EpisodeHit, SQLiteStorage

    storage = SQLiteStorage(db_path=str(tmp_path / "t.db"), embed_url="")  # type: ignore[operator]
    t0 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
    t1 = datetime(2024, 1, 1, 10, 1, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 1, 10, 2, 0, tzinfo=UTC)

    from ai_knot.knowledge import KnowledgeBase

    kb = KnowledgeBase(agent_id="a", storage=storage)
    kb.ingest_episode(
        session_id="s",
        turn_id="turn-0",
        speaker="Alice",
        observed_at=t0,
        raw_text="Alice: We talked about many things.",
    )
    kb.ingest_episode(
        session_id="s",
        turn_id="turn-1",
        speaker="Bob",
        observed_at=t1,
        raw_text="Bob: Yes, Zephyra was the main topic.",
    )
    kb.ingest_episode(
        session_id="s",
        turn_id="turn-2",
        speaker="Alice",
        observed_at=t2,
        raw_text="Alice: Right, I remember that.",
    )

    hits = storage.search_episodes_by_entities(
        "a", ["Alice", "Bob"], query="What is Zephyra?", top_k=3
    )

    assert hits, "expected at least one hit"
    top = hits[0]
    assert isinstance(top, EpisodeHit)
    # Centre must be the turn that contains "Zephyra"
    assert "Zephyra" in top.raw_text
    # Neighbours must be populated (session has 3 episodes)
    assert top.prev_id is not None, "prev_id must be set for a middle episode"
    assert top.next_id is not None, "next_id must be set for a middle episode"


def test_search_episodes_centre_beats_window(tmp_path: object) -> None:
    """Sub-step A: exact-match on centre text must outscore a neighbour-diluted candidate."""
    from datetime import datetime

    from ai_knot.query_types import RawEpisode
    from ai_knot.storage.sqlite_storage import SQLiteStorage

    storage = SQLiteStorage(str(tmp_path / "test.db"), embed_url="")  # type: ignore[operator]

    def ep(id_: str, session: str, turn: int, text: str) -> RawEpisode:
        return RawEpisode(
            id=id_,
            agent_id="agent1",
            session_id=session,
            turn_id=f"{session}-{turn}",
            speaker="user",
            observed_at=datetime(2024, 1, turn, tzinfo=UTC),
            session_date=None,
            raw_text=text,
            source_meta={},
            parent_episode_id=None,
        )

    storage.save_episodes(
        "agent1",
        [
            ep("s1_prev", "sess1", 1, "Alice went to Paris for vacation last month."),
            ep("s1_center", "sess1", 2, "Alice lives in Paris now."),  # exact answer
            ep("s1_next", "sess1", 3, "She loves the Eiffel Tower."),
            # sess2: Alice is mentioned in centre but answer is only in neighbour
            ep(
                "s2_prev", "sess2", 1, "Alice mentioned she had been to Paris."
            ),  # neighbour has answer tokens
            ep(
                "s2_center", "sess2", 2, "Alice went to the grocery store."
            ),  # noisy centre, no answer tokens
            ep("s2_next", "sess2", 3, "Alice bought croissants there."),
        ],
    )

    hits = storage.search_episodes_by_entities(
        "agent1", ["Alice"], query="Where does Alice live?", top_k=5
    )
    ids = [h.id for h in hits]
    # Both s1_center and s2_center must appear (both mention Alice).
    assert "s1_center" in ids, f"s1_center missing from results: {ids}"
    assert "s2_center" in ids, f"s2_center missing from results: {ids}"
    assert ids.index("s1_center") < ids.index("s2_center"), (
        "Centre-strong match 's1_center' must rank above neighbour-diluted 's2_center'"
    )


def test_search_episodes_hybrid_semantic_gap(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sub-step B: stub embedder makes semantic match win when BM25 cannot."""

    from datetime import datetime

    import ai_knot.embedder as _embedder_mod
    from ai_knot.query_types import RawEpisode
    from ai_knot.storage.sqlite_storage import SQLiteStorage

    storage = SQLiteStorage(
        str(tmp_path / "test.db"),  # type: ignore[operator]
        embed_url="http://fake-embed",
        embed_model="test-model",
    )

    def ep(id_: str, text: str) -> RawEpisode:
        return RawEpisode(
            id=id_,
            agent_id="agent1",
            session_id="sess1",
            turn_id=f"sess1-{id_}",
            speaker="user",
            observed_at=datetime(2024, 1, 1, tzinfo=UTC),
            session_date=None,
            raw_text=text,
            source_meta={},
            parent_episode_id=None,
        )

    storage.save_episodes(
        "agent1",
        [
            ep("ep_bm25", "Alice works at Google."),  # BM25 match on "works"
            ep("ep_semantic", "Alice is employed by Google."),  # semantic match, no BM25 on "job"
        ],
    )

    # Stub embedder: ep_semantic is closer to the query vector than ep_bm25.
    # query=[1,0], ep_semantic=[0.9,0.1], ep_bm25=[0.1,0.9]
    async def fake_embed(
        texts: list[str],
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> list[list[float]]:
        vectors = {
            "Alice works at Google.": [0.1, 0.9],
            "Alice is employed by Google.": [0.9, 0.1],
        }
        return [vectors.get(t, [0.5, 0.5]) for t in texts]

    monkeypatch.setattr(_embedder_mod, "embed_texts", fake_embed)

    hits = storage.search_episodes_by_entities(
        "agent1", ["Alice"], query="What is Alice's job?", top_k=2
    )
    ids = [h.id for h in hits]
    # ep_semantic should appear in results because of hybrid fusion
    assert "ep_semantic" in ids, f"Semantic match missing from hybrid results: {ids}"
