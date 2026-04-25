# Impact Analysis: Pattern Facts on LOCOMO conv-0

## Date: 2026-04-11

---

## Current Baseline (v094-entity-scope-all, corrupted DB)

| Cat | Pass | Total | Rate | Description |
|-----|------|-------|------|-------------|
| 1 | 8 | 32 | 25.0% | Single-hop (actually 66% aggregation) |
| 2 | 15 | 37 | 40.5% | Multi-hop (actually 100% temporal "When") |
| 3 | 5 | 13 | 38.5% | Reasoning / inference |
| 4 | 23 | 36 | 63.9% | World knowledge + context |
| **Overall** | **51** | **118** | **43.2%** | |

Note: measured on corrupted DB (16x duplication, 6959 records instead of ~700).
Baseline on clean DB is UNKNOWN — must measure first.

---

## Failure Decomposition by Root Cause

### Cat 1 Failures (24 total)

| Root cause | Count | Example | Pattern helps? |
|------------|-------|---------|---------------|
| Multi-source aggregation | 21 | "What activities does Melanie partake in?" (pottery, camping, painting, swimming — 4+ sessions) | **YES** |
| Single-source lookup | 3 | "What is Caroline's identity?" (transgender — one fact) | No |

**88% of Cat 1 failures are aggregation** — answer requires collecting items from multiple sessions.
Pattern facts (token-union clusters) directly address this: all activity tokens in one document.

Specific aggregation failures that patterns should fix:
- Q16: What activities does Melanie partake in? → pottery, camping, painting, swimming (4 sessions)
- Q19: Where has Melanie camped? → beach, mountains, forest (3 sessions)
- Q39: What activities has Melanie done with her family? → 6 items from 6 sessions
- Q52: What has Melanie painted? → Horse, sunset, sunrise (3 sessions)
- Q61: What instruments does Melanie play? → clarinet and violin (2 sessions)
- Q62: What musical artists has Melanie seen? → Summer Sounds, Matt Patterson (2 sessions)
- Q66: What changes has Caroline faced? → body changes, losing friends (2 sessions)
- Q71: What transgender events has Caroline attended? → poetry reading, conference (2 sessions)

### Cat 2 Failures (22 total)

| Root cause | Count | Example | Pattern helps? |
|------------|-------|---------|---------------|
| Single-source temporal | 22 | "When did Caroline go to the LGBTQ support group?" → 7 May 2023 (one turn: D1:3) | **NO** |

**100% of Cat 2 failures are single-source "When did X?" questions.**
Each has exactly ONE evidence span — one dialogue turn containing the date.
Pattern facts AGGREGATE tokens, LOSING temporal specificity.
A pattern fact "caroline lgbtq support group pride parade conference" doesn't tell you WHEN each event happened.

Cat 2 needs the OPPOSITE of aggregation: find ONE SPECIFIC FACT with a date.
This is a retrieval precision problem, not a coverage problem.

### Cat 3 Failures (8 total)

| Root cause | Count | Example | Pattern helps? |
|------------|-------|---------|---------------|
| Inference from multiple facts | 5 | "Would Caroline be considered religious?" → need to infer from worldview facts | Marginally |
| Counterfactual reasoning | 2 | "Would Caroline still want counseling if no support?" → hypothetical | No |
| Personality inference | 1 | "What personality traits might Melanie say Caroline has?" → subjective | No |

Pattern facts might marginally help inference questions (more context for LLM to reason from).
Expected: +1-2 correct at most.

### Cat 4 Failures (13 total)

| Root cause | Count | Example | Pattern helps? |
|------------|-------|---------|---------------|
| Single-source detail | 13 | "What book did Caroline recommend?" → "Becoming Nicole" (one turn: D7:11) | **NO** |

All Cat 4 failures are detail questions with ONE evidence span.
Pattern facts don't help find one specific detail.
These might improve with DB fix (less noise → BM25 finds the specific fact).

---

## Pattern Facts Projected Impact

