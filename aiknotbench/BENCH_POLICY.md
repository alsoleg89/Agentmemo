# BENCH_POLICY — Bench Specificity & Reproducibility Rules

These rules govern what changes are allowed in the LOCOMO benchmark harness
and the ai-knot product code that backs it.

## Rules

### 1. No hardcoded noun or phrase lists in materializer regex

Regex patterns in `src/ai_knot/materialization.py` must match generic English
grammatical frames, not a closed vocabulary of specific nouns that happen to
appear in LOCOMO gold data.

Enforcement: `aiknotbench/scripts/lint_materializer.py` (CI check).

Bad example:
```python
r"^I\s+(?:visited?)\s+(?:store|park|gym|hospital|restaurant)..."
```

Good example:
```python
r"^I\s+(?:visited?|stopped\s+by|went\s+to)\s+(.+?)\.?$"
```

### 2. No dataset-sized magic numbers in default profiles

A `char_budget > 16 000` in the `balanced` or `narrow` profile must include a
`# justification:` comment with a non-LOCOMO-specific rationale, or the value
moves to a dedicated profile (e.g. `"locomo"`).

File: `src/ai_knot/query_runtime.py` — `_PROFILE_CAPS`.

### 3. No reachability-less relations

A relation name emitted by `_FP_EVENT_PATTERNS` / `_FP_STATE_PATTERNS` must
have a matching entry in `RELATION_VERBS` (`src/ai_knot/relation_vocab.py`).
Asserted by test in `tests/test_materializer_frames_v*.py`.

### 4. New regex requires generic test cases

Any new pattern added to the materializer must ship with ≥ 3 parametrized
English test cases. None of the test strings may be copied from
`data/locomo10.json` or resemble LOCOMO proper nouns / scenario text.

### 5. New config knob → `canonical.json` in the same PR

Every new CLI flag or env var that affects bench outcome must be added to
`aiknotbench/config/canonical.json` in the same PR. CI diff check enforces this.

### 6. No pre-judge scoring twists

`aiknotbench/src/evaluator.ts` must not normalise, lowercase, strip punctuation,
or pattern-match candidate/gold answers before passing them to the LLM judge.
The judge LLM is the sole source of verdict. No exact-match short-circuits.

## Anti-patterns (reject PR)

The following are **bench hacks** — changes that inflate benchmark numbers
without improving general product quality:

- Adding LOCOMO-specific phrases or nouns to `_CURRENT_SIGNALS`, `_HISTORICAL_SIGNALS`, `_SET_NOUN_HEADS`, or materializer patterns.
- Editing `ANSWER_SYSTEM`, `JUDGE_SYSTEM`, or `_EXTRACTION_SYSTEM_PROMPT`.
- Cat5 / "Not mentioned" special-casing in product code (`knowledge.py`, `query_runtime.py`).
- Exact-match or normalisation short-circuit in `evaluator.ts`.
- Resurrecting `_pool_recall` as a parallel fast-path.
- `search_claims_semantic` top_k > 60.
- Linear normalised score combination instead of RRF (distribution mismatch).
- Trust-discount / recency-boost from legacy pool recall in query runtime.
