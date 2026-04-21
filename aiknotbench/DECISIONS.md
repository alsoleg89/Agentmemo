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
