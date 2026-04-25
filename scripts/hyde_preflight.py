"""HyDE-lite preflight — extend BM25 query tokens with content-tokens harvested
from existing atomic_claims of the question's focus_entities. Test whether this
"claim-derived expansion" reaches gold tokens missing from the literal question.

Motivation: cat1 WRONG bucket (from ppr_preflight v2) shows gold tokens
("pottery", "clarinet") rarely overlap with query tokens ("activities",
"instruments"). Atomic claims for the same entity often *do* contain the
gold vocabulary. Expanding query with claim-tokens closes the vocabulary
gap at retrieval time, without touching render membership.

Usage:
    .venv/bin/python scripts/hyde_preflight.py \\
        --db aiknotbench/data/runs/p1-1b-2conv/knot.db \\
        --run aiknotbench/data/runs/p1-1b-2conv
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from math import log

_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from ai_knot.query_contract import analyze_query  # noqa: E402

_WORD_RE = re.compile(r"\b([a-zA-Z][a-zA-Z\-]{2,})\b")

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "but",
        "for",
        "with",
        "from",
        "that",
        "this",
        "these",
        "those",
        "have",
        "has",
        "had",
        "was",
        "were",
        "been",
        "being",
        "are",
        "its",
        "they",
        "them",
        "their",
        "there",
        "then",
        "than",
        "will",
        "would",
        "could",
        "should",
        "shall",
        "might",
        "must",
        "can",
        "about",
        "into",
        "over",
        "under",
        "any",
        "all",
        "each",
        "every",
        "some",
        "such",
        "much",
        "many",
        "most",
        "not",
        "only",
        "also",
        "just",
        "your",
        "yours",
        "mine",
        "you",
        "him",
        "her",
        "his",
        "she",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "when",
        "where",
        "why",
        "how",
        "does",
        "doing",
        "did",
        "done",
        "really",
        "very",
        "like",
        "liked",
        "likes",
        "get",
        "got",
        "getting",
        "make",
        "made",
        "makes",
        "making",
        "good",
        "great",
        "nice",
        "time",
        "thing",
        "things",
        "way",
        "ways",
        "today",
        "yesterday",
        "tomorrow",
        "now",
    }
)


def _content_tokens(text: str, min_len: int = 4) -> list[str]:
    out: list[str] = []
    for m in _WORD_RE.findall(text or ""):
        low = m.lower()
        if low in _STOPWORDS:
            continue
        if len(low) < min_len:
            continue
        out.append(low)
    return out


def _gold_tokens(gold: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", gold or "")]


def _contains_gold(text: str, gold: str) -> bool:
    toks = _gold_tokens(gold)
    if not toks:
        return True
    low = text.lower()
    return all(t in low for t in toks)


def _harvest_expansion(
    conn: sqlite3.Connection,
    agent_id: str,
    seeds: list[str],
    max_tokens: int = 12,
) -> list[str]:
    if not seeds:
        return []
    placeholders = " OR ".join(["LOWER(subject) LIKE ?"] * len(seeds))
    params = [agent_id] + [f"%{s}%" for s in seeds]
    rows = conn.execute(
        "SELECT relation, value_text FROM atomic_claims "
        "WHERE agent_id=? AND (" + placeholders + ")",
        params,
    ).fetchall()
    bag: Counter[str] = Counter()
    for rel, val in rows:
        for tok in _content_tokens(str(rel or "")):
            bag[tok] += 1
        for tok in _content_tokens(str(val or "")):
            bag[tok] += 1
    seeds_set = set(s.lower() for s in seeds)
    for s in seeds_set:
        bag.pop(s, None)
    return [tok for tok, _ in bag.most_common(max_tokens)]


def _load_pool(
    conn: sqlite3.Connection, agent_id: str, seeds: list[str]
) -> list[tuple[str, str, str, str]]:
    if not seeds:
        return []
    placeholders = " OR ".join(["raw_text LIKE ?"] * len(seeds))
    params = [agent_id] + [f"%{s}%" for s in seeds]
    rows = conn.execute(
        "SELECT id, session_id, turn_id, raw_text FROM raw_episodes "
        "WHERE agent_id=? AND (" + placeholders + ")",
        params,
    ).fetchall()
    return [(r[0], r[1] or "", r[2] or "", r[3] or "") for r in rows]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z\-]+", (text or "").lower())


def _bm25_rank(
    q_tokens: list[str], docs: list[tuple[str, str]]
) -> list[tuple[str, float]]:
    if not q_tokens or not docs:
        return [(d[0], 0.0) for d in docs]
    tokenized = [(rid, _tokenize(text)) for rid, text in docs]
    n = len(tokenized)
    avg_len = sum(len(t) for _, t in tokenized) / max(1, n)
    df: Counter[str] = Counter()
    for _, toks in tokenized:
        for tok in set(toks):
            df[tok] += 1
    k1, b = 1.5, 0.75
    scored = []
    for rid, toks in tokenized:
        if not toks:
            scored.append((rid, 0.0))
            continue
        tf = Counter(toks)
        score = 0.0
        dlen = len(toks)
        for tok in q_tokens:
            freq = tf.get(tok, 0)
            if freq <= 0:
                continue
            idf = log((n - df[tok] + 0.5) / (df[tok] + 0.5) + 1.0)
            norm = freq + k1 * (1 - b + b * dlen / max(1.0, avg_len))
            score += idf * freq * (k1 + 1) / norm
        scored.append((rid, score))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--top-k", type=int, default=18)
    ap.add_argument("--max-expansion", type=int, default=12)
    args = ap.parse_args()

    run_dir = pathlib.Path(args.run)
    log_path = run_dir / "log.jsonl"

    rows: list[dict] = []
    with log_path.open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    target = [r for r in rows if r.get("category") == 1 and r.get("verdict") == "WRONG"]
    print(f"Target cat1 WRONG Q: {len(target)}")

    tmp_dir = tempfile.mkdtemp(prefix="hyde_preflight_")
    tmp_db = str(pathlib.Path(tmp_dir) / "q.db")

    counters: dict[str, int] = {
        "base_has": 0,
        "bm25_plain_top12": 0,
        "bm25_plain_top18": 0,
        "bm25_expanded_top12": 0,
        "bm25_expanded_top18": 0,
        "pool_has_gold": 0,
        "no_expansion_tokens": 0,
    }
    per_q: list[dict] = []

    for r in target:
        conv_idx = r["convIdx"]
        agent_id = f"conv-{conv_idx}"
        q = r["question"]
        gold = r["goldAnswer"]
        frame = analyze_query(q)
        seeds = [s.lower() for s in frame.focus_entities]

        base_ctx = r.get("context", "") or ""
        base_ok = _contains_gold(base_ctx, gold)
        if base_ok:
            counters["base_has"] += 1

        shutil.copy2(args.db, tmp_db)
        conn = sqlite3.connect(tmp_db)
        try:
            pool = _load_pool(conn, agent_id, seeds)
            expansion = _harvest_expansion(conn, agent_id, seeds, args.max_expansion)
        finally:
            conn.close()

        if not expansion:
            counters["no_expansion_tokens"] += 1

        pool_docs = [(rid, text) for rid, _sid, _tid, text in pool]
        q_content = _content_tokens(q)
        q_plain = list(set(q_content + seeds))
        q_expanded = list(set(q_plain + expansion))

        pool_text = " ".join(text for _, text in pool_docs)
        if _contains_gold(pool_text, gold):
            counters["pool_has_gold"] += 1

        bm25_plain = _bm25_rank(q_plain, pool_docs)
        bm25_expanded = _bm25_rank(q_expanded, pool_docs)

        pool_by_id = {rid: text for rid, text in pool_docs}

        def _cat_top(ranked: list[tuple[str, float]], k: int) -> str:
            return " ".join(pool_by_id.get(rid, "") for rid, _ in ranked[:k])

        plain12_ok = _contains_gold(_cat_top(bm25_plain, 12), gold)
        plain18_ok = _contains_gold(_cat_top(bm25_plain, 18), gold)
        exp12_ok = _contains_gold(_cat_top(bm25_expanded, 12), gold)
        exp18_ok = _contains_gold(_cat_top(bm25_expanded, 18), gold)

        if plain12_ok:
            counters["bm25_plain_top12"] += 1
        if plain18_ok:
            counters["bm25_plain_top18"] += 1
        if exp12_ok:
            counters["bm25_expanded_top12"] += 1
        if exp18_ok:
            counters["bm25_expanded_top18"] += 1

        gold_lower_toks = _gold_tokens(gold)
        exp_covers_gold = [t for t in gold_lower_toks if t in expansion]

        per_q.append(
            {
                "conv": conv_idx,
                "qa": r["qaIdx"],
                "question": q[:80],
                "gold": gold[:80],
                "seeds": seeds,
                "expansion": expansion,
                "exp_covers_gold": exp_covers_gold,
                "baseline_gold_in_ctx": base_ok,
                "bm25_plain_top12": plain12_ok,
                "bm25_plain_top18": plain18_ok,
                "bm25_expanded_top12": exp12_ok,
                "bm25_expanded_top18": exp18_ok,
                "n_pool": len(pool_docs),
            }
        )

    out_path = run_dir / "hyde_preflight.json"
    out_path.write_text(
        json.dumps({"summary": counters, "n": len(target), "rows": per_q}, indent=2)
    )

    print("\n=== HyDE-lite Preflight Summary (cat1 WRONG) ===")
    n = len(target)
    print(f"  N Q:                              {n}")
    print(f"  Baseline gold-in-ctx:             {counters['base_has']}/{n}")
    print(f"  Pool upper-bound:                 {counters['pool_has_gold']}/{n}")
    print(f"  Q with no expansion tokens:       {counters['no_expansion_tokens']}")
    print(f"  --- Plain BM25 (no expansion) ---")
    print(f"  plain BM25 top-12 gold-in-ctx:    {counters['bm25_plain_top12']}/{n}")
    print(f"  plain BM25 top-18 gold-in-ctx:    {counters['bm25_plain_top18']}/{n}")
    print(f"  --- BM25 + claim-expansion ---")
    print(f"  expanded BM25 top-12:             {counters['bm25_expanded_top12']}/{n}")
    print(f"  expanded BM25 top-18:             {counters['bm25_expanded_top18']}/{n}")
    print(f"  Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
