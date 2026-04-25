"""PPR preflight v2 — extend graph with content-token nodes and seed PPR
with (focus_entities ∪ salient_query_tokens).

v1 finding: pure entity-only graph + entity-only seeds is worse than BM25+embed
because PPR ignores question keywords. All Calvin-raws get high rank, including
irrelevant ones.

v2 hypothesis: if graph includes content-token nodes (non-stopword query words)
and we seed with both entities AND query tokens, PPR becomes a "multi-hop
keyword matcher" — raws that mention BOTH Calvin AND clarinet get boosted
through two paths, not one.

Usage:
    .venv/bin/python scripts/ppr_preflight_v2.py \\
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

import networkx as nx

_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from ai_knot.query_contract import analyze_query  # noqa: E402

_PROPER_NAME_RE = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b")
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
        "is",
        "it",
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
        "may",
        "might",
        "must",
        "can",
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
        "had",
        "did",
        "do",
        "done",
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
    }
)


def _content_tokens(text: str, min_len: int = 4) -> set[str]:
    out: set[str] = set()
    for m in _WORD_RE.findall(text or ""):
        low = m.lower()
        if low in _STOPWORDS:
            continue
        if len(low) < min_len:
            continue
        out.add(low)
    return out


def _extract_entities(text: str) -> set[str]:
    return {m.lower() for m in _PROPER_NAME_RE.findall(text or "")}


def _gold_tokens(gold: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", gold or "")]


def _contains_gold(text: str, gold: str) -> bool:
    toks = _gold_tokens(gold)
    if not toks:
        return True
    low = text.lower()
    return all(t in low for t in toks)


def _build_graph(
    conn: sqlite3.Connection, agent_id: str, df_cap: int
) -> tuple[nx.Graph, dict[str, str], Counter]:
    rows = conn.execute(
        "SELECT id, raw_text FROM raw_episodes WHERE agent_id=?", (agent_id,)
    ).fetchall()
    raw_text_by_id: dict[str, str] = {r[0]: r[1] or "" for r in rows}

    df: Counter = Counter()
    for _rid, text in rows:
        for tok in _content_tokens(text or ""):
            df[tok] += 1
        for ent in _extract_entities(text or ""):
            df[f"E:{ent}"] += 1

    G: nx.Graph = nx.Graph()
    for rid, text in rows:
        G.add_node(rid, kind="raw")
        for ent in _extract_entities(text or ""):
            node = f"E:{ent}"
            G.add_node(node, kind="entity")
            G.add_edge(node, rid)
        for tok in _content_tokens(text or ""):
            if df[tok] > df_cap:
                continue
            node = f"T:{tok}"
            G.add_node(node, kind="token")
            G.add_edge(node, rid)

    return G, raw_text_by_id, df


def _ppr_rank(
    G: nx.Graph, seed_nodes: list[str], raw_ids: list[str]
) -> list[tuple[str, float]]:
    personalization = {n: 1.0 for n in seed_nodes if G.has_node(n)}
    if not personalization:
        return [(rid, 0.0) for rid in raw_ids]
    scores = nx.pagerank(
        G, alpha=0.85, personalization=personalization, max_iter=200, tol=1e-7
    )
    raw_scores = [(rid, float(scores.get(rid, 0.0))) for rid in raw_ids]
    raw_scores.sort(key=lambda t: t[1], reverse=True)
    return raw_scores


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument(
        "--df-cap",
        type=int,
        default=50,
        help="Skip tokens that appear in > df-cap raws (stopword-ish)",
    )
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

    tmp_dir = tempfile.mkdtemp(prefix="ppr_preflight_v2_")
    tmp_db = str(pathlib.Path(tmp_dir) / "q.db")

    counters: dict[str, int] = {
        "base_has": 0,
        "ppr12_ent": 0,
        "ppr18_ent": 0,
        "ppr12_ent_tok": 0,
        "ppr18_ent_tok": 0,
        "ppr30_ent_tok": 0,
        "pool_has_gold": 0,
        "union_base_plus_ppr12": 0,
        "union_base_plus_ppr18": 0,
    }
    per_q: list[dict] = []

    for r in target:
        conv_idx = r["convIdx"]
        agent_id = f"conv-{conv_idx}"
        q = r["question"]
        gold = r["goldAnswer"]
        frame = analyze_query(q)
        ent_seeds = [s.lower() for s in frame.focus_entities]
        q_content = list(_content_tokens(q))

        base_ctx = r.get("context", "") or ""
        base_ok = _contains_gold(base_ctx, gold)
        if base_ok:
            counters["base_has"] += 1

        shutil.copy2(args.db, tmp_db)
        conn = sqlite3.connect(tmp_db)
        try:
            G, raw_text_by_id, df = _build_graph(conn, agent_id, args.df_cap)
        finally:
            conn.close()

        filtered_ids = [
            rid
            for rid, text in raw_text_by_id.items()
            if any(s in text.lower() for s in ent_seeds)
        ]

        if _contains_gold(" ".join(raw_text_by_id[r] for r in filtered_ids), gold):
            counters["pool_has_gold"] += 1

        ent_nodes = [f"E:{e}" for e in ent_seeds]
        tok_nodes = [f"T:{t}" for t in q_content if df.get(t, 0) <= args.df_cap]

        ranked_ent = _ppr_rank(G, ent_nodes, filtered_ids)
        ranked_ent_tok = _ppr_rank(G, ent_nodes + tok_nodes, filtered_ids)

        def _cat(ids: list[str]) -> str:
            return " ".join(raw_text_by_id.get(i, "") for i in ids)

        ppr_ent_top12 = [i for i, _ in ranked_ent[:12]]
        ppr_ent_top18 = [i for i, _ in ranked_ent[:18]]
        ppr_et_top12 = [i for i, _ in ranked_ent_tok[:12]]
        ppr_et_top18 = [i for i, _ in ranked_ent_tok[:18]]
        ppr_et_top30 = [i for i, _ in ranked_ent_tok[:30]]

        if _contains_gold(_cat(ppr_ent_top12), gold):
            counters["ppr12_ent"] += 1
        if _contains_gold(_cat(ppr_ent_top18), gold):
            counters["ppr18_ent"] += 1
        if _contains_gold(_cat(ppr_et_top12), gold):
            counters["ppr12_ent_tok"] += 1
        if _contains_gold(_cat(ppr_et_top18), gold):
            counters["ppr18_ent_tok"] += 1
        if _contains_gold(_cat(ppr_et_top30), gold):
            counters["ppr30_ent_tok"] += 1

        union12 = base_ctx + " " + _cat(ppr_et_top12)
        union18 = base_ctx + " " + _cat(ppr_et_top18)
        if _contains_gold(union12, gold):
            counters["union_base_plus_ppr12"] += 1
        if _contains_gold(union18, gold):
            counters["union_base_plus_ppr18"] += 1

        per_q.append(
            {
                "conv": conv_idx,
                "qa": r["qaIdx"],
                "question": q[:80],
                "gold": gold[:80],
                "ent_seeds": ent_seeds,
                "tok_seeds": q_content,
                "baseline_gold_in_ctx": base_ok,
                "ppr_ent_top12": _contains_gold(_cat(ppr_ent_top12), gold),
                "ppr_et_top12": _contains_gold(_cat(ppr_et_top12), gold),
                "ppr_et_top18": _contains_gold(_cat(ppr_et_top18), gold),
                "pool_has_gold": _contains_gold(_cat(filtered_ids), gold),
                "n_pool": len(filtered_ids),
                "n_tok_nodes_in_graph": sum(
                    1 for _n, d in G.nodes(data=True) if d.get("kind") == "token"
                ),
            }
        )

    out_path = run_dir / "ppr_preflight_v2.json"
    out_path.write_text(
        json.dumps({"summary": counters, "n": len(target), "rows": per_q}, indent=2)
    )

    print("\n=== PPR Preflight v2 Summary (cat1 WRONG) ===")
    n = len(target)
    print(f"  N Q:                              {n}")
    print(f"  Baseline gold-in-ctx:             {counters['base_has']}/{n}")
    print(f"  Pool upper-bound:                 {counters['pool_has_gold']}/{n}")
    print(f"  --- PPR entities only ---")
    print(f"  PPR-ent top-12:                   {counters['ppr12_ent']}/{n}")
    print(f"  PPR-ent top-18:                   {counters['ppr18_ent']}/{n}")
    print(f"  --- PPR entities + query tokens ---")
    print(f"  PPR-ent+tok top-12:               {counters['ppr12_ent_tok']}/{n}")
    print(f"  PPR-ent+tok top-18:               {counters['ppr18_ent_tok']}/{n}")
    print(f"  PPR-ent+tok top-30:               {counters['ppr30_ent_tok']}/{n}")
    print(f"  --- Union with baseline ---")
    print(f"  base ∪ PPR-ent+tok top-12:        {counters['union_base_plus_ppr12']}/{n}")
    print(f"  base ∪ PPR-ent+tok top-18:        {counters['union_base_plus_ppr18']}/{n}")
    print(f"  Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
