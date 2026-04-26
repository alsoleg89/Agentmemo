# PROC Baseline Bucket Audit — 2026-04-27

Run: `diag-baseline-proc-c0` (conv0, 199 Qs) + `diag-baseline-proc-c1` (conv1, 105 Qs)  
Backend: `ai-knot` v0.9.6, dated ingest, top_k=60  
Models: gpt-4.1-nano (judge + answer), text-embedding-3-small  
Date: 2026-04-26

---

## Accuracy

| Run | Correct | Total | Accuracy |
|-----|---------|-------|----------|
| c0 (conv0) | 135 | 199 | 67.8% |
| c1 (conv1) | 65 | 105 | 61.9% |
| **Combined** | **200** | **304** | **65.8%** |

Per-category (combined):

| Cat | Correct | Total | Accuracy |
|-----|---------|-------|----------|
| cat1 single-hop | 17 | 43 | 39.5% |
| cat2 multi-hop | 37 | 63 | 58.7% |
| cat3 temporal | 10 | 13 | 76.9% |
| cat4 open-ended | 90 | 114 | 78.9% |
| cat5 adversarial | 46 | 71 | 64.8% |

---

## PROC Bucket Counts (combined c0 + c1)

| Bucket | Count | % of WRONG |
|--------|-------|------------|
| LLM-fail | **60** | 57.7% |
| partial-recall | **30** | 28.8% |
| low-recall | **6** | 5.8% |
| hard-miss | **8** | 7.7% |
| **Total WRONG** | **104** | 100% |

---

## Pool / Pack Recall

| Metric | Value | N |
|--------|-------|---|
| PoolGoldRecall@K (top_k=60) | **98.7%** | 301 |
| PackGoldRecall@Budget | **84.0%** | 301 |
| ReaderFailDespiteGold (LLM-fail) | 84 | — |
| DistractorDensity (avg) | 96.7% | — |

---

## Per-Category Breakdown

### cat1 (single-hop) — 26 wrong total

| Bucket | c0 | c1 | Total |
|--------|----|----|-------|
| LLM-fail | 5 | 0 | 5 |
| partial-recall | 9 | 5 | 14 |
| low-recall | 4 | 1 | 5 |
| hard-miss | 2 | 0 | 2 |

PoolGoldRecall avg: c0=96.2%, c1=97.9%  
PackGoldRecall avg: c0=54.7%, c1=49.0%  
→ **cat1 bottleneck: Pack quality** (gold in pool but lost in pack)

### cat2 (multi-hop) — 26 wrong total

| Bucket | c0 | c1 | Total |
|--------|----|----|-------|
| LLM-fail | 15 | 9 | 24 |
| hard-miss | 1 | 1 | 2 |

PoolGoldRecall avg: 100%  
PackGoldRecall avg: c0=93.8%, c1=90.0%  
→ **cat2 bottleneck: LLM reasoning** (gold in pack, LLM fails)

### cat4 (open-ended) — 24 wrong total

| Bucket | c0 | c1 | Total |
|--------|----|----|-------|
| LLM-fail | 6 | 7 | 13 |
| partial-recall | 4 | 5 | 9 |
| hard-miss | 0 | 2 | 2 |

### cat5 (adversarial) — 25 wrong total

| Bucket | c0 | c1 | Total |
|--------|----|----|-------|
| LLM-fail | 10 | 8 | 18 |
| partial-recall | 4 | 2 | 6 |
| hard-miss | 1 | 0 | 1 |

---

## Key Findings

1. **PoolGoldRecall@K=98.7%** — retrieval is nearly perfect (gold is in pool almost always)
2. **PackGoldRecall@Budget=84.0%** — 15% of gold facts that reach the pool are dropped during packing
3. **57.7% LLM-fail** — majority of wrong answers have gold in the pack; LLM fails to extract
4. **cat1 specific**: PackGoldRecall drops to ~52% for single-hop — pack quality is cat1's main lever
5. **hard-miss=8** — only 8 questions where gold is completely unretrievable

## Implications for Phase A (Lexical Bridge)

The LLM-fail bucket (60/104) is the dominant failure mode. Lexical bridge (Phase A)
addresses retrieval coverage — it may help the 36 partial+low+hard-miss cases but
NOT the LLM-fail majority. Phase B (Evidence Pack V2) is the higher-leverage intervention.

Phase A is still worth running (cat1 PackGoldRecall ~52% suggests pack reordering matters),
but target uplift should be realistic: +2-4pp aggregate, not +10pp.
