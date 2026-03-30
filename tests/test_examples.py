"""Tests for README examples — run without LLM API keys."""

from __future__ import annotations

import asyncio
import pathlib
from unittest.mock import patch

import pytest

from ai_knot import KnowledgeBase, MemoryType
from ai_knot.storage import SQLiteStorage, YAMLStorage, create_storage
from ai_knot.types import ConversationTurn


@pytest.fixture
def kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    return KnowledgeBase(agent_id="test", storage=YAMLStorage(base_dir=str(tmp_path)))


def test_example1_manual_add_recall(kb: KnowledgeBase) -> None:
    kb.add("User prefers Python", type=MemoryType.PROCEDURAL, importance=0.9)
    kb.add("User deploys with Docker", importance=0.85)
    kb.add("Deploy failed last Tuesday", type=MemoryType.EPISODIC, importance=0.4)

    context = kb.recall("how to deploy?")
    assert isinstance(context, str)
    assert "Docker" in context


def test_example2_sqlite_init(tmp_path: pathlib.Path) -> None:
    storage = SQLiteStorage(db_path=str(tmp_path / "bot.db"))
    kb = KnowledgeBase(agent_id="bot", storage=storage)
    kb.add("User works with Python and FastAPI")
    context = kb.recall("what stack does user use?")
    assert "FastAPI" in context


def test_example3_yaml_init(tmp_path: pathlib.Path) -> None:
    storage = YAMLStorage(base_dir=str(tmp_path))
    kb = KnowledgeBase(agent_id="bot", storage=storage)
    kb.add("Always write tests with pytest", type=MemoryType.PROCEDURAL)
    context = kb.recall("testing preferences")
    assert "pytest" in context


@pytest.mark.parametrize("backend", ["yaml", "sqlite"])
def test_example4_create_storage_factory(tmp_path: pathlib.Path, backend: str) -> None:
    storage = create_storage(backend, base_dir=str(tmp_path))
    kb = KnowledgeBase(agent_id="assistant", storage=storage)
    kb.add("Prefer concise answers", type=MemoryType.PROCEDURAL)
    assert kb.stats()["total_facts"] == 1


def test_example5_per_customer(tmp_path: pathlib.Path) -> None:
    def handle_ticket(customer_id: str, message: str) -> str:
        kb = KnowledgeBase(
            agent_id=f"customer_{customer_id}",
            storage=YAMLStorage(base_dir=str(tmp_path)),
        )
        return kb.recall(message)

    # Seed customer facts
    kb = KnowledgeBase(
        agent_id="customer_123",
        storage=YAMLStorage(base_dir=str(tmp_path)),
    )
    kb.add("Customer prefers email notifications")
    kb.add("Customer is on premium tier")

    result = handle_ticket("123", "notification preferences")
    assert isinstance(result, str)
    assert "email" in result.lower() or "notification" in result.lower()


def test_example6_project_context(tmp_path: pathlib.Path) -> None:
    kb = KnowledgeBase(agent_id="project", storage=YAMLStorage(str(tmp_path)))
    kb.add("Stack: FastAPI + PostgreSQL + Docker", importance=1.0)
    kb.add("No unittest — use pytest only", type=MemoryType.PROCEDURAL, importance=0.9)
    kb.add("All endpoints require JWT auth", importance=0.95)

    context = kb.recall("how should I write tests?")
    assert "pytest" in context


def test_example7_shared_knowledge(tmp_path: pathlib.Path) -> None:
    storage = SQLiteStorage(db_path=str(tmp_path / "team.db"))
    researcher = KnowledgeBase(agent_id="team_alpha", storage=storage)
    writer = KnowledgeBase(agent_id="team_alpha", storage=storage)

    researcher.add("API rate limit is 100 req/s")
    context = writer.recall("rate limits")
    assert "100" in context or "rate" in context.lower()


def test_example8_stats_and_decay(kb: KnowledgeBase) -> None:
    kb.add("User likes dark mode")
    kb.add("User timezone is UTC+3")

    stats = kb.stats()
    assert stats["total_facts"] == 2
    assert "avg_importance" in stats
    assert "avg_retention" in stats
    assert "by_type" in stats

    kb.decay()  # should not raise