### Assumptions
- Pattern facts computed as token-union from clusters of 3+ related facts
- Added to fact pool alongside individual facts
- BM25 matches pattern facts for aggregation queries
- Only helps Cat 1 aggregation failures (21 out of 24 Cat 1 fails)

### Scenarios

| Scenario | Cat 1 fix rate | Cat 1 score | Overall | Delta |
|----------|---------------|-------------|---------|-------|
| Conservative (30%) | +6 | 14/32 = 44% | 57/118 = 48% | +5% |
| Realistic (50%) | +10 | 18/32 = 56% | 62/118 = 53% | +10% |
| Optimistic (75%) | +16 | 24/32 = 75% | 68/118 = 58% | +15% |

### Ceiling with patterns only
Even at 100% Cat 1 fix rate: 29/32 + 15 + 5 + 23 = 72/118 = **61%**.
Pattern facts CANNOT reach 70% alone because Cat 2 (22 fails) is untouched.

---

## What Fixes Cat 2?

Cat 2 = 22 "When did X?" failures. All single-source. Need to find ONE specific fact with a date.

### Hypothesis: DB fix alone might fix many Cat 2
With corrupted DB: BM25 searches 6,959 records. The one fact with the date
is buried under ~15 duplicates of nearby turns plus thousands of unrelated noise.
With clean DB: BM25 searches ~700 records. The date fact has a much higher
chance of appearing in top-60.

**Cat 2 might improve significantly from DB fix alone.** This is the strongest
argument for "measure baseline on clean DB first."

### If DB fix is insufficient for Cat 2:
- Temporal signal boost: add date-pattern detection as a BM25 signal
  (facts containing dates get bonus score for "When" queries)
- Session-date tagging: tag each fact with its session date during ingestion
  (already partially done in dated-learn mode)
- Neither of these requires pattern facts

---

## What Fixes Cat 4?

Cat 4 = 13 detail failures. All single-source. Same as Cat 2 but non-temporal.

### Hypothesis: DB fix might fix most Cat 4
Same reasoning: less noise → BM25 finds the specific fact.
Cat 4 is already at 64% — only 13 failures. Many might be noise-related.

### If DB fix is insufficient for Cat 4:
- These are mostly "What specifically did X?" questions
- Need precise BM25 matching or embedding similarity
- Existing dense retrieval injection might help (already implemented but untested on clean DB)

---

## Summary: Three Independent Interventions Needed

| Intervention | Fixes | Cat impact | Complexity |
|-------------|-------|-----------|------------|
| **DB isolation fix** | Noise reduction → helps Cat 2, Cat 4 | Cat 2: 40%→?%, Cat 4: 64%→?% | Done (1 line) |
| **Pattern facts (CLS)** | Coverage for aggregation → helps Cat 1 | Cat 1: 25%→50-75% | ~100 LOC |
| **Temporal boost** (if needed) | Date-aware ranking → helps Cat 2 | Cat 2: ?%→?% | ~30 LOC |

### Execution order (measure-first approach):

```
Step 1: Fix DB (DONE) → measure clean baseline
        → reveals true Cat 2 and Cat 4 scores without noise
Step 2: IF Cat 1 < 50% → implement pattern facts → measure
Step 3: IF Cat 2 < 55% → implement temporal boost → measure
Step 4: Each step is independent, can be ablated
```

---

## Key Finding

**Pattern facts are a Cat 1 intervention, not a universal solution.**

The three categories have three DIFFERENT failure modes:
- Cat 1: COVERAGE problem (need to aggregate) → pattern facts
- Cat 2: PRECISION problem (need to find one specific dated fact) → DB fix + maybe temporal boost
- Cat 4: PRECISION problem (need to find one specific detail) → DB fix

No single mechanism fixes everything. The architecture needs intent-aware
routing to DIFFERENT retrieval strategies per query type — which is exactly
what the architecture_synthesis.md concluded:

```
Intent → Objective → Mechanism
AGGREGATION → coverage → pattern facts
TEMPORAL → precision + date boost → standard BM25 + temporal signal
POINT → precision → standard BM25
```

This is the real architecture. Not one technique to rule them all.
