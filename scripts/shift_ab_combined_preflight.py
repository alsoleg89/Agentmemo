"""Shift A + B stacked preflight — validate architectural_ideas combined 50-58% projection.

Method
------
1. Build per-entity answer sheet from atomic_claims (Shift A).
2. Prepend sheet to baseline ctx.
3. Generate n=3 samples at T=0.7 (Shift B).
4. Item-level union with dedup.
5. Judge via gpt-4o-mini.

Cost: 30 Q × (3 answer + 1 judge) = 120 gpt-4o-mini calls.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sqlite3
import sys
from collections import OrderedDict
from dataclasses import dataclass

from openai import OpenAI

_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from ai_knot.query_contract import analyze_query  # noqa: E402

ANSWER_SYSTEM = "Answer the question based on the memory context below. Answer concisely."
JUDGE_SYSTEM = """You are an evaluation judge. Given a question, a candidate answer, and the gold answer,
decide whether the candidate answer is correct.

Return JSON exactly like: {"verdict": "CORRECT"} or {"verdict": "WRONG"}

Rules:
- CORRECT if the candidate answer conveys the same essential information as the gold answer.
- Exact wording is not required; semantic equivalence is sufficient.
- WRONG if the candidate answer is missing key facts, contradicts the gold, or is irrelevant.
- Do not output anything other than the JSON object."""

_ITEM_SPLIT = re.compile(r"\s*(?:,|;|\band\b|\bor\b|/)\s*", re.IGNORECASE)
_NOISE_VALUE_RE = re.compile(
    r"^(?:it|you|your|our|my|them|us|this|that|those|these)\b",
    re.IGNORECASE,
)


def _load_env() -> None:
    env_path = _ROOT / "aiknotbench" / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


@dataclass
class Claim:
    relation: str
    value_text: str
    source_episode_id: str


def _fetch_claims(conn: sqlite3.Connection, agent_id: str, entities: list[str]) -> list[Claim]:
    if not entities:
        return []
    clauses = " OR ".join(["LOWER(subject) LIKE ?"] * len(entities))
    params: list[object] = [agent_id]
    for e in entities:
        params.append(f"%{e.lower()}%")
    rows = conn.execute(
        "SELECT relation, value_text, source_episode_id "
        "FROM atomic_claims WHERE agent_id=? AND (" + clauses + ")",
        params,
    ).fetchall()
    seen: set[tuple[str, str]] = set()
    out: list[Claim] = []
    for rel, val, src in rows:
        val = val or ""
        if len(val.strip()) < 12 or _NOISE_VALUE_RE.match(val.strip()):
            continue
        key = (rel or "", val[:80].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(Claim(rel or "", val, src or ""))
    return out


def _render_sheet(entity: str, claims: list[Claim]) -> str:
    if not claims:
        return ""
    by_rel: dict[str, list[Claim]] = {}
    for c in claims:
        by_rel.setdefault(c.relation, []).append(c)
    lines = [f"# Answer sheet for {entity}"]
    for rel, grp in sorted(by_rel.items()):
        items: list[str] = []
        for c in grp:
            val = c.value_text.strip().rstrip(".")
            if len(val) > 120:
                val = val[:117] + "..."
            ep_short = c.source_episode_id.split(":")[-1] if c.source_episode_id else "?"
            items.append(f"{val} [{ep_short}]")
        lines.append(f"- {rel}: " + "; ".join(items))
    return "\n".join(lines)


def _answer_sample(client: OpenAI, context: str, question: str, temperature: float) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=temperature,
        max_tokens=256,
    )
    return (resp.choices[0].message.content or "").strip()


def _judge(client: OpenAI, question: str, candidate: str, gold: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": f"Question: {question}\nCandidate answer: {candidate}\nGold answer: {gold}"},
        ],
        temperature=0,
        max_tokens=32,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(raw)
        if parsed.get("verdict") in ("CORRECT", "WRONG"):
            return parsed["verdict"]
    except json.JSONDecodeError:
        pass
    m = re.search(r"CORRECT|WRONG", raw.upper())
    return m.group(0) if m else "WRONG"


def _union_items(samples: list[str]) -> str:
    pool: OrderedDict[str, str] = OrderedDict()
    for s in samples:
        for it in _ITEM_SPLIT.split(s.strip().rstrip(".")):
            it = it.strip().strip('".')
            if not it:
                continue
            key = re.sub(r"[^a-z0-9]", "", it.lower())[:40]
            if key and key not in pool:
                pool[key] = it
    return ", ".join(pool.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2

    run_dir = pathlib.Path(args.run)
    rows: list[dict] = []
    with (run_dir / "log.jsonl").open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    target = [r for r in rows if r.get("category") == 1 and r.get("verdict") == "WRONG"]
    if args.limit:
        target = target[: args.limit]
    print(f"Target cat1 WRONG Q: {len(target)} (A+B stacked, n={args.n}, T={args.temperature})")

    client = OpenAI()
    conn = sqlite3.connect(args.db)
    results: list[dict] = []
    counters = {"new_correct": 0, "still_wrong": 0}

    try:
        for i, r in enumerate(target):
            conv = r["convIdx"]
            agent_id = f"conv-{conv}"
            q = r["question"]
            gold = r["goldAnswer"]
            baseline_ctx = r.get("context", "") or ""
            frame = analyze_query(q)
            entities = list(frame.focus_entities) or []

            sheets: list[str] = []
            total_claims = 0
            for ent in entities:
                cl = _fetch_claims(conn, agent_id, [ent])
                if cl:
                    sheets.append(_render_sheet(ent, cl))
                    total_claims += len(cl)
            sheet = "\n\n".join(sheets)
            new_ctx = (sheet + "\n\n---\n\n" + baseline_ctx) if sheet else baseline_ctx

            samples = [_answer_sample(client, new_ctx, q, args.temperature) for _ in range(args.n)]
            unioned = _union_items(samples) or samples[0]
            verdict = _judge(client, q, unioned, gold)

            if verdict == "CORRECT":
                counters["new_correct"] += 1
            else:
                counters["still_wrong"] += 1

            results.append({
                "conv": conv,
                "qa": r["qaIdx"],
                "question": q,
                "gold": gold,
                "focus_entities": entities,
                "n_claims": total_claims,
                "samples": samples,
                "unioned": unioned,
                "new_verdict": verdict,
            })
            tag = "OK" if verdict == "CORRECT" else "--"
            print(f"  [{i+1:>2}/{len(target)}] {tag} conv={conv} qa={r['qaIdx']}  claims={total_claims}  union={unioned[:80]!r}")
    finally:
        conn.close()

    out = run_dir / f"shift_ab_combined_preflight_n{args.n}.json"
    out.write_text(json.dumps({"summary": counters, "n": len(target), "rows": results}, indent=2))

    print("\n=== Shift A+B Stacked summary ===")
    print(f"  N cat1 WRONG Q:          {len(target)}")
    print(f"  NEW-CORRECT (flip→OK):   {counters['new_correct']}/{len(target)}")
    print(f"  Still WRONG:             {counters['still_wrong']}/{len(target)}")
    print(f"  Projected cat1:          {13 + counters['new_correct']}/43 = "
          f"{100*(13 + counters['new_correct'])/43:.1f}% (baseline 30.2%, architectural_ideas projected 50-58%)")
    print(f"  Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
