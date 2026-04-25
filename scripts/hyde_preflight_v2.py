"""HyDE-lite preflight v2 — corrected metric.

v1 used `all tokens in ctx` which mis-classifies SET gold ("A, B, C") and
ghost-tokens (gold words absent from the corpus entirely — typos, abstract
paraphrases). v2 uses `at_least_one_item_in_ctx` where items are split by
comma / semicolon / " and " — the realistic retrieval success condition
for SET-type cat1 Q.

Also reports:
  - per-item recall (how many gold items reach render ctx)
  - ghost tokens per Q (items with 0 raws anywhere in agent_id)
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
_ITEM_SPLIT = re.compile(r"\s*(?:,|;|\band\b|\bor\b|/)\s*", re.IGNORECASE)

_STOPWORDS = frozenset(
    {
        "the", "and", "but", "for", "with", "from", "that", "this", "these",
        "those", "have", "has", "had", "was", "were", "been", "being", "are",
        "its", "they", "them", "their", "there", "then", "than", "will",
        "would", "could", "should", "shall", "might", "must", "can", "about",
        "into", "over", "under", "any", "all", "each", "every", "some",
        "such", "much", "many", "most", "not", "only", "also", "just",
        "your", "yours", "mine", "you", "him", "her", "his", "she", "one",
        "two", "three", "what", "which", "who", "whom", "whose", "when",
        "where", "why", "how", "does", "doing", "did", "done", "really",
        "very", "like", "liked", "likes", "get", "got", "make", "made",
        "makes", "good", "great", "time", "thing", "things", "way", "ways",
    }
)


def _content_tokens(text: str, min_len: int = 4) -> list[str]:
    out: list[str] = []
    for m in _WORD_RE.findall(text or ""):
        low = m.lower()
        if low in _STOPWORDS or len(low) < min_len:
            continue
        out.append(low)
    return out


def _gold_items(gold: str) -> list[str]:
    raw_items = _ITEM_SPLIT.split((gold or "").strip())
    return [it.strip().lower() for it in raw_items if it.strip()]


def _item_matches(item: str, text_low: str) -> bool:
    if not item:
        return False
    if item in text_low:
        return True
    toks = [t for t in _WORD_RE.findall(item) if len(t) >= 4 and t.lower() not in _STOPWORDS]
    if not toks:
        return False
    return any(t.lower() in text_low for t in toks)


def _count_items_in_ctx(items: list[str], ctx: str) -> int:
    low = (ctx or "").lower()
    return sum(1 for it in items if _item_matches(it, low))


def _at_least_one(items: list[str], ctx: str) -> bool:
    return _count_items_in_ctx(items, ctx) > 0


def _harvest_expansion(conn, agent_id, seeds, max_tokens=12):
    if not seeds:
        return []
    ph = " OR ".join(["LOWER(subject) LIKE ?"] * len(seeds))
    params = [agent_id] + [f"%{s}%" for s in seeds]
    rows = conn.execute(
        "SELECT relation, value_text FROM atomic_claims WHERE agent_id=? AND (" + ph + ")",
        params,
    ).fetchall()
    bag: Counter = Counter()
    for rel, val in rows:
        for tok in _content_tokens(str(rel or "")):
            bag[tok] += 1
        for tok in _content_tokens(str(val or "")):
            bag[tok] += 1
    for s in set(seeds):
        bag.pop(s.lower(), None)
    return [tok for tok, _ in bag.most_common(max_tokens)]


def _load_pool(conn, agent_id, seeds, widen_adjacent: bool) -> list[tuple[str, str]]:
    if not seeds:
        return []
    ph = " OR ".join(["raw_text LIKE ?"] * len(seeds))
    params = [agent_id] + [f"%{s}%" for s in seeds]
    rows = conn.execute(
        "SELECT id, session_id, turn_id, raw_text FROM raw_episodes WHERE agent_id=? AND (" + ph + ")",
        params,
    ).fetchall()

    if not widen_adjacent:
        return [(r[0], r[3] or "") for r in rows]

    all_rows = conn.execute(
        "SELECT id, session_id, turn_id, raw_text FROM raw_episodes WHERE agent_id=?",
        (agent_id,),
    ).fetchall()

    by_session: dict[str, list[tuple[str, str, str]]] = {}
    for rid, sid, tid, rt in all_rows:
        by_session.setdefault(sid, []).append((rid, tid or "", rt or ""))

    def _ti(t: str) -> int:
        try:
            return int(t.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            return 0

    for sid in by_session:
        by_session[sid].sort(key=lambda x: _ti(x[1]))

    pool_ids = {r[0] for r in rows}
    widened: dict[str, str] = {r[0]: r[3] or "" for r in rows}
    for sid, lst in by_session.items():
        for i, (rid, _tid, rt) in enumerate(lst):
            if rid not in pool_ids:
                continue
            if i > 0:
                prev_rid, _p_t, prev_rt = lst[i - 1]
                widened.setdefault(prev_rid, prev_rt)
            if i + 1 < len(lst):
                next_rid, _n_t, next_rt = lst[i + 1]
                widened.setdefault(next_rid, next_rt)
    return list(widened.items())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z\-]+", (text or "").lower())


def _bm25_rank(q_tokens, docs) -> list[tuple[str, float]]:
    if not q_tokens or not docs:
        return [(d[0], 0.0) for d in docs]
    tokenized = [(rid, _tokenize(text)) for rid, text in docs]
    n = len(tokenized)
    avg_len = sum(len(t) for _, t in tokenized) / max(1, n)
    df: Counter = Counter()
    for _, toks in tokenized:
        for t in set(toks):
            df[t] += 1
    k1, b = 1.5, 0.75
    scored = []
    for rid, toks in tokenized:
        if not toks:
            scored.append((rid, 0.0))
            continue
        tf = Counter(toks)
        s = 0.0
        dl = len(toks)
        for t in q_tokens:
            f = tf.get(t, 0)
            if f <= 0:
                continue
            idf = log((n - df[t] + 0.5) / (df[t] + 0.5) + 1.0)
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / max(1.0, avg_len)))
        scored.append((rid, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--run", required=True)
    args = ap.parse_args()

    run_dir = pathlib.Path(args.run)
    rows: list[dict] = []
    with (run_dir / "log.jsonl").open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    target = [r for r in rows if r.get("category") == 1 and r.get("verdict") == "WRONG"]
    print(f"Target cat1 WRONG Q: {len(target)}")

    tmp_dir = tempfile.mkdtemp(prefix="hyde_v2_")
    tmp_db = str(pathlib.Path(tmp_dir) / "q.db")

    counters: dict[str, int] = {
        "base_any_item": 0,
        "plain12_any": 0, "plain18_any": 0,
        "exp12_any": 0, "exp18_any": 0,
        "plain12_wide_any": 0, "exp18_wide_any": 0,
        "pool_any": 0, "pool_wide_any": 0,
    }
    per_q: list[dict] = []

    for r in target:
        conv_idx = r["convIdx"]
        agent_id = f"conv-{conv_idx}"
        q = r["question"]
        gold = r["goldAnswer"]
        items = _gold_items(gold)
        frame = analyze_query(q)
        seeds = [s.lower() for s in frame.focus_entities]

        base_ctx = r.get("context", "") or ""
        base_ok = _at_least_one(items, base_ctx)
        base_count = _count_items_in_ctx(items, base_ctx)
        if base_ok:
            counters["base_any_item"] += 1

        shutil.copy2(args.db, tmp_db)
        conn = sqlite3.connect(tmp_db)
        try:
            pool_narrow = _load_pool(conn, agent_id, seeds, widen_adjacent=False)
            pool_wide = _load_pool(conn, agent_id, seeds, widen_adjacent=True)
            expansion = _harvest_expansion(conn, agent_id, seeds, 12)
        finally:
            conn.close()

        if _at_least_one(items, " ".join(t for _, t in pool_narrow)):
            counters["pool_any"] += 1
        if _at_least_one(items, " ".join(t for _, t in pool_wide)):
            counters["pool_wide_any"] += 1

        q_plain = list(set(_content_tokens(q) + seeds))
        q_expanded = list(set(q_plain + expansion))

        plain_narrow = _bm25_rank(q_plain, pool_narrow)
        plain_wide = _bm25_rank(q_plain, pool_wide)
        exp_narrow = _bm25_rank(q_expanded, pool_narrow)
        exp_wide = _bm25_rank(q_expanded, pool_wide)

        def _cat(ranked, k, pool):
            by_id = {rid: t for rid, t in pool}
            return " ".join(by_id.get(rid, "") for rid, _ in ranked[:k])

        if _at_least_one(items, _cat(plain_narrow, 12, pool_narrow)):
            counters["plain12_any"] += 1
        if _at_least_one(items, _cat(plain_narrow, 18, pool_narrow)):
            counters["plain18_any"] += 1
        if _at_least_one(items, _cat(exp_narrow, 12, pool_narrow)):
            counters["exp12_any"] += 1
        if _at_least_one(items, _cat(exp_narrow, 18, pool_narrow)):
            counters["exp18_any"] += 1
        if _at_least_one(items, _cat(plain_wide, 12, pool_wide)):
            counters["plain12_wide_any"] += 1
        if _at_least_one(items, _cat(exp_wide, 18, pool_wide)):
            counters["exp18_wide_any"] += 1

        per_q.append({
            "conv": conv_idx, "qa": r["qaIdx"],
            "question": q[:80], "gold": gold[:80],
            "items": items,
            "expansion": expansion,
            "base_any": base_ok, "base_count": base_count, "n_items": len(items),
            "pool_narrow": len(pool_narrow), "pool_wide": len(pool_wide),
        })

    out_path = run_dir / "hyde_preflight_v2.json"
    out_path.write_text(json.dumps(
        {"summary": counters, "n": len(target), "rows": per_q},
        indent=2,
    ))

    n = len(target)
    print("\n=== HyDE-lite v2 Preflight (at-least-one-item metric) ===")
    print(f"  N Q:                          {n}")
    print(f"  Baseline (BM25+embed render): {counters['base_any_item']}/{n}")
    print(f"  Pool upper bound (narrow):    {counters['pool_any']}/{n}")
    print(f"  Pool upper bound (widened):   {counters['pool_wide_any']}/{n}")
    print(f"  --- narrow pool + simple BM25 (replica) ---")
    print(f"  plain top-12:                 {counters['plain12_any']}/{n}")
    print(f"  plain top-18:                 {counters['plain18_any']}/{n}")
    print(f"  expanded top-12:              {counters['exp12_any']}/{n}")
    print(f"  expanded top-18:              {counters['exp18_any']}/{n}")
    print(f"  --- adjacent-widened pool ---")
    print(f"  plain top-12 wide:            {counters['plain12_wide_any']}/{n}")
    print(f"  expanded top-18 wide:         {counters['exp18_wide_any']}/{n}")
    print(f"  Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
