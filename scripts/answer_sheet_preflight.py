"""Shift A preflight — Answer-Sheet Materialization.

Validate the core assumption of Shift A before writing production code:
*does gpt-4o-mini produce correct cat1 SET answers when the prompt context
contains a per-entity "answer sheet" (pre-aggregated list of claims) instead
of / in addition to raw turns?*

Method
------
1. Load `p1-1b-2conv/log.jsonl`; select cat1 WRONG Q (30).
2. For each Q:
   a. `analyze_query` → focus_entities.
   b. `SELECT relation, value_text, kind, source_episode_id
        FROM atomic_claims
       WHERE agent_id=? AND LOWER(subject) LIKE ?` per entity.
   c. Render an *answer sheet* string (compact, de-duplicated, grouped by
      relation).
   d. Prepend sheet to the **baseline rendered context** (already present
      in `log.jsonl.context`). We keep the raw turns — the sheet is an
      additional evidence block, not a replacement.
   e. Call gpt-4o-mini with same `ANSWER_SYSTEM` used by the bench.
   f. Judge new answer vs gold via LLM judge (same JUDGE_SYSTEM).
3. Report: NEW-CORRECT / REGRESS / UNCHANGED vs baseline verdict.

Outputs
-------
- `<run>/answer_sheet_preflight.json`: per-Q trace.
- Stdout summary.

Cost
----
~30 Q × 2 LLM calls = 60 gpt-4o-mini calls. Roughly $0.01–$0.02 total.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sqlite3
import sys
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
    subject: str
    relation: str
    value_text: str
    kind: str
    source_episode_id: str


def _fetch_claims(conn: sqlite3.Connection, agent_id: str, entities: list[str]) -> list[Claim]:
    """Return all claims where subject LIKE any of entities (case-insensitive)."""
    if not entities:
        return []
    clauses = " OR ".join(["LOWER(subject) LIKE ?"] * len(entities))
    params: list[object] = [agent_id]
    for e in entities:
        params.append(f"%{e.lower()}%")
    rows = conn.execute(
        "SELECT subject, relation, value_text, kind, source_episode_id "
        "FROM atomic_claims WHERE agent_id=? AND (" + clauses + ")",
        params,
    ).fetchall()
    out: list[Claim] = []
    seen: set[tuple[str, str, str]] = set()
    for sub, rel, val, kind, src in rows:
        key = (sub or "", rel or "", (val or "")[:80].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(Claim(sub or "", rel or "", val or "", kind or "", src or ""))
    return out


_NOISE_VALUE_RE = re.compile(
    r"^(?:it|you|your|our|my|them|us|this|that|those|these)\b",
    re.IGNORECASE,
)


def _is_noise_claim(c: Claim) -> bool:
    v = c.value_text.strip()
    if len(v) < 12:
        return True
    if _NOISE_VALUE_RE.match(v):
        return True
    return False


def _render_sheet(entity_label: str, claims: list[Claim], clean: bool = False) -> str:
    """Render a compact answer sheet — grouped by relation, de-duplicated, with evidence ids."""
    if not claims:
        return ""
    if clean:
        claims = [c for c in claims if not _is_noise_claim(c)]
        if not claims:
            return ""
    by_rel: dict[str, list[Claim]] = {}
    for c in claims:
        by_rel.setdefault(c.relation, []).append(c)
    lines = [f"# Answer sheet for {entity_label}"]
    for rel, group in sorted(by_rel.items()):
        items: list[str] = []
        for c in group:
            val = c.value_text.strip().rstrip(".")
            if len(val) > 120:
                val = val[:117] + "..."
            ep_short = c.source_episode_id.split(":")[-1] if c.source_episode_id else "?"
            items.append(f"{val} [{ep_short}]")
        lines.append(f"- {rel}: " + "; ".join(items))
    return "\n".join(lines)


def _render_multi_sheet(by_entity: dict[str, list[Claim]], clean: bool = False) -> str:
    parts: list[str] = []
    for ent, cl in by_entity.items():
        s = _render_sheet(ent, cl, clean=clean)
        if s:
            parts.append(s)
    return "\n\n".join(parts)


def _answer(client: OpenAI, context: str, question: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0,
        max_tokens=256,
    )
    content = resp.choices[0].message.content or ""
    return content.strip()


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


def _item_recall(gold: str, answer: str) -> tuple[int, int]:
    """Gold-item recall: fraction of gold items any content-token matches in answer."""
    items = re.split(r"\s*(?:,|;|\band\b|\bor\b|/)\s*", gold, flags=re.IGNORECASE)
    items = [it.strip() for it in items if it.strip()]
    low = answer.lower()
    hit = 0
    for it in items:
        if it.lower() in low:
            hit += 1
            continue
        toks = [t for t in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", it) if t.lower() not in {"the", "and", "but"}]
        if any(t.lower() in low for t in toks):
            hit += 1
    return hit, len(items) or 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--limit", type=int, default=0, help="only first N Q (0 = all)")
    ap.add_argument("--mode", choices=["prepend", "sheet_only", "prepend_clean"], default="prepend",
                    help="prepend: sheet + raw ctx; sheet_only: sheet only; prepend_clean: noise-filtered sheet + raw")
    args = ap.parse_args()

    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2

    run_dir = pathlib.Path(args.run)
    client = OpenAI()
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
    print(f"Target cat1 WRONG Q: {len(target)} (mode={args.mode})")

    conn = sqlite3.connect(args.db)
    results: list[dict] = []
    counters: dict[str, int] = {"new_correct": 0, "regress": 0, "still_wrong": 0}

    try:
        for i, r in enumerate(target):
            conv = r["convIdx"]
            agent_id = f"conv-{conv}"
            q = r["question"]
            gold = r["goldAnswer"]
            baseline_ctx = r.get("context", "") or ""
            baseline_ans = r.get("answer", "") or ""

            frame = analyze_query(q)
            entities = list(frame.focus_entities) or []
            by_ent: dict[str, list[Claim]] = {}
            for ent in entities:
                cl = _fetch_claims(conn, agent_id, [ent])
                if cl:
                    by_ent[ent] = cl
            clean = args.mode == "prepend_clean"
            sheet = _render_multi_sheet(by_ent, clean=clean)

            if args.mode == "sheet_only":
                new_ctx = sheet if sheet else baseline_ctx
            else:
                new_ctx = (sheet + "\n\n---\n\n" + baseline_ctx) if sheet else baseline_ctx

            new_ans = _answer(client, new_ctx, q)
            verdict = _judge(client, q, new_ans, gold)
            base_hit, base_total = _item_recall(gold, baseline_ans)
            new_hit, new_total = _item_recall(gold, new_ans)

            if verdict == "CORRECT":
                counters["new_correct"] += 1
            else:
                counters["still_wrong"] += 1

            results.append({
                "conv": conv,
                "qa": r["qaIdx"],
                "question": q,
                "gold": gold,
                "baseline_answer": baseline_ans,
                "new_answer": new_ans,
                "baseline_verdict": "WRONG",  # by construction
                "new_verdict": verdict,
                "baseline_item_recall": f"{base_hit}/{base_total}",
                "new_item_recall": f"{new_hit}/{new_total}",
                "focus_entities": entities,
                "n_claims": sum(len(v) for v in by_ent.values()),
                "sheet_preview": sheet[:300],
            })
            tag = "OK" if verdict == "CORRECT" else "--"
            print(f"  [{i+1:>2}/{len(target)}] {tag} conv={conv} qa={r['qaIdx']} "
                  f"items {base_hit}/{base_total}->{new_hit}/{new_total}")
    finally:
        conn.close()

    out = run_dir / f"answer_sheet_preflight_{args.mode}.json"
    out.write_text(json.dumps({
        "summary": counters,
        "n": len(target),
        "mode": args.mode,
        "rows": results,
    }, indent=2))

    print("\n=== Answer-Sheet Preflight summary ===")
    print(f"  Mode:                    {args.mode}")
    print(f"  N cat1 WRONG Q:          {len(target)}")
    print(f"  NEW-CORRECT (flip→OK):   {counters['new_correct']}/{len(target)}")
    print(f"  Still WRONG:             {counters['still_wrong']}/{len(target)}")
    print(f"  Projected cat1:          "
          f"{(13 + counters['new_correct'])}/43 = "
          f"{100*(13 + counters['new_correct'])/43:.1f}% (baseline 30.2%)")
    print(f"  Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
