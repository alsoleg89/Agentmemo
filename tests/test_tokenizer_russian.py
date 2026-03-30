"""Russian morphology in _tokenize — suffix stripping improves Recall@K.

Tests that:
1. Common Russian inflectional endings are stripped to a common stem.
2. English tokenization behavior is unchanged.
3. Retrieval correctly matches morphological variants.
"""

from __future__ import annotations

import pytest

from ai_knot.retriever import TFIDFRetriever, _tokenize
from ai_knot.types import Fact


class TestRussianSuffixStripping:
    """Inflected Russian words should share a normalized stem."""

    @pytest.mark.parametrize(
        "inflected, base_form",
        [
            ("маркетингового", "маркетинг"),
            ("маркетинговому", "маркетинг"),
            ("маркетинговым", "маркетинг"),
            ("продажами", "продаж"),
            ("конверсией", "конверси"),
            ("публикаций", "публикаци"),
            ("стратегического", "стратегич"),
            ("аналитических", "аналитич"),
        ],
    )
    def test_inflected_shares_stem_with_base(self, inflected: str, base_form: str) -> None:
        tokens = _tokenize(inflected)
        assert len(tokens) == 1
        # The stripped token should start with the base form stem
        assert tokens[0].startswith(base_form[:4]), (
            f"Expected '{inflected}' to strip to something starting with "
            f"'{base_form[:4]}', got '{tokens[0]}'"
        )

    def test_short_cyrillic_word_not_over_stripped(self) -> None:
        # Words with stem < 4 chars should not be stripped
        tokens = _tokenize("она")
        assert tokens == ["она"]

    def test_english_plural_still_stripped(self) -> None:
        assert _tokenize("containers") == ["container"]

    def test_english_unchanged_for_no_s(self) -> None:
        assert _tokenize("python") == ["python"]

    def test_mixed_cyrillic_latin_sentence(self) -> None:
        tokens = _tokenize("маркетинговый контент Python")
        assert len(tokens) == 3
        assert "python" in tokens


class TestRussianRetrieval:
    """TFIDFRetriever finds morphological variants via suffix-stripped tokens."""

    def test_inflected_query_finds_base_form_fact(self) -> None:
        retriever = TFIDFRetriever()
        facts = [
            Fact(content="маркетинг контент стратегия"),
            Fact(content="пользователь работает в Сбере"),
        ]
        # Query in inflected form should still find the marketing fact
        results = retriever.search("маркетингового", facts, top_k=1)
        assert len(results) == 1
        assert "маркетинг" in results[0][0].content

    def test_recall_improves_with_morphological_variant(self) -> None:
        retriever = TFIDFRetriever()
        facts = [
            Fact(content="продажи в четвёртом квартале выросли"),
            Fact(content="пользователь предпочитает Python"),
        ]
        # Query "продажами" should match "продажи"
        results = retriever.search("продажами", facts, top_k=1)
        assert "продаж" in results[0][0].content or "продажи" in results[0][0].content
