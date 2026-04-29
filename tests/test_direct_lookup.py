"""Tests for DirectLookup — entity-filtered + cosine-ranked retrieval channel."""

from __future__ import annotations

import math
import pathlib

import pytest

import ai_knot.knowledge as _kb_module
from ai_knot._direct_lookup import DirectLookup, extract_all_entities
from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.yaml_storage import YAMLStorage

# ─── extract_all_entities ────────────────────────────────────────────────────


def test_extract_single_entity() -> None:
    assert extract_all_entities("What did Caroline research?") == ["Caroline"]


def test_extract_multi_entity() -> None:
    result = extract_all_entities("What do Jon and Gina both have in common?")
    assert "Jon" in result
    assert "Gina" in result


def test_extract_no_entity() -> None:
    assert extract_all_entities("what time is it?") == []


def test_extract_skips_question_words() -> None:
    result = extract_all_entities("When did What happen?")
    # "When" and "What" are in _WH_SKIP, must not appear
    assert "When" not in result
    assert "What" not in result


def test_extract_returns_sorted_unique() -> None:
    result = extract_all_entities("What does Jon and Jon and Gina share?")
    # Deduplicated and sorted
    assert result == sorted(set(result))
    assert result.count("Jon") == 1


# ─── DirectLookup ────────────────────────────────────────────────────────────


def _make_fake_vec(tag: float, dim: int = 8) -> list[float]:
    """Simple normalised vector: concentrated on first dim."""
    v = [0.0] * dim
    v[0] = tag
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


@pytest.fixture
def kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    storage = YAMLStorage(base_dir=str(tmp_path))
    return KnowledgeBase(agent_id="dl_test", storage=storage)


class TestDirectLookupUnit:
    def _make_lookup(self, top_k: int = 3) -> DirectLookup:
        return DirectLookup(top_k=top_k)

    def _make_fact(self, fid: str, content: str) -> object:
        """Return a minimal Fact-like object for unit testing."""
        from ai_knot.types import Fact, MemoryType

        f = Fact.__new__(Fact)
        f.id = fid
        f.content = content
        f.entity = ""
        f.attribute = ""
        f.value_text = ""
        f.prompt_surface = ""
        f.source_verbatim = ""
        f.type = MemoryType.SEMANTIC
        return f  # type: ignore[return-value]

    def test_no_entity_returns_empty(self) -> None:
        dl = self._make_lookup()
        facts = [self._make_fact("f1", "Some random fact.")]
        result, trace = dl.lookup(_make_fake_vec(1.0), "what time is it?", facts, {})
        assert result == {}
        assert trace["applied"] is False
        assert trace["reason"] == "no_entity"

    def test_entity_matched_by_substring(self) -> None:
        dl = self._make_lookup(top_k=5)
        facts = [
            self._make_fact("f1", "Caroline went hiking."),
            self._make_fact("f2", "Melanie loves painting."),
            self._make_fact("f3", "Caroline joined a group."),
        ]
        q_vec = _make_fake_vec(1.0)
        dense = {"f1": _make_fake_vec(0.9), "f2": _make_fake_vec(0.5), "f3": _make_fake_vec(0.8)}
        result, trace = dl.lookup(q_vec, "What did Caroline do?", facts, dense)

        assert "Caroline" in result
        # Should NOT include Melanie (different entity)
        assert "Melanie" not in result
        caroline_ids = [f.id for f in result["Caroline"]]
        assert "f1" in caroline_ids
        assert "f3" in caroline_ids
        assert "f2" not in caroline_ids
        assert trace["applied"] is True

    def test_top_k_limits_per_entity(self) -> None:
        dl = self._make_lookup(top_k=2)
        facts = [self._make_fact(f"f{i}", f"Alice fact {i}.") for i in range(10)]
        # Use i+1 to avoid zero vectors (zero norm causes ZeroDivisionError in cosine)
        dense = {f"f{i}": _make_fake_vec(float(i + 1) / 10) for i in range(10)}
        result, _ = dl.lookup(_make_fake_vec(1.0), "What has Alice done?", facts, dense)
        assert "Alice" in result
        assert len(result["Alice"]) == 2

    def test_multi_entity_dedup(self) -> None:
        dl = self._make_lookup(top_k=3)
        facts = [
            self._make_fact("f1", "Jon and Gina both danced."),
            self._make_fact("f2", "Jon loves music."),
            self._make_fact("f3", "Gina runs a store."),
        ]
        dense = {f.id: _make_fake_vec(0.8) for f in facts}
        result, trace = dl.lookup(
            _make_fake_vec(1.0),
            "What do Jon and Gina have in common?",
            facts,
            dense,
        )
        # Both entities found
        assert "Jon" in result
        assert "Gina" in result
        # f1 matches both entities; first entity (alphabetical: Gina) wins dedup
        jon_ids = {f.id for f in result["Jon"]}
        gina_ids = {f.id for f in result["Gina"]}
        assert jon_ids.isdisjoint(gina_ids), "No fact should appear in both entity groups"
        assert trace["applied"] is True


class TestDirectLookupIntegration:
    """Integration: DirectLookup channel in KnowledgeBase._execute_recall."""

    def test_flag_off_no_direct_lookup(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_kb_module, "_DIRECT_LOOKUP_ENABLED", False)
        kb._direct_lookup = None
        for i in range(5):
            kb.add(f"Alice activity {i}.")
        _, _, trace = kb.recall_with_trace("What has Alice done?", top_k=3)
        dl_trace = trace.get("stage_direct_lookup", {})
        assert dl_trace.get("applied") is False

    def test_flag_on_produces_trace(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_kb_module, "_DIRECT_LOOKUP_ENABLED", True)
        kb._direct_lookup = DirectLookup(top_k=4)
        for i in range(6):
            kb.add(f"Bob went hiking on day {i}.")
        _, _, trace = kb.recall_with_trace("What has Bob done?", top_k=3)
        dl_trace = trace.get("stage_direct_lookup", {})
        assert "applied" in dl_trace
        assert "entities" in dl_trace
        assert "facts_per_entity" in dl_trace
        assert "top_k" in dl_trace

    def test_context_contains_related_block_when_entity_found(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_kb_module, "_DIRECT_LOOKUP_ENABLED", True)
        # Provide embedding-like stubs via monkeypatching _last_direct_lookup
        kb._direct_lookup = DirectLookup(top_k=3)
        kb.add("Eve loves painting.")
        kb.add("Eve went hiking last week.")

        # Simulate direct lookup result (without real embeddings)
        from datetime import UTC, datetime

        from ai_knot.types import Fact, MemoryType

        def _fake_fact(content: str) -> Fact:
            f = Fact.__new__(Fact)
            f.id = "fake-id"
            f.content = content
            f.entity = "Eve"
            f.attribute = ""
            f.value_text = ""
            f.prompt_surface = ""
            f.source_verbatim = ""
            f.type = MemoryType.SEMANTIC
            f.created_at = datetime.now(UTC)
            return f

        kb._last_direct_lookup = {"Eve": [_fake_fact("Eve loves painting.")]}
        context = kb.recall("What has Eve done?", top_k=3)
        assert "Related to Eve:" in context
        assert "Additional context:" in context

    def test_no_direct_lookup_block_when_empty(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_kb_module, "_DIRECT_LOOKUP_ENABLED", True)
        kb._direct_lookup = DirectLookup(top_k=3)
        kb._last_direct_lookup = {}
        kb.add("Some fact about nothing specific.")
        context = kb.recall("What happened?", top_k=3)
        assert "Related to" not in context
        assert "Additional context:" not in context
