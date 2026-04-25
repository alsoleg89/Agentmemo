"""PPR preflight — test if personalized PageRank over entity↔raw bipartite
graph would put gold evidence into render top-K for cat1 WRONG questions.

For each cat1 WRONG Q in a baseline run:
  1. Load all raws from knot.db for the Q's agent_id.
  2. Build bipartite graph: entity-node ↔ raw-node (edge per proper-name mention).
  3. Run personalized PageRank with frame.focus_entities as seeds.
  4. Rank entity-filtered raws by PPR score, take top-12 / 18 / 30.
  5. Check if gold tokens appear in concatenated top-K text.

Output: counts of gold-in-top-K for PPR vs baseline gold-in-context (from
the logged BM25+embed context), plus an upper-bound (gold-in-pool).

This is a *necessary-but-not-sufficient* signal — it only tells us whether
PPR makes gold *reachable* within render budget. Bench delta depends on
the LLM's extraction from the re-ranked context.

Usage:
    .venv/bin/python scripts/ppr_preflight.py \\
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

import networkx as nx

_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from ai_knot.query_contract import analyze_query  # noqa: E402

_PROPER_NAME_RE = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b")


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
    conn: sqlite3.Connection, agent_id: str
) -> tuple[nx.Graph, dict[str, str]]:
    G: nx.Graph = nx.Graph()
    raw_text_by_id: dict[str, str] = {}
    rows = conn.execute(
        "SELECT id, raw_text FROM raw_episodes WHERE agent_id=?", (agent_id,)
    ).fetchall()
    for rid, text in rows:
        raw_text_by_id[rid] = text or ""
        G.add_node(rid, kind="raw")
        for ent in _extract_entities(text or ""):
            node = f"E:{ent}"
            G.add_node(node, kind="entity")
            G.add_edge(node, rid)
    return G, raw_text_by_id


def _ppr_rank(
    G: nx.Graph, seed_entities: list[str], raw_ids: list[str]
) -> list[tuple[str, float]]:
    personalization = {}
    for ent in seed_entities:
        node = f"E:{ent.lower()}"
        if G.has_node(node):
            personalization[node] = 1.0
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
    args = ap.parse_args()

    run_dir = pathlib.Path(args.run)
    log_path = run_dir / "log.jsonl"
    if not log_path.exists():
        print(f"ERROR: {log_path} not found", file=sys.stderr)
        return 2

    rows: list[dict] = []
    with log_path.open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    target = [r for r in rows if r.get("category") == 1 and r.get("verdict") == "WRONG"]
    print(f"Target cat1 WRONG Q: {len(target)}")

    tmp_dir = tempfile.mkdtemp(prefix="ppr_preflight_")
    tmp_db = str(pathlib.Path(tmp_dir) / "q.db")

    counters = {
        "base_has": 0,
        "ppr12": 0,
        "ppr18": 0,
        "ppr30": 0,
        "pool_has_gold": 0,
        "no_seeds": 0,
        "empty_pool": 0,
    }
    per_q: list[dict] = []

    for r in target:
        conv_idx = r["convIdx"]
        agent_id = f"conv-{conv_idx}"
        q = r["question"]
        gold = r["goldAnswer"]
        frame = analyze_query(q)
        seeds = list(frame.focus_entities)

        base_ctx = r.get("context", "") or ""
        base_ok = _contains_gold(base_ctx, gold)
        if base_ok:
            counters["base_has"] += 1

        shutil.copy2(args.db, tmp_db)
        conn = sqlite3.connect(tmp_db)
        try:
            G, raw_text_by_id = _build_graph(conn, agent_id)
        finally:
            conn.close()

        seeds_lower = [s.lower() for s in seeds]
        if not seeds_lower:
            counters["no_seeds"] += 1
            filtered_ids: list[str] = []
        else:
            filtered_ids = [
                rid
                for rid, text in raw_text_by_id.items()
                if any(s in text.lower() for s in seeds_lower)
            ]

        if not filtered_ids:
            counters["empty_pool"] += 1

        ranked = _ppr_rank(G, seeds, filtered_ids) if filtered_ids else []
        top12_ids = [rid for rid, _ in ranked[:12]]
        top18_ids = [rid for rid, _ in ranked[:18]]
        top30_ids = [rid for rid, _ in ranked[:30]]

        def _cat(ids: list[str]) -> str:
            return " ".join(raw_text_by_id.get(rid, "") for rid in ids)

        ppr12_ok = _contains_gold(_cat(top12_ids), gold) if top12_ids else False
        ppr18_ok = _contains_gold(_cat(top18_ids), gold) if top18_ids else False
        ppr30_ok = _contains_gold(_cat(top30_ids), gold) if top30_ids else False
        pool_ok = _contains_gold(_cat(filtered_ids), gold) if filtered_ids else False

        if ppr12_ok:
            counters["ppr12"] += 1
        if ppr18_ok:
            counters["ppr18"] += 1
        if ppr30_ok:
            counters["ppr30"] += 1
        if pool_ok:
            counters["pool_has_gold"] += 1

        per_q.append(
            {
                "conv": conv_idx,
                "qa": r["qaIdx"],
                "question": q[:80],
                "gold": gold[:80],
                "seeds": seeds,
                "baseline_gold_in_ctx": base_ok,
                "ppr_top12": ppr12_ok,
                "ppr_top18": ppr18_ok,
                "ppr_top30": ppr30_ok,
                "pool_has_gold": pool_ok,
                "n_pool": len(filtered_ids),
                "n_entities_in_graph": sum(
                    1 for _n, d in G.nodes(data=True) if d.get("kind") == "entity"
                ),
            }
        )

    out_path = run_dir / "ppr_preflight.json"
    out_path.write_text(
        json.dumps(
            {"summary": counters, "n": len(target), "rows": per_q},
            indent=2,
        )
    )

    print("\n=== PPR Preflight Summary (cat1 WRONG) ===")
    print(f"  N Q:                        {len(target)}")
    print(f"  Q with no seed entities:    {counters['no_seeds']}")
    print(f"  Q with empty filtered pool: {counters['empty_pool']}")
    print(f"  Baseline gold-in-ctx:       {counters['base_has']}/{len(target)}")
    print(f"  Pool upper-bound (any raw): {counters['pool_has_gold']}/{len(target)}")
    print(f"  PPR top-12 gold-in-ctx:     {counters['ppr12']}/{len(target)}")
    print(f"  PPR top-18 gold-in-ctx:     {counters['ppr18']}/{len(target)}")
    print(f"  PPR top-30 gold-in-ctx:     {counters['ppr30']}/{len(target)}")
    print(f"  Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
