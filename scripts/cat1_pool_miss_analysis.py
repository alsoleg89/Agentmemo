"""cat1 pool-miss analysis — for each cat1 WRONG Q where gold is absent from
the entity-filtered pool, classify *why* the gold-bearing raws were missed.

Hypothesis space:
  A. Co-reference: gold raw uses he/she/they/we instead of the entity name.
  B. Speaker continuation: gold raw is the co-speaker's reply (no name mention
     even via prefix), e.g. Caroline answers a Melanie question.
  C. Cross-turn attribution: the factual claim is split across two turns
     (Q entity in turn N-1, gold noun in turn N).
  D. Pure semantic gap: gold raw mentions neither the entity name nor any
     obvious co-reference; requires multi-hop to attribute.

For each miss Q:
  1. Compute full entity-filtered pool (current behaviour).
  2. Scan *all* raws in the agent_id for gold-token coverage.
  3. For each gold-bearing raw, inspect:
       - is the raw itself a speaker-reply (no entity mention)?
       - does adjacent turn (prev/next in session) mention the entity?
       - does raw contain pronouns (co-reference candidates)?

Usage:
    .venv/bin/python scripts/cat1_pool_miss_analysis.py \\
        --db aiknotbench/data/runs/p1-1b-2conv/knot.db \\
        --run aiknotbench/data/runs/p1-1b-2conv
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from ai_knot.query_contract import analyze_query  # noqa: E402

_PRONOUN_RE = re.compile(
    r"\b(he|she|they|we|him|her|them|us|his|hers|their|theirs|ours)\b",
    re.IGNORECASE,
)
_YOU_RE = re.compile(r"\b(you|your|yours)\b", re.IGNORECASE)


def _gold_tokens(gold: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", gold or "")]


def _contains_all_gold(text: str, gold_toks: list[str]) -> bool:
    if not gold_toks:
        return True
    low = (text or "").lower()
    return all(t in low for t in gold_toks)


def _contains_any_gold(text: str, gold_toks: list[str]) -> list[str]:
    low = (text or "").lower()
    return [t for t in gold_toks if t in low]


def _load_all_raws(
    conn: sqlite3.Connection, agent_id: str
) -> list[tuple[str, str, str, str, str]]:
    rows = conn.execute(
        "SELECT id, session_id, turn_id, speaker, raw_text "
        "FROM raw_episodes WHERE agent_id=?",
        (agent_id,),
    ).fetchall()
    return [(r[0], r[1] or "", r[2] or "", r[3] or "", r[4] or "") for r in rows]


def _session_order(raws: list[tuple[str, str, str, str, str]]) -> dict[str, list[str]]:
    by_session: dict[str, list[tuple[str, str, str]]] = {}
    for rid, sid, tid, _sp, _rt in raws:
        by_session.setdefault(sid, []).append((rid, tid, _rt))

    def _ti(t: str) -> int:
        try:
            return int(t.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            return 0

    ordered: dict[str, list[str]] = {}
    for sid, lst in by_session.items():
        lst.sort(key=lambda x: _ti(x[1]))
        ordered[sid] = [rid for rid, _tid, _rt in lst]
    return ordered


def _neighbours(
    raws: list[tuple[str, str, str, str, str]], ordered: dict[str, list[str]]
) -> dict[str, tuple[str | None, str | None]]:
    out: dict[str, tuple[str | None, str | None]] = {}
    for sid, rids in ordered.items():
        for i, rid in enumerate(rids):
            prev = rids[i - 1] if i > 0 else None
            nxt = rids[i + 1] if i + 1 < len(rids) else None
            out[rid] = (prev, nxt)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--run", required=True)
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

    per_q: list[dict] = []
    bucket = {
        "pool_already_has_gold": 0,
        "no_gold_raw_anywhere": 0,
        "miss_coref_pronoun": 0,
        "miss_speaker_continuation": 0,
        "miss_cross_turn_neighbour_mentions": 0,
        "miss_pure_semantic_gap": 0,
    }

    conn = sqlite3.connect(args.db)
    try:
        for r in target:
            conv_idx = r["convIdx"]
            agent_id = f"conv-{conv_idx}"
            q = r["question"]
            gold = r["goldAnswer"]
            gold_toks = _gold_tokens(gold)
            frame = analyze_query(q)
            seeds = [s.lower() for s in frame.focus_entities]

            raws = _load_all_raws(conn, agent_id)
            ordered = _session_order(raws)
            nb = _neighbours(raws, ordered)
            by_id = {rid: (sid, tid, sp, rt) for rid, sid, tid, sp, rt in raws}

            pool_ids = [
                rid
                for rid, _sid, _tid, _sp, rt in raws
                if any(s in rt.lower() for s in seeds)
            ]
            pool_has = _contains_all_gold(
                " ".join(by_id[rid][3] for rid in pool_ids), gold_toks
            )

            if pool_has:
                bucket["pool_already_has_gold"] += 1
                per_q.append(
                    {
                        "conv": conv_idx,
                        "qa": r["qaIdx"],
                        "status": "pool_has_gold",
                        "question": q[:80],
                        "gold": gold[:60],
                    }
                )
                continue

            gold_raws: list[dict] = []
            for rid, sid, tid, sp, rt in raws:
                matched = _contains_any_gold(rt, gold_toks)
                if not matched:
                    continue
                prev_id, next_id = nb.get(rid, (None, None))
                prev_rt = by_id[prev_id][3] if prev_id in by_id else ""
                next_rt = by_id[next_id][3] if next_id in by_id else ""
                entity_in_raw = any(s in rt.lower() for s in seeds)
                entity_in_prev = any(s in prev_rt.lower() for s in seeds)
                entity_in_next = any(s in next_rt.lower() for s in seeds)
                pronoun_in_raw = bool(_PRONOUN_RE.search(rt))
                you_in_raw = bool(_YOU_RE.search(rt))
                gold_raws.append(
                    {
                        "rid": rid,
                        "session_id": sid,
                        "turn_id": tid,
                        "speaker": sp,
                        "raw_prefix": rt[:40],
                        "raw_text": rt,
                        "matched_gold_tokens": matched,
                        "entity_in_raw": entity_in_raw,
                        "entity_in_prev_turn": entity_in_prev,
                        "entity_in_next_turn": entity_in_next,
                        "pronoun_in_raw": pronoun_in_raw,
                        "you_in_raw": you_in_raw,
                    }
                )

            if not gold_raws:
                bucket["no_gold_raw_anywhere"] += 1
                per_q.append(
                    {
                        "conv": conv_idx,
                        "qa": r["qaIdx"],
                        "status": "no_gold_raw_anywhere",
                        "question": q[:80],
                        "gold": gold[:60],
                    }
                )
                continue

            full_gold_raws = [
                g
                for g in gold_raws
                if _contains_all_gold(g["raw_text"], gold_toks)
            ]
            cover = full_gold_raws or gold_raws

            primary_cause = "miss_pure_semantic_gap"
            any_adjacent_mention = any(
                g["entity_in_prev_turn"] or g["entity_in_next_turn"] for g in cover
            )
            any_pronoun = any(g["pronoun_in_raw"] or g["you_in_raw"] for g in cover)

            if any_adjacent_mention:
                primary_cause = "miss_cross_turn_neighbour_mentions"
            elif any_pronoun:
                primary_cause = "miss_coref_pronoun"

            speaker_continuation = all(
                not g["entity_in_raw"] and (g["entity_in_prev_turn"])
                for g in cover
            )
            if speaker_continuation:
                primary_cause = "miss_speaker_continuation"

            bucket[primary_cause] += 1
            per_q.append(
                {
                    "conv": conv_idx,
                    "qa": r["qaIdx"],
                    "status": primary_cause,
                    "question": q[:80],
                    "gold": gold[:80],
                    "seeds": seeds,
                    "n_gold_raws": len(gold_raws),
                    "n_full_gold_raws": len(full_gold_raws),
                    "samples": [
                        {
                            "matched": g["matched_gold_tokens"],
                            "entity_in_raw": g["entity_in_raw"],
                            "entity_in_prev": g["entity_in_prev_turn"],
                            "entity_in_next": g["entity_in_next_turn"],
                            "pronoun_in_raw": g["pronoun_in_raw"],
                            "you_in_raw": g["you_in_raw"],
                            "speaker": g["speaker"],
                            "raw_prefix": g["raw_prefix"],
                        }
                        for g in cover[:3]
                    ],
                }
            )
    finally:
        conn.close()

    out_path = run_dir / "cat1_pool_miss.json"
    out_path.write_text(
        json.dumps({"buckets": bucket, "n": len(target), "rows": per_q}, indent=2)
    )

    print("\n=== cat1 Pool-Miss Buckets ===")
    for k, v in bucket.items():
        print(f"  {k:38s}: {v}")
    print(f"  Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
