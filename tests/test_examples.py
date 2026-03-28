"""Tests for README examples — run without LLM API keys."""
import pathlib

import pytest

from agentmemo import KnowledgeBase, MemoryType
from agentmemo.storage import SQLiteStorage, YAMLStorage, create_storage


@pytest.fixture
def kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    return KnowledgeBase(agent_id="test", storage=YAMLStorage(base_dir=str(tmp_path)))


@pytest.fixture
def sqlite_kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    return KnowledgeBase(
        agent_id="test",
        storage=SQLiteStorage(db_path=str(tmp_path / "test.db")),
    )


# --- Example 1: Manual add + recall ---


def test_example1_manual_add_recall(kb: KnowledgeBase) -> None:
    kb.add("User prefers Python", type=MemoryType.PROCEDURAL, importance=0.9)
    kb.add("User deploys with Docker", importance=0.85)
    kb.add("Deploy failed last Tuesday", type=MemoryType.EPISODIC, importance=0.4)

    context = kb.recall("how to deploy?")
    assert isinstance(context, str)
    assert "Docker" in context


# --- Example 2: SQLite storage init ---


def test_example2_sqlite_init(tmp_path: pathlib.Path) -> None:
    storage = SQLiteStorage(db_path=str(tmp_path / "bot.db"))
    kb = KnowledgeBase(agent_id="bot", storage=storage)
    kb.add("User works with Python and FastAPI")
    context = kb.recall("what stack does user use?")
    assert "FastAPI" in context


# --- Example 3: YAML storage init ---


def test_example3_yaml_init(tmp_path: pathlib.Path) -> None:
    storage = YAMLStorage(base_dir=str(tmp_path))
    kb = KnowledgeBase(agent_id="bot", storage=storage)
    kb.add("Always write tests with pytest", type=MemoryType.PROCEDURAL)
    context = kb.recall("testing preferences")
    assert "pytest" in context


# --- Example 4: create_storage factory ---


def test_example4_create_storage_yaml(tmp_path: pathlib.Path) -> None:
    storage = create_storage("yaml", base_dir=str(tmp_path))
    kb = KnowledgeBase(agent_id="assistant", storage=storage)
    kb.add("Prefer concise answers", type=MemoryType.PROCEDURAL)
    assert kb.stats()["total_facts"] == 1


def test_example4_create_storage_sqlite(tmp_path: pathlib.Path) -> None:
    storage = create_storage("sqlite", base_dir=str(tmp_path))
    kb = KnowledgeBase(agent_id="assistant", storage=storage)
    kb.add("Prefer concise answers", type=MemoryType.PROCEDURAL)
    assert kb.stats()["total_facts"] == 1


# --- Example 5: Per-customer knowledge ---


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


# --- Example 6: Coding agent with project context ---


def test_example6_project_context(tmp_path: pathlib.Path) -> None:
    kb = KnowledgeBase(agent_id="project", storage=YAMLStorage(str(tmp_path)))
    kb.add("Stack: FastAPI + PostgreSQL + Docker", importance=1.0)
    kb.add("No unittest — use pytest only", type=MemoryType.PROCEDURAL, importance=0.9)
    kb.add("All endpoints require JWT auth", importance=0.95)

    context = kb.recall("how should I write tests?")
    assert "pytest" in context


# --- Example 7: Shared knowledge across agents ---


def test_example7_shared_knowledge(tmp_path: pathlib.Path) -> None:
    storage = SQLiteStorage(db_path=str(tmp_path / "team.db"))
    researcher = KnowledgeBase(agent_id="team_alpha", storage=storage)
    writer = KnowledgeBase(agent_id="team_alpha", storage=storage)

    researcher.add("API rate limit is 100 req/s")
    context = writer.recall("rate limits")
    assert "100" in context or "rate" in context.lower()


# --- Example 8: Stats and decay ---


def test_example8_stats_and_decay(kb: KnowledgeBase) -> None:
    kb.add("User likes dark mode")
    kb.add("User timezone is UTC+3")

    stats = kb.stats()
    assert stats["total_facts"] == 2
    assert "avg_importance" in stats
    assert "avg_retention" in stats
    assert "by_type" in stats

    kb.decay()  # should not raise


# --- Initialization: recall never needs a provider ---


def test_recall_does_not_need_provider(kb: KnowledgeBase) -> None:
    kb.add("User deploys everything in Docker")
    context = kb.recall("how should I deploy this?")
    assert "Docker" in context
