# Claude Implementer Workflow — ai-knot v2

Rules for Claude sessions working on `src/ai_knot_v2/`. Supplement to `src/ai_knot_v2/CLAUDE.md`.

---

## Sprint mechanics

- Each sprint is a focused unit. Start with a read of `research/aiknot_v2_product_kernel_plan.md` §4 to confirm the sprint scope.
- Do NOT implement Sprint N+1 work during Sprint N. Keep the diff minimal and reviewable.
- End of sprint: commit, push, update draft PR description with sprint tag.
- After a BG-run completes: apply multi-metric gate formula (§5.3 of plan). Accept or revert immediately.

---

## Token discipline

- Prefer Read + Grep over Agent/Explore for known file paths.
- Use Agent(subagent_type="Explore") only for open-ended codebase questions spanning >5 unknown files.
- Use Agent(subagent_type="Plan") for design review of a new sprint's scope before writing code.
- Keep plan-agents in background (run_in_background=True) when their result is not needed immediately.

---

## Parallelism rules

- Independent writes (different files): send in a single message with multiple Write/Edit calls.
- Independent Bash operations: combine with && or send as parallel Bash calls.
- Never parallelize operations that depend on each other's output (git checkout → mkdir → write files: sequential).
- After branch creation: all file writes can be parallelized.

---

## Background-task management

- BG-run naming: always pass `--run-id` or equivalent tag so scorecard can compare.
- Wait for BG completion before committing scorecard-gated changes.
- Never run a full 10-conv LOCOMO during dev iteration — 2-conv only.
- Explicit user request required for full 10-conv.

---

## Stop-and-revert protocol

1. BG-run returns scorecard.
2. Apply `is_safe_change(prev_run, new_run)` from `bench/scorecard.py`.
3. If REJECT: `git revert HEAD --no-edit` immediately. No "fix on top of regression".
4. Record revert in memory: which change, which metric failed, by how much.
5. Next session starts from the reverted baseline.

---

## Architecture gate (run before every push)

```bash
# 1. No LLM in core
grep -r "openai\|anthropic\|gpt\|claude\|litellm" src/ai_knot_v2/{core,ops,store,api}/ && echo FAIL || echo ok

# 2. No LOCOMO-specific patterns in v2 src
grep -r "locomo\|LOCOMO\|p1_1b\|conv0\|conv1" src/ai_knot_v2/{core,ops,store,api}/ && echo FAIL || echo ok

# 3. Architecture test
.venv/bin/pytest src/ai_knot_v2/tests/architecture/ -v

# 4. Format + lint + types
.venv/bin/ruff format --check src/ai_knot_v2/
.venv/bin/ruff check src/ai_knot_v2/
.venv/bin/mypy --strict src/ai_knot_v2/core src/ai_knot_v2/ops src/ai_knot_v2/store src/ai_knot_v2/api

# 5. Unit tests
.venv/bin/pytest src/ai_knot_v2/tests/unit/ -q
```

All 5 must pass before push.

---

## Memory hygiene

After each sprint, update relevant memory files if:
- A new sprint gate result changes the benchmark state.
- A new constraint or invariant is discovered.
- A design decision is made that affects future sessions.

Do NOT save: code patterns, function signatures, file paths (derivable from code). Do NOT save: current scorecard numbers (use git log / BG run artifacts).

---

## Commit conventions (see CLAUDE.md at repo root)

- Author: `alsoleg89 <155813332+alsoleg89@users.noreply.github.com>`
- Subject: short, factual, no tool names, no session URLs.
- Verify: `git log -1 --format="%an"` must be `alsoleg89`.
- Never push to main. All work → `feat/v2-product-kernel` → PR.
