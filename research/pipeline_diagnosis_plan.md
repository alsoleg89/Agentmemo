# Pipeline Diagnosis: Where Are Points Actually Lost?

## Date: 2026-04-11

---

## The Unasked Question

We spent hours optimizing RETRIEVAL (entity-scoping, Strand, CLS, pattern facts,
MMR). But we never checked whether retrieval is actually the bottleneck.

The benchmark pipeline has 4 stages:

```
Ingest → Recall → Answer → Judge
  ↓        ↓        ↓        ↓
 facts   top-60   LLM gen  LLM eval
         BM25    qwen2.5   qwen2.5
```

We've been optimizing stage 2 (Recall). But the failure could be in ANY stage.

---

## Four Hypotheses for 43.2% Score

### H1: Recall doesn't find the right facts (retrieval failure)
- BM25 can't find the fact containing the answer in top-60
- This is what we've been assuming
- Pattern facts, entity-scoping, MMR all target this

### H2: Recall finds the facts, but Answer model can't synthesize (generation failure)
- The right fact IS in top-60, but qwen2.5:14b can't extract the answer
- 60 facts = ~3000 tokens of context → "lost in the middle" effect
- Or the fact is there but phrased differently from the question
- No amount of retrieval improvement fixes this

### H3: Answer is correct but Judge rejects it (evaluation failure)
- qwen2.5:14b as judge may be too strict, or hallucinate incorrect verdicts
- "Transgender woman" vs "Caroline identifies as transgender" → judge says WRONG?
- This would inflate failure rate artificially

### H4: DB corruption is the main issue (data quality failure)
- 7000 records instead of 700 → 10x noise
- BM25 searching through 15 copies of each turn
- Entity-scoping working on 1.6% instead of 16%
- Fix DB alone might give +15-20% improvement
- WE HAVEN'T MEASURED THIS

---

## What We Need to Measure (Before Building Anything)

### Test 1: Clean DB baseline
- Fix DB (DONE — one-line fix)
- Delete corrupted `aiknotbench/.ai_knot/ai_knot.db`
- Run LOCOMO with existing code on clean DB
- Compare: 43.2% → ???

### Test 2: Recall quality audit (sample 10 failing questions)
For each failing question:
- What did recall() actually return? (log the 60 facts)
- Is the gold answer's evidence IN the returned facts?
- If YES → problem is Answer model (H2) or Judge (H3)
- If NO → problem is Recall (H1)

This tells us: what % of failures are retrieval failures vs generation failures?

### Test 3: Judge reliability
- Take 20 questions where we know the answer is correct
- Check if judge says CORRECT
- Take 20 questions where answer is clearly wrong
- Check if judge says WRONG
- Measure judge accuracy → if <90%, judge is the bottleneck

### Test 4: Answer model quality
- For questions where recall returns the right facts:
- Does the answer model extract the right answer?
- Try with different prompt templates
- Try with different top_k (5, 10, 30, 60) → does less context help?

---

## Why This Matters

If 50% of failures are H2 (answer model) and 30% are H1 (retrieval):
- Improving retrieval fixes 30% of failures → ~13 questions → 43% → ~54%
- Improving answer model fixes 50% → ~22 questions → 43% → ~62%
- We've been optimizing the WRONG thing

If 80% of failures are H1 (retrieval):
- Retrieval improvements are the right focus
- But DB fix alone might fix half of them

If 40% of failures are H4 (DB corruption):
- DB fix alone: 43% → ~55%
- Then retrieval improvements on clean data: 55% → 65%
- We'd be in good shape without any new architecture

**We don't know the distribution. We need to measure.**

---

## Execution Plan

```
Step 1: Clean DB baseline (30 min)
  - Delete corrupted DB
  - Run benchmark: npx tsx src/index.ts run -r clean-baseline \
      --ingest-mode dated-learn --top-k 60 --judge ollama:qwen2.5:14b \
      --model ollama:qwen2.5:14b --limit 1
  - Record: overall %, per-category %
  - Compare with corrupted baseline (43.2%)

Step 2: Recall audit (1 hour)
  - Add debug logging to recall: print returned facts for each question
  - Run on 20 failing questions (sample across Cat 1-4)
  - For each: is gold evidence in returned facts? YES/NO
  - Calculate: % retrieval failures vs % generation/judge failures

Step 3: Based on results, choose intervention:
  If retrieval is bottleneck → pattern facts / session storage / MMR
  If generation is bottleneck → better prompt template / fewer facts / reranking
  If judge is bottleneck → switch judge model or calibrate
  If DB fix is sufficient → ship it, move to multi-agent improvements
```

---

## Key Insight

We've been designing architecture (Strand, CLS, pattern facts) to solve a
problem we haven't diagnosed. This is like prescribing medicine before
running blood tests.

The correct order:
1. **Diagnose** — where are points lost? (measure)
2. **Identify** — which stage is the bottleneck? (analyze)
3. **Intervene** — fix the bottleneck (implement)
4. **Verify** — did it work? (measure again)

We jumped from step 0 to step 3. Time to go back to step 1.
