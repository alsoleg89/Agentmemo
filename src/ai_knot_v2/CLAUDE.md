# ai-knot v2 — Architectural Invariants

This file governs ALL sessions working on `src/ai_knot_v2/`. Rules below are non-negotiable.

---

## 1. No LLM in the memory core

```
FORBIDDEN imports in core/ ops/ store/ api/:
  openai  anthropic  gpt  claude  litellm  langchain
```

CI gate: `tests/architecture/test_no_llm_in_core.py` will fail the build if any LLM import is detected.

LLM is allowed ONLY in:
- `synth/` (extraction oracle, optional, enabled via `--llm-oracle`)
- `bench/` (answer rendering and judge, enabled via `--llm-answerer` / `--llm-judge`)

Never make LLM extraction mandatory for memory correctness.

---

## 2. Full schema from Sprint 1 — no schema rewrites

`MemoryAtom` in `core/atom.py` defines the permanent schema. Fields evolve in
precision (placeholder → full implementation) across sprints, but the dataclass
signature never changes after Sprint 1.

If you feel the urge to rename or remove a field, that is a signal to fix the
computation function, not the schema.

---

## 3. Multi-metric stop rule

Every BG-run produces a scorecard. Accept a change ONLY IF ALL hold:

```
cat1 monotonic up (or stable if targeting another metric)
GoldEvidenceCoverage@Budget up
ContextDilutionRate not up
UnsafeOmissionRate not up
DependencyClosureRecall not down
test_no_llm_in_core passes
no LOCOMO-specific code/keywords added (grep-check)
```

If any condition fails → REVERT immediately. Do not stack fixes on a regressed baseline.

---

## 4. Forbidden patterns (any sprint)

- Benchmark-tailored regex or vocabulary (LOCOMO-specific word lists).
- Prompt engineering as a fix for retrieval failures (push fix into retrieval/materializer).
- Hardcoded LOCOMO question IDs, answer patterns, or conversation indices.
- Broad context-widening as a substitute for evidence planning.
- LLM calls from `ops/read.py`, `ops/write.py`, `ops/planner.py`, `core/`, `store/`, `api/`.

---

## 5. Sprint defaults

- Default LLM provider (bench only): `gpt-4o-mini` (OpenAI).
- Default synthetic domain (Sprint 6): `medical`.
- Gate failure → revert (not iterate on regressed baseline).
- BG-runs during development: 2-conv only; full 10-conv on explicit request.
- Cost discipline: each BG-run ≤ ~$0.5 (product-default mode).

---

## 6. Architecture check commands

```bash
# Confirm no LLM in core (run before every commit to v2)
grep -r "openai\|anthropic\|gpt\|claude\|litellm" src/ai_knot_v2/{core,ops,store,api}/ && echo FAIL || echo ok

# mypy strict (v2 only)
.venv/bin/mypy --strict src/ai_knot_v2/core src/ai_knot_v2/ops src/ai_knot_v2/store src/ai_knot_v2/api

# ruff
.venv/bin/ruff format --check src/ai_knot_v2/
.venv/bin/ruff check src/ai_knot_v2/

# architecture gate — use -p no:cov (pyproject addopts applies coverage to all runs;
# v2 coverage gate re-enabled in Sprint 6 when codebase is populated)
.venv/bin/pytest src/ai_knot_v2/tests/architecture/ -p no:cov -v

# unit tests (Sprint 1+)
.venv/bin/pytest src/ai_knot_v2/tests/unit/ -p no:cov -v

# integration tests (Sprint 2+)
.venv/bin/pytest src/ai_knot_v2/tests/integration/ -p no:cov -v
```
