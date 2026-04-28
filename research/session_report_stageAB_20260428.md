# Stage A/B Session Report — 2026-04-28

## Context

Data-flow audit revealed three P0/P1 data contract bugs that invalidated all previous bench numbers:
- **F0**: `create_storage("sqlite", dsn=...)` ignored `dsn=`; bench wrote to fallback `.ai_knot/ai_knot.db` (29 464 cross-conv facts)
- **F1**: `kb.add()` never populated structured fields (entity/attribute/value_text) → ProfileIndex/K1Router were no-ops
- **F3**: 77–89% of conv0/conv1 facts were 3-turn multi-speaker windows — per-speaker attribution broken

Branch: `feat/stage-a/data-contract`

---

## Stage A — Data Contract Repair

### A1: DSN fix (`src/ai_knot/storage/__init__.py`)
```python
if backend == "sqlite":
    db_path = dsn if dsn else os.path.join(base_dir, "ai_knot.db")
    return SQLiteStorage(db_path=db_path)
```
SQLite factory now uses `dsn` when provided instead of always falling back to `base_dir/ai_knot.db`.

### A2: Preflight guard (`aiknotbench/src/runner.ts`)
Guard fires only on first ingest of a run (`cp.ingested.length === 0`). Prevents false-positive on conv1 when conv0 data already exists in the same DB file.

### A4-trimmed: Per-speaker ingest (`aiknotbench/src/aiknot.ts`)
`ingestDated()` now calls `kb.add()` once per speaker-turn (not once per 3-turn window). Each fact = one speaker + date prefix.

### A5: Contract test
`tests/test_locomo_ingest_contract.py` — synthetic 2-session payload (not LoCoMo gold), verifies single-speaker invariant + fact count + date prefix preservation.

**Commit**: `ca391be`

---

## Stage B — ProfileIndex / K1Router

### B1: ProfileIndex (`src/ai_knot/_profile_index.py`)
In-memory `(entity, facet) → [ProfileRow]` index. `index_fact()` supports:
- Path A: structured fields (`entity`, `attribute`, `value_text`)
- Path B: parse from observation-tagged or dated-turn content format
- B1 invariant: logs WARNING if multi-speaker content detected (should never fire after A4-trimmed)

Activated by `AI_KNOT_PROFILE_INDEX=1`.

### B2: K1Router (`src/ai_knot/_k1_router.py`)
`classify_k1(question)` → `K1Query(entity, facets)` or `None`.
- Bypasses temporal/causal/yes-no openers (`_SINGLE_RE`)
- Matches profile/list/count openers (`_PROFILE_RE`)
- Requires both entity AND at least one generic facet stem (hobbies, pets, art, sports, etc.)
- Returns None if no facet → no pollution for non-profile questions

Activated by `AI_KNOT_K1_ROUTER=1`.

### B3: Remove bm25_ids skip guard (`src/ai_knot/knowledge.py`)
Profile-injected facts were silently dropped if BM25 already found them. Removed `row.fact_id not in bm25_ids` check → profile rows now always appear at head regardless of BM25 overlap (LITM fix).

### B4: Normalizer isolation
`_canonical_enrichment.py` not called from global `add()` path. P4 vocab-inflation regression isolated.

**Tests**: `tests/test_k1_router.py` (11 cases), `tests/test_profile_index.py` (7 cases)

**Commit**: `89aa625`

---

## Windowed Ingest Mode (Added during ablation)

Added `windowed` as a new `IngestMode` in `aiknotbench/src/aiknot.ts` and `aiknotbench/src/index.ts`. Implements the pre-Stage-A 3-turn sliding window behavior (date-prefixed) to allow direct comparison with historical baseline.

CLI: `--ingest-mode windowed --top-k 60`

---

## Bench Results — 2-Conv Comparison

| Config             | Cat1       | Cat2       | Cat3       | Cat4        | Cat1-4      | Total       |
|--------------------|------------|------------|------------|-------------|-------------|-------------|
| A per-turn k5      | 11/43 (25%)| 32/63 (50%)| 9/13 (69%) | 70/114 (61%)| 122/233 (52%)| 157/304 (51%)|
| A per-turn k25     | 11/43 (25%)| 36/63 (57%)| 10/13 (76%)| 69/114 (60%)| 126/233 (54%)| 163/304 (53%)|
| B per-turn k5      | 12/43 (27%)| 36/63 (57%)| 9/13 (69%) | 62/114 (54%)| 119/233 (51%)| 148/304 (48%)|
| B per-turn k25     | 12/43 (27%)| 35/63 (55%)| 8/13 (61%) | 71/114 (62%)| 126/233 (54%)| 167/304 (54%)|
| **B windowed k60** | **17/43 (39%)**| 29/63 (46%)| **10/13 (76%)**| **87/114 (76%)**| **143/233 (61%)**| **190/304 (62%)**|
| baseline (pre-A)   | 37%        | 51%        | —          | —           | —           | 62.5%       |

---

## Key Findings

### 1. Per-turn ingest kills cat1 regardless of top_k
top_k ablation (k5 / k15 / k20 / k25) showed cat1 stuck at 25% for all values. Root cause: BM25 token density. Each per-turn fact has ~30–60 tokens. A 3-turn window has ~90–180 tokens → 3× richer BM25 surface. Short facts simply don't match retrieval queries well at any recall depth.

### 2. Stage B gives marginal +2pp cat1 on per-turn config
ProfileIndex and K1Router inject profile-matched facts at head. This helps cat1 slightly (+2pp) but far below the gap caused by ingest-mode regression (−12pp from baseline).

### 3. Only windowed k60 restores baseline
`B windowed k60` = 62% total / 39% cat1, matching pre-Stage-A reference (62.5% / 37%). The Stage B B3 fix (remove bm25_ids skip guard) contributes to cat4 improvement (76% vs estimated ~61% pre-B).

### 4. Pre-Stage-A numbers are invalid
DSN regression means all bench runs before Stage A could write to a shared fallback DB. Specifically, `baseline-pr` (cat1=37%, agg=62.5%) is confirmed-valid only because it was run with the corrected code.

---

## Decision: Production Config

Use `windowed k60` as the reference configuration for any further Stage C/D experiments. Per-turn (`dated`) config is architecturally cleaner (speaker attribution) but requires Stage C K1 ensemble to close the 14pp cat1 gap.

---

## Pending

- **Stage C C1 gate**: Run `research/k1_confidence_selector_replay.ts` on conv2-9 (holdout, not conv0/1). Gate: net cat1 ≥ +5, zero control regressions.
- **Stage C C2**: Promote `_k1_ensemble.py` only after C1 gate passes, with `AI_KNOT_K1_ENSEMBLE=1` flag.
- **A3 (image/query surface)**: Deferred. Return only if Stage C C1 gate fails and ledger shows image-only evidence is the bottleneck.
