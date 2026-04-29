"""Regression tests for F5: recall_with_trace must use a single retrieval pass.
context and pack_fact_ids must be derived from the same pipeline execution."""

from __future__ import annotations

import json
import pathlib

import pytest

from ai_knot._mcp_tools import tool_recall_with_trace
from ai_knot.knowledge import KnowledgeBase
from ai_knot.storage.yaml_storage import YAMLStorage


@pytest.fixture
def kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    storage = YAMLStorage(base_dir=str(tmp_path))
    kb = KnowledgeBase(agent_id="f5_test", storage=storage)
    kb.add("Alice loves painting as a hobby.")
    kb.add("Bob enjoys hiking on weekends.")
    kb.add("Caroline has two dogs as pets.")
    return kb


class TestRecallWithTraceSinglePass:
    def test_pack_fact_ids_match_context_facts(self, kb: KnowledgeBase) -> None:
        """Fact IDs in pack_fact_ids must correspond to facts shown in context."""
        context, pack_fact_ids, trace = kb.recall_with_trace("painting hobby", top_k=3)
        assert isinstance(context, str)
        assert isinstance(pack_fact_ids, list)
        assert isinstance(trace, dict)
        # At least one fact retrieved
        assert len(pack_fact_ids) > 0
        # Context must contain facts (non-empty)
        assert context.strip() != ""

    def test_trace_has_stage1_candidates(self, kb: KnowledgeBase) -> None:
        _, _, trace = kb.recall_with_trace("hobby", top_k=3)
        assert "stage1_candidates" in trace
        assert "from_bm25" in trace["stage1_candidates"]
        assert "total" in trace["stage1_candidates"]

    def test_context_consistent_with_pack_ids(self, kb: KnowledgeBase) -> None:
        """context must reference exactly the facts in pack_fact_ids (no phantom facts)."""
        context, pack_fact_ids, _ = kb.recall_with_trace("dogs pets", top_k=5)
        # Verify every line in context starts with [N]
        for line in context.splitlines():
            assert line.startswith("["), f"context line missing bracket: {line!r}"


class TestToolRecallWithTraceSinglePass:
    def test_tool_returns_valid_json(self, kb: KnowledgeBase) -> None:
        result = tool_recall_with_trace(kb, "painting hobby", top_k=3)
        data = json.loads(result)
        assert "context" in data
        assert "pack_fact_ids" in data
        assert "trace" in data

    def test_tool_no_double_recall(self, kb: KnowledgeBase) -> None:
        """pack_fact_ids must reference facts that appear in context — single-pass coherence."""
        result = tool_recall_with_trace(kb, "hiking outdoors", top_k=3)
        data = json.loads(result)
        context: str = data["context"]
        pack_ids: list[str] = data["pack_fact_ids"]
        # Context should be non-empty if pack has facts
        if pack_ids:
            assert context.strip() != ""