def test_recall_does_not_need_provider(kb: KnowledgeBase) -> None:
    kb.add("User deploys everything in Docker")
    context = kb.recall("how should I deploy this?")
    assert "Docker" in context


# ── v0.4.0 examples ───────────────────────────────────────────────────────────


def test_example9_add_many(tmp_path: pathlib.Path) -> None:
    """add_many() inserts a batch of facts without an LLM call."""
    kb = KnowledgeBase(agent_id="bot", storage=YAMLStorage(base_dir=str(tmp_path)))

    # Plain strings use method-level defaults.
    facts = kb.add_many(["User deploys on Fridays", "User uses Docker"])
    assert len(facts) == 2
    assert all(f.type == MemoryType.SEMANTIC for f in facts)

    # Dicts allow per-fact control.
    facts2 = kb.add_many(
        [
            {"content": "Always use type hints", "type": "procedural", "importance": 0.9},
            {"content": "Sprint demo on Monday", "type": "episodic", "importance": 0.6},
        ]
    )
    assert facts2[0].type == MemoryType.PROCEDURAL
    assert pytest.approx(facts2[0].importance) == 0.9
    assert facts2[1].type == MemoryType.EPISODIC

    # All four facts were persisted in a single load+save.
    assert kb.stats()["total_facts"] == 4

    # Recall works normally over batch-inserted facts.
    context = kb.recall("deployment schedule")
    assert isinstance(context, str)


def test_example10_provider_at_init(tmp_path: pathlib.Path) -> None:
    """Provider credentials set at __init__ are used as defaults for learn()."""
    kb = KnowledgeBase(
        agent_id="bot",
        storage=YAMLStorage(base_dir=str(tmp_path)),
        provider="openai",
        api_key="sk-test",
    )
    turns = [ConversationTurn(role="user", content="I deploy everything in Docker")]

    # learn() uses init-time provider — no api_key= needed per call.
    with patch("ai_knot.extractor.Extractor._call_llm", return_value=[]):
        result = kb.learn(turns)
    assert result == []

    # Per-call values still override init-time defaults.
    with patch("ai_knot.extractor.Extractor._call_llm", return_value=[]):
        result2 = kb.learn(turns, provider="anthropic", api_key="sk-ant-other")
    assert result2 == []


def test_example11_async_api(tmp_path: pathlib.Path) -> None:
    """arecall / arecall_facts are non-blocking async wrappers over sync methods."""
    kb = KnowledgeBase(agent_id="bot", storage=YAMLStorage(base_dir=str(tmp_path)))
    kb.add("User prefers Python")
    kb.add("User deploys on Kubernetes")

    # arecall returns the same string as recall.
    context = asyncio.run(kb.arecall("deployment"))
    assert isinstance(context, str)
    assert len(context) > 0

    # arecall_facts returns Fact objects.
    facts = asyncio.run(kb.arecall_facts("language"))
    assert isinstance(facts, list)

    # alearn with mocked extractor — does not block the event loop.
    turns = [ConversationTurn(role="user", content="I use FastAPI")]
    with patch("ai_knot.extractor.Extractor._call_llm", return_value=[]):
        result = asyncio.run(kb.alearn(turns, provider="openai", api_key="sk-test"))
    assert result == []


def test_example12_scored_retrieval(tmp_path: pathlib.Path) -> None:
    """recall_facts_with_scores() returns (Fact, float) pairs with a hybrid score."""
    kb = KnowledgeBase(agent_id="bot", storage=YAMLStorage(base_dir=str(tmp_path)))
    kb.add("User deploys everything in Docker", importance=0.9)
    kb.add("User prefers Python over Java", type=MemoryType.PROCEDURAL, importance=0.8)
    kb.add("User works at Acme Corp", importance=0.7)

    scored = kb.recall_facts_with_scores("Docker deployment", top_k=3)

    assert len(scored) >= 1
    for fact, score in scored:
        assert score >= 0.0
        assert isinstance(fact.content, str)

    # Scores are sorted descending.
    scores = [s for _, s in scored]
    assert scores == sorted(scores, reverse=True)

    # Threshold-based filtering works as a one-liner.
    relevant = [fact for fact, score in scored if score >= 0.1]
    assert len(relevant) >= 1
