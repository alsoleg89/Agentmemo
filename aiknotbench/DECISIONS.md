# Bench Decision Log

Append one entry per experiment. Every commit that touches product code or
bench settings must have a paired entry here before it lands on the branch.

**Decisions:** ACCEPT | REVERT | PARK (PARK = keep branch alive, diagnosis in progress)

---

## Template

```
## YYYY-MM-DD — <title>

**Commit:** `<sha>` on `<branch>`
**Baseline:** `baselines/latest_2conv.json` (label: `<label>`, cat1-4 = X %)
**Run:** `data/runs/<run-id>/report.json` (cat1-4 = Y %, delta = ±Z pp)
**Config deviations:** none | [list of knob diffs from canonical.json]
**Decision:** ACCEPT | REVERT | PARK
**Reason:** one-line summary
**Next baseline update:** yes | no (insufficient improvement) | no (gate failed)
```

---

## 2026-04-21 — Decision pipeline bootstrap

**Commit:** `(pipeline PRs 1–4)` on `feature/configurable-mcp-env-v0.9.4`
**Baseline:** pf3-phase1 manually recorded, 59.2 % cat1-4 (unverified in registry)
**Run:** n/a — infra-only PRs, no bench run
**Config deviations:** n/a
**Decision:** ACCEPT
**Reason:** Process infra; no product code changed; cannot regress bench numbers
**Next baseline update:** no (infra only)

---

## 2026-04-21 — Moves A+B+C+D (MMR, fallback gate, conditional RRF, debug trace)

**Commit:** `3d3752b` + `06f30f5` + `2251e1d` on `feature/configurable-mcp-env-v0.9.4`
**Baseline:** pf3-phase1-2conv, 59.2 % cat1-4 (gpt-4o-mini)
**Run:** `gate-06f30f5-2conv-drift` — drift run (ollama:qwen2.5:7b), NOT canonical
**Config deviations:** answer=ollama:qwen2.5:7b, judge=ollama:qwen2.5:7b; .env bug caused all prior runs to use ollama instead of OpenAI
**Decision:** PARK — drift run; awaiting canonical gpt-4o-mini gate `gate-23cd897-2conv`
**Reason:** .env was not sourced by tsx (Node); fixed in commit `20d25fd`; canonical gate now running
**Drift-run numbers (informational only, not comparable to baseline):**
  - cat1-4 aggregate: 60.1 % (+0.9 pp vs pf3 baseline of 59.2 %)
  - cat1: 18.6 % (−11.6 pp — model artifact: qwen much weaker on set-valued list-all questions)
  - cat2: 57.1 % (+11.1 pp — confirms MMR session diversity working)
  - cat3: 53.8 % (−7.7 pp — within noise on qwen)
  - cat4: 78.1 % (+0.9 pp)
**Next baseline update:** pending canonical run result

---

## 2026-04-21 — Move E (SET-aware cap widening)

**Commit:** `23cd897` on `feature/configurable-mcp-env-v0.9.4`
**Baseline:** pf3-phase1-2conv, 59.2 % cat1-4 (gpt-4o-mini)
**Run:** `gate-23cd897-2conv` — canonical run (gpt-4o-mini), IN PROGRESS
**Config deviations:** none expected
**Decision:** PENDING — gate running
**Reason:** Widen render funnel for SET queries (render_top_k 12→18, collect_cap 15→22, char_budget 22K→30K) to address Cat1 M-type failures (46 % of Cat1 wrong: facts in context, model listed only subset)

---

## Known bad artifacts

### `data/runs/ddsa-off/`

`report.json` records `gpt-4o-mini` for both models.
`checkpoint.json` records `ollama:qwen2.5:7b` for both.
Root cause: checkpoint saved model from run-start env; report read model
from end-of-run CLI state after a manual model swap mid-run.
Fix shipped in Phase 2 (run_config.json written once at start, never mutated).
Run numbers from this dir are **not comparable** to any baseline.

### `data/runs/phase2-2conv/`, `phase3-2conv/`, `phase5-2conv/`

All three used `ollama:qwen2.5:7b` for answer and judge (local dev config).
pf3 baselines used `gpt-4o-mini`. Numbers are **not comparable**.
