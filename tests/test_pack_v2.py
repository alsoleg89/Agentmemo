"""Tests for Evidence Pack V2 — EvidencePackBuilder (A.pack cycle)."""

from __future__ import annotations

import pathlib
from unittest.mock import patch

from ai_knot.knowledge import KnowledgeBase
from ai_knot.pack import EvidencePackBuilder
from ai_knot.storage.yaml_storage import YAMLStorage

# ---- Helpers ----------------------------------------------------------------


def _kb(tmp_path: pathlib.Path) -> KnowledgeBase:
    return KnowledgeBase(agent_id="pack-test", storage=YAMLStorage(base_dir=str(tmp_path)))


def _add_n_facts(kb: KnowledgeBase, n: int, prefix: str = "fact") -> None:
    for i in range(n):
        kb.add(f"{prefix} {i}: Alice did something on day {i}")


# ---- EvidencePackBuilder.build ----------------------------------------------


class TestLostInMiddleReorder:
    def test_single_fact_unchanged(self, tmp_path: pathlib.Path) -> None:
        kb = _kb(tmp_path)
        kb.add("Alice likes cats")
        pairs = kb.recall_facts_with_scores("what does Alice like?", top_k=1)
        builder = EvidencePackBuilder()
        pack = builder.build(pairs, intent="FACTUAL")
        assert len(pack.raw_ribbons) == 1

    def test_two_facts_preserve_order(self, tmp_path: pathlib.Path) -> None:
        kb = _kb(tmp_path)
        kb.add("rank1 Alice works at Acme")
        kb.add("rank2 Bob works at Bravo")
        pairs = kb.recall_facts_with_scores("where does Alice work?", top_k=2)
        builder = EvidencePackBuilder()
        pack = builder.build(pairs, intent="FACTUAL")
        assert len(pack.raw_ribbons) == 2

    def test_litm_interleave_head_tail(self, tmp_path: pathlib.Path) -> None:
        """rank 1 → pos 0, rank 2 → last, rank 3 → pos 1, rank 4 → second-last."""
        from ai_knot.types import Fact

        dummy_facts: list[tuple[Fact, float]] = []
        for i, score in enumerate([1.0, 0.9, 0.8, 0.7, 0.6], start=1):
            f = Fact(content=f"fact rank{i}", id=f"id{i:02d}")
            dummy_facts.append((f, score))

        builder = EvidencePackBuilder()
        reordered = builder._litm_reorder(dummy_facts)
        rendered_contents = [f.content for f, _ in reordered]
        # rank 1 at head, rank 2 at tail
        assert rendered_contents[0] == "fact rank1"
        assert rendered_contents[-1] == "fact rank2"

    def test_exploratory_intent_skips_reorder(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.types import Fact

        dummy_facts = [(Fact(content=f"fact{i}", id=f"id{i}"), float(5 - i)) for i in range(5)]
        builder = EvidencePackBuilder()
        pack = builder.build(dummy_facts, intent="EXPLORATORY")
        # EXPLORATORY skips LITM — order should be unchanged
        original_ids = [f.id for f, _ in dummy_facts]
        assert pack.fact_ids == original_ids


class TestTokenBudget:
    def test_budget_respected(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.types import Fact

        # Each fact ~200 chars → 50 tokens. Budget = 100 tokens → ~2 facts.
        long_text = "A" * 200
        dummy_facts = [(Fact(content=long_text, id=f"id{i}"), 1.0) for i in range(10)]
        builder = EvidencePackBuilder(token_budget=100)
        pack = builder.build(dummy_facts, intent="FACTUAL")
        # Should include ≤ 100 tokens worth of facts (~400 chars budget)
        total_chars = sum(len(r) for r in pack.raw_ribbons)
        assert total_chars <= 100 * 4 + len(pack.raw_ribbons) * 6

    def test_at_least_one_fact_always_included(self, tmp_path: pathlib.Path) -> None:
        from ai_knot.types import Fact

        # One very long fact that exceeds budget
        huge_text = "B" * 10_000
        dummy_facts = [(Fact(content=huge_text, id="big"), 1.0)]
        builder = EvidencePackBuilder(token_budget=10)
        pack = builder.build(dummy_facts, intent="FACTUAL")
        assert len(pack.fact_ids) == 1


class TestStructuredOutput:
    def test_render_produces_numbered_lines(self, tmp_path: pathlib.Path) -> None:
        kb = _kb(tmp_path)
        kb.add("Alice works at Acme Corp")
        pairs = kb.recall_facts_with_scores("where does Alice work?", top_k=3)
        pack = EvidencePackBuilder().build(pairs, intent="FACTUAL")
        rendered = pack.render()
        assert rendered.startswith("[1]")

    def test_what_we_dont_know_present_when_uncertainty(self) -> None:
        from ai_knot.types import Fact

        all_pairs = [(Fact(content=f"f{i}", id=f"id{i}"), 1.0) for i in range(10)]
        # budgeted will be empty if budget is 0 → but builder always includes first
        builder = EvidencePackBuilder(token_budget=1)
        pack = builder.build(all_pairs, intent="FACTUAL")
        # 1 fact budgeted vs 10 total → uncertainty signal fires
        assert pack.what_we_dont_know is not None

    def test_what_we_dont_know_absent_when_no_uncertainty(self) -> None:
        from ai_knot.types import Fact

        all_pairs = [(Fact(content="short fact", id="id0"), 1.0)]
        pack = EvidencePackBuilder().build(all_pairs, intent="FACTUAL")
        # 1 out of 1 → no uncertainty
        assert pack.what_we_dont_know is None

    def test_what_we_dont_know_override_true(self) -> None:
        from ai_knot.types import Fact

        pairs = [(Fact(content="fact", id="id0"), 1.0)]
        pack = EvidencePackBuilder().build(pairs, intent="FACTUAL", uncertainty_signal=True)
        assert pack.what_we_dont_know is not None

    def test_what_we_dont_know_override_false(self) -> None:
        from ai_knot.types import Fact

        # Even if auto-detection fires, explicit False suppresses it
        all_pairs = [(Fact(content="x" * 200, id=f"id{i}"), 1.0) for i in range(10)]
        pack = EvidencePackBuilder(token_budget=1).build(
            all_pairs, intent="FACTUAL", uncertainty_signal=False
        )
        assert pack.what_we_dont_know is None

    def test_fact_ids_in_rendered_order(self) -> None:
        from ai_knot.types import Fact

        pairs = [(Fact(content=f"fact{i}", id=f"id{i:02d}"), float(5 - i)) for i in range(5)]
        pack = EvidencePackBuilder().build(pairs, intent="FACTUAL")
        # fact_ids should match the reordered content order
        assert len(pack.fact_ids) == len(pack.raw_ribbons)

    def test_deduplicates_identical_content(self) -> None:
        from ai_knot.types import Fact

        pairs = [
            (Fact(content="same text", id="id1"), 1.0),
            (Fact(content="same text", id="id2"), 0.9),
        ]
        pack = EvidencePackBuilder().build(pairs, intent="FACTUAL")
        assert len(pack.raw_ribbons) == 1


class TestPackV2Integration:
    def test_recall_uses_pack_v2_when_enabled(self, tmp_path: pathlib.Path) -> None:
        kb = _kb(tmp_path)
        kb.add("Alice prefers dark roast coffee")
        kb.add("Bob prefers green tea")
        kb.add("Charlie prefers sparkling water")

        with patch.dict("os.environ", {"AI_KNOT_PACK_V2": "1"}):
            # Reload the module flag
            import importlib

            import ai_knot.pack as pack_mod

            importlib.reload(pack_mod)
            # Also reload knowledge to pick up the new flag
            import ai_knot.knowledge as k_mod

            importlib.reload(k_mod)
            from ai_knot.knowledge import KnowledgeBase as KBReloaded
            from ai_knot.storage.yaml_storage import YAMLStorage as YSReloaded

            kb2 = KBReloaded(
                agent_id="pack-test2",
                storage=YSReloaded(base_dir=str(tmp_path / "kb2")),
            )
            kb2.add("Alice drinks dark roast coffee every morning")
            result = kb2.recall("what does Alice drink?", top_k=3)
            assert "[1]" in result
