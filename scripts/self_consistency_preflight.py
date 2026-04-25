"""Shift B preflight — Self-Consistency Union for cat1 SET Q.

Validate Shift B before writing production code: *does calling gpt-4o-mini
n=3 times with temperature=0.7 and unioning the SET answers recover gold
items that a single deterministic call misses?*

Method
------
For each cat1 WRONG Q:
  1. Generate n=3 candidate answers with temp=0.7 (vs bench temp=0).
  2. Union: concatenate answers, split by comma/semicolon/"and"/"or",
     de-duplicate by lowercase stem.
  3. Re-render as `"<item1>, <item2>, ...."` (same shape gold expects).
  4. Judge via gpt-4o-mini LLM judge against gold.

Baseline comparison: the original WRONG answer already in log.jsonl.

Cost: 30 Q × (3 answer calls + 1 judge call) = ~120 gpt-4o-mini calls.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from collections import OrderedDict

from openai import OpenAI

_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

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
            {
                "role": "user",
                "content": (
                    f"Question: {question}\nCandidate answer: {candidate}\nGold answer: {gold}"
                ),
            },
        ],
        temperature=0,
        max_tokens=32,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(raw)
        v = parsed.get("verdict", "")
        if v in ("CORRECT", "WRONG"):
            return v
    except json.JSONDecodeError:
        pass
    m = re.search(r"CORRECT|WRONG", raw.upper())
    return m.group(0) if m else "WRONG"


def _extract_items(text: str) -> list[str]:
    """Split a SET-like answer into atomic items (trimmed, non-empty)."""
    raw = _ITEM_SPLIT.split(text.strip().rstrip("."))
    out = [x.strip().strip('".') for x in raw if x.strip()]
    seen: OrderedDict[str, str] = OrderedDict()
    for x in out:
        key = re.sub(r"[^a-z0-9]", "", x.lower())[:40]
        if not key:
            continue
        if key not in seen:
            seen[key] = x
    return list(seen.values())


def _union(samples: list[str]) -> str:
    pool: OrderedDict[str, str] = OrderedDict()
    for s in samples:
        for it in _extract_items(s):
            key = re.sub(r"[^a-z0-9]", "", it.lower())[:40]
            if not key:
                continue
            if key not in pool:
                pool[key] = it
    return ", ".join(pool.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--n", type=int, default=3, help="samples per Q")
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
    print(f"Target cat1 WRONG Q: {len(target)} (n={args.n}, T={args.temperature})")

    client = OpenAI()
    results: list[dict] = []
    counters = {"new_correct": 0, "still_wrong": 0}

    for i, r in enumerate(target):
        q = r["question"]
        gold = r["goldAnswer"]
        ctx = r.get("context", "") or ""
        samples: list[str] = []
        for _ in range(args.n):
            samples.append(_answer_sample(client, ctx, q, args.temperature))
        unioned = _union(samples) or samples[0]
        verdict = _judge(client, q, unioned, gold)
        if verdict == "CORRECT":
            counters["new_correct"] += 1
        else:
            counters["still_wrong"] += 1
        results.append({
            "conv": r["convIdx"],
            "qa": r["qaIdx"],
            "question": q,
            "gold": gold,
            "samples": samples,
            "unioned": unioned,
            "new_verdict": verdict,
        })
        tag = "OK" if verdict == "CORRECT" else "--"
        print(f"  [{i+1:>2}/{len(target)}] {tag} conv={r['convIdx']} qa={r['qaIdx']}  union={unioned[:80]!r}")

    out = run_dir / f"self_consistency_preflight_n{args.n}.json"
    out.write_text(json.dumps({"summary": counters, "n": len(target), "rows": results}, indent=2))

    print("\n=== Self-Consistency Preflight summary ===")
    print(f"  N cat1 WRONG Q:          {len(target)}")
    print(f"  NEW-CORRECT (flip→OK):   {counters['new_correct']}/{len(target)}")
    print(f"  Still WRONG:             {counters['still_wrong']}/{len(target)}")
    print(f"  Projected cat1:          {13 + counters['new_correct']}/43 = "
          f"{100*(13 + counters['new_correct'])/43:.1f}% (baseline 30.2%)")
    print(f"  Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
