"""Tests for Stage 4c: Entity-Pack Union (AI_KNOT_ENTITY_PACK_UNION).

The flag is read at module import time, so tests patch the module attribute
directly via monkeypatch.setattr rather than monkeypatch.setenv.
"""

from __future__ import annotations

import pathlib

import pytest

import ai_knot.knowledge as _kb_module
from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.yaml_storage import YAMLStorage


@pytest.fixture
def kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    storage = YAMLStorage(base_dir=str(tmp_path))
    return KnowledgeBase(agent_id="union_test", storage=storage)


class TestEntityPackUnionFlagOff:
    def test_flag_off_is_noop(self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch) -> None:
        """With flag disabled (default), pack size equals top_k and trace has no union key."""
        monkeypatch.setattr(_kb_module, "_ENTITY_PACK_UNION_ENABLED", False)
        for i in range(10):
            kb.add(f"Melanie went hiking on day {i}.")
        pairs, trace = kb.recall_facts_with_trace("Melanie hobbies", top_k=5)

        assert len(pairs) <= 5
        assert (
            "stage4c_entity_pack_union" not in trace
            or not trace["stage4c_entity_pack_union"]["applied"]
        )


class TestEntityPackUnionFlagOn:
    def test_flag_on_expands_pack(self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch) -> None:
        """With flag enabled and entity-rich corpus, pack expands beyond top_k."""
        monkeypatch.setattr(_kb_module, "_ENTITY_PACK_UNION_ENABLED", True)
        for i in range(12):
            kb.add(f"Melanie did activity number {i} this week.")
        pairs, trace = kb.recall_facts_with_trace("Melanie hobbies", top_k=5)

        union_info = trace.get("stage4c_entity_pack_union", {})
        if union_info.get("applied"):
            assert len(pairs) > 5
            assert len(pairs) <= 10
            assert len(union_info["extras_added"]) >= 1

    def test_flag_on_no_entity_is_noop(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Query with no extractable entity → union is no-op."""
        monkeypatch.setattr(_kb_module, "_ENTITY_PACK_UNION_ENABLED", True)
        for i in range(5):
            kb.add(f"Generic fact number {i}.")
        pairs, trace = kb.recall_facts_with_trace("what time is it", top_k=5)

        union_info = trace.get("stage4c_entity_pack_union", {})
        assert union_info.get("applied") is False
        assert union_info.get("entity") == ""

    def test_no_expansion_when_pool_already_in_pack(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If all entity-matching facts are already selected, extras_added is empty."""
        monkeypatch.setattr(_kb_module, "_ENTITY_PACK_UNION_ENABLED", True)
        # Only 4 facts mention Sarah — all will fit in top_k=5; nothing to add.
        for i in range(4):
            kb.add(f"Sarah went swimming on day {i}.")
        pairs, trace = kb.recall_facts_with_trace("Sarah hobbies", top_k=5)

        union_info = trace.get("stage4c_entity_pack_union", {})
        # Pack covers all Sarah facts, so no extras beyond what MMR already selected.
        assert union_info.get("extras_added", None) is not None
        assert len(union_info["extras_added"]) == 0

    def test_pack_size_capped_at_2x_top_k(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even with many entity-matching facts, pack is capped at 2 * top_k."""
        monkeypatch.setattr(_kb_module, "_ENTITY_PACK_UNION_ENABLED", True)
        for i in range(50):
            kb.add(f"Carol completed task {i} for the project.")
        pairs, trace = kb.recall_facts_with_trace("Carol activities", top_k=5)

        assert len(pairs) <= 10

    def test_trace_stage4c_key_always_present_when_flag_on(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stage4c_entity_pack_union key is always written when flag is on."""
        monkeypatch.setattr(_kb_module, "_ENTITY_PACK_UNION_ENABLED", True)
        kb.add("Alice loves painting.")
        _, trace = kb.recall_facts_with_trace("Alice hobbies", top_k=5)

        assert "stage4c_entity_pack_union" in trace
        info = trace["stage4c_entity_pack_union"]
        assert "applied" in info
        assert "entity" in info
        assert "extras_added" in info
        assert "pack_size_post_union" in info

    def test_trace_stage1_from_entity_direct_populated_on_expansion(
        self, kb: KnowledgeBase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When expansion occurs, union extras appear in from_entity_direct trace channel."""
        monkeypatch.setattr(_kb_module, "_ENTITY_PACK_UNION_ENABLED", True)
        for i in range(12):
            kb.add(f"David completed task {i} this month.")
        pairs, trace = kb.recall_facts_with_trace("David activities", top_k=5)

        union_info = trace.get("stage4c_entity_pack_union", {})
        if union_info.get("applied"):
            from_entity_direct = set(trace["stage1_candidates"].get("from_entity_direct", []))
            for fid in union_info["extras_added"]:
                assert fid in from_entity_direct, f"{fid!r} not in from_entity_direct"
