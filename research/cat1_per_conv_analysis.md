# Cat1 Per-Conversation Failure Analysis

**Date:** 2026-04-11
**Baseline:** v095-learn-off-all (dated mode, no learn, top-k 60, gpt-4o-mini)
**MMR run:** v096-dated-all (same but with MMR diversity reranking, lambda=0.5)

---

## Key Finding: Aggregation vs Point Questions

Cat1 failures are almost entirely **aggregation questions** ("list ALL X"). Point questions ("What is X?") have ~50% accuracy. Aggregation questions have ~25%.

| Conv | Cat1% | Agg correct | Point correct | Wrong agg | Hard agg (>=3 items) |
|------|-------|-------------|---------------|-----------|---------------------|
| 00 | 22% | 1/20 (5%) | 6/12 (50%) | 19 | 7 |
| 01 | 45% | 3/7 (43%) | 2/4 (50%) | 4 | 3 |
| 02 | 45% | 10/24 (42%) | 4/7 (57%) | 14 | 6 |
| 03 | 24% | 4/25 (16%) | 5/12 (42%) | 21 | 14 |
| 04 | 29% | 6/22 (27%) | 3/9 (33%) | 16 | 11 |
| 05 | 60% | 4/13 (31%) | 14/17 (82%) | 9 | 8 |
| 06 | 45% | 8/17 (47%) | 1/3 (33%) | 9 | 4 |
| 07 | 29% | 3/15 (20%) | 3/6 (50%) | 12 | 10 |
| 08 | 62% | 1/3 (33%) | 4/5 (80%) | 2 | 1 |

Conv 05 and 08 score well because they have more point questions.
Conv 03, 04, 07 are worst — 14-21 wrong aggregation with >=3 items.

---

## MMR Impact: Churn, Not Improvement

MMR run (conv 00-03 available):

| Conv | Base | MMR | Delta | Notes |
|------|------|-----|-------|-------|
| 00 | 7/32 | 10/32 | +3 | User reported, checkpoint shows +1 |
| 01 | 5/11 | 5/11 | 0 | |
| 02 | 14/31 | 14/30 | 0 | 4 gained, 4 lost — pure churn |
| 03 | 9/37 | ~8/29 | -1 | 1 gained, 1 lost |

Conv 02 churn detail:
- CORRECT->WRONG: qa18 (yoga partner), qa23 (desserts), qa25 (European countries), qa26 (faith)
- WRONG->CORRECT: qa35 (vacation states), qa42 (flood area), qa49 (food item), qa57 (causes for events)

MMR reshuffles which facts enter top-k, but doesn't address the core problem: model sees facts but doesn't enumerate all items.

---

## Hard Aggregation Questions — Items Required

| Conv | Wrong agg | 2 items | 3 items | 4 items | 5+ items |
|------|-----------|---------|---------|---------|----------|
| 00 | 19 | 12 | 4 | 2 | 1 |
| 01 | 4 | 1 | 1 | 0 | 2 |
| 02 | 14 | 8 | 3 | 2 | 1 |
| 03 | 21 | 7 | 3 | 5 | 6 |
| 04 | 16 | 5 | 4 | 2 | 5 |
| 05 | 9 | 1 | 2 | 4 | 2 |
| 06 | 9 | 5 | 1 | 0 | 3 |
| 07 | 12 | 2 | 2 | 3 | 5 |
| 08 | 2 | 1 | 0 | 0 | 1 |

Conv 03 and 04 have the most 5+ item questions — hardest to answer correctly.

---

## Contingency Strategy Assessment

### 1. Ingest-time dedup
- Compresses index ~2x, improves IDF discrimination
- **Does NOT address M-type** (83% of errors)
- Estimated: +1-2 correct per conv, uniform
- **Verdict: marginal**

### 2. Adaptive top_k (truncate at score drop)
- Less noise -> better signal density
- BUT: for aggregation, relevant facts at position 41 would be CUT
- "What activities does Melanie do?" — swimming at pos 41 -> lost
- **Verdict: may HURT aggregation questions**

### 3. Entity-grouped recall format
- Groups facts by entity before presenting to model
- Directly addresses the scatter problem: facts at pos 7, 23, 41 -> grouped together
- Model sees cluster instead of scattered individual facts
- **Verdict: only strategy that targets the actual bottleneck**
- Estimated: +30-40 correct out of ~120 wrong-agg, ~+12-15pp Cat1

---

## Error Type Distribution (extrapolated from locomo_fails_report.md)

Per-conv estimated:
| Conv | Total wrong | Est M-type (83%) | Est R-type (17%) |
|------|-------------|-------------------|-------------------|
| 00 | 25 | 21 | 4 |
| 01 | 6 | 5 | 1 |
| 02 | 17 | 14 | 3 |
| 03 | 28 | 23 | 5 |
| 04 | 22 | 18 | 4 |
| 05 | 12 | 10 | 2 |
| 06 | 11 | 9 | 2 |
| 07 | 15 | 12 | 3 |
| 08 | 3 | 2 | 1 |
