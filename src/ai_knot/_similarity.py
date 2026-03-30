"""Pure-stdlib TF-IDF cosine similarity for deduplication.

Used by the extractor to detect near-duplicate facts during extraction
and conflict resolution with existing facts.  No external dependencies.
"""

from __future__ import annotations

import math
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenization (Latin + Cyrillic, no stemming)."""
    return re.findall(r"[a-zA-Z0-9\u0400-\u04FF]+", text.lower())


def tfidf_cosine(a: str, b: str) -> float:
    """TF-IDF weighted cosine similarity between two strings.

    Uses a 2-document IDF so shared rare words count more than shared
    stop-words.  Handles length-mismatch paraphrases better than Jaccard.

    Args:
        a: First string.
        b: Second string.

    Returns:
        Cosine similarity in [0.0, 1.0].  Returns 0.0 on empty input.
    """
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0

    set_a = set(tokens_a)
    set_b = set(tokens_b)
    vocab = set_a | set_b
    len_a = len(tokens_a)
    len_b = len(tokens_b)
    tf_a: Counter[str] = Counter(tokens_a)
    tf_b: Counter[str] = Counter(tokens_b)

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for term in vocab:
        # df ∈ {1, 2} — term appears in one or both documents
        df = (1 if term in set_a else 0) + (1 if term in set_b else 0)
        idf = math.log(1.0 + 2.0 / (1.0 + df))
        va = (tf_a.get(term, 0) / len_a) * idf
        vb = (tf_b.get(term, 0) / len_b) * idf
        dot += va * vb
        norm_a += va * va
        norm_b += vb * vb

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
