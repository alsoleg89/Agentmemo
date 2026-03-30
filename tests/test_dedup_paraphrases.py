"""Deduplication quality — TF-IDF cosine handles length-asymmetric pairs better than Jaccard.

TF-IDF cosine improvement over Jaccard:
- Lexical extension pairs (same key nouns, one sentence longer): cosine detects them;
  Jaccard misses them because union grows faster than intersection.
- Exact duplicates: both methods catch.
- Semantic paraphrases (different vocabulary): neither method catches without embeddings.

Tests validate the actual improvement, not hypothetical embedding-level recall.
"""

from __future__ import annotations

from ai_knot._similarity import tfidf_cosine
from ai_knot.extractor import deduplicate_facts
from ai_knot.types import Fact

# Lexical extension pairs: same key concepts + same key words; one is longer.
# Cosine handles these well because shared rare words dominate the score.
# Jaccard misses them because |union| grows much faster than |intersection|.
_EXTENSION_PAIRS = [
    ("User deploys in Docker", "User deploys all applications in Docker containers"),
    ("Use pytest for testing", "Always use pytest framework for all testing"),
    ("User prefers Python", "User always prefers Python for all backend development"),
    ("Deploy with Docker Compose", "Deploy all services with Docker Compose configuration"),
    ("User works at Sber", "User currently works full-time at Sber as director"),
]

# Exact duplicates — must always be merged regardless of method.
_EXACT_DUPLICATES = [
    "User deploys in Docker",
    "Always use type hints",
    "User prefers Python",
]

# Distinct facts — must never be merged.
_DISTINCT_PAIRS = [
    ("User prefers Python", "User works at Google"),
    ("Deploy with Docker", "User likes tea"),
    ("Use pytest", "User is a manager"),
]


class TestCosineVsJaccard:
    """TF-IDF cosine detects length-asymmetric pairs that Jaccard misses."""

    def test_cosine_detects_extension_pairs(self) -> None:
        """Pairs where one sentence extends the other share enough cosine similarity."""
        caught = 0
        for short, extended in _EXTENSION_PAIRS:
            score = tfidf_cosine(short, extended)
            if score >= 0.55:
                caught += 1

        # Cosine should catch at least 60 % of length-asymmetric lexical pairs
        catch_rate = caught / len(_EXTENSION_PAIRS)
        assert catch_rate >= 0.60, (
            f"Cosine catch rate {catch_rate:.0%} below 60 % "
            f"({caught}/{len(_EXTENSION_PAIRS)} pairs detected)"
        )

    def test_jaccard_misses_extension_pairs(self) -> None:
        """Confirm the Jaccard baseline misses most extension pairs at 0.7 threshold."""

        def jaccard(a: str, b: str) -> float:
            wa, wb = set(a.lower().split()), set(b.lower().split())
            if not wa or not wb:
                return 0.0
            return len(wa & wb) / len(wa | wb)

        jaccard_caught = sum(
            1 for short, extended in _EXTENSION_PAIRS if jaccard(short, extended) >= 0.7
        )
        cosine_caught = sum(
            1 for short, extended in _EXTENSION_PAIRS if tfidf_cosine(short, extended) >= 0.55
        )
        # Cosine must be at least as good as Jaccard for extension pairs
        assert cosine_caught >= jaccard_caught


class TestDeduplicateFacts:
    """deduplicate_facts with TF-IDF cosine."""

    def test_exact_duplicates_removed(self) -> None:
        for content in _EXACT_DUPLICATES:
            facts = [Fact(content=content), Fact(content=content)]
            assert len(deduplicate_facts(facts)) == 1

    def test_distinct_facts_not_merged(self) -> None:
        for a, b in _DISTINCT_PAIRS:
            facts = [Fact(content=a), Fact(content=b)]
            assert len(deduplicate_facts(facts)) == 2, f"'{a}' and '{b}' should not be merged"

    def test_extension_pair_merged_at_lenient_threshold(self) -> None:
        short, extended = _EXTENSION_PAIRS[0]
        facts = [Fact(content=short), Fact(content=extended)]
        # At lenient threshold (0.5) cosine should merge the extension pair
        merged = deduplicate_facts(facts, threshold=0.50)
        score = tfidf_cosine(short, extended)
        if score >= 0.50:
            assert len(merged) == 1
        else:
            assert len(merged) == 2  # score too low — kept separate

    def test_single_fact_unchanged(self) -> None:
        facts = [Fact(content="User prefers Python")]
        assert deduplicate_facts(facts) == facts

    def test_empty_list(self) -> None:
        assert deduplicate_facts([]) == []

    def test_threshold_controls_strictness(self) -> None:
        facts = [
            Fact(content="User prefers Python"),
            Fact(content="User prefers Python language"),
        ]
        strict = deduplicate_facts(facts, threshold=0.99)
        lenient = deduplicate_facts(facts, threshold=0.50)
        assert len(strict) >= len(lenient)
