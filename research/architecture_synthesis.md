# Architecture Synthesis — What Survives Criticism

## Date: 2026-04-11
## Perspective: Stripped of marketing, biology metaphors, and premature optimization

---

## What the Critic Destroyed

1. **Strand as a data structure** — premature. 2-bit bitmaps, L1 cache claims, binary format spec — all irrelevant until the CONCEPT is validated. Python won't benefit from cache alignment. Designing storage before proving value is backwards.

2. **Co-occurrence as THE mechanism** — flawed for dialogue. In 2-person conversation, co-occurrence is symmetric between speakers. Can't tell "does X" from "talks about X". Noise dominates signal when raw turns outnumber extracted facts 2:1.

3. **Biology as engineering argument** — post-hoc rationalization. DNA metaphor didn't predict 2-bit encoding. Ant metaphor didn't predict temporal decay design. Useful for vision, not for code.

4. **Rescripting** — vaporware for v1. No user, no API, no use case. Natural rescripting through new facts + Ebbinghaus decay is real but doesn't need Strand.

5. **"Nobody does this"** — embeddings ARE compressed co-occurrence. Every system with embeddings already has this signal. The question is whether CORPUS-SPECIFIC co-occurrence adds value ON TOP of general embeddings.

---

## What the Critic Did NOT Destroy

### 1. The retrieval objective problem is real

BM25 top_k=60 on 700+ facts = 3.4% coverage. For aggregation queries (66% of Cat 1), this is mathematically insufficient. This is not opinion — it's arithmetic.

**No amount of ranking improvement fixes insufficient coverage.** If the answer requires facts from 8 sessions and you only see 60 facts clustered around 2 sessions, even perfect ranking within those 60 won't help.

### 2. Intent-adaptive retrieval is genuinely novel

ai-knot already has:
- Intent classifier (5 intents)
- 6-signal RRF
- Intent-dependent weight routing

No competitor has this combination. But right now intent only changes WEIGHTS. It doesn't change the OBJECTIVE:
- AGGREGATION should maximize COVERAGE (breadth)
- POINT should maximize RELEVANCE (precision)
- TEMPORAL should maximize RECENCY-WEIGHTED RELEVANCE

This is the real contribution. Not a data structure — a **retrieval paradigm**.

### 3. The "information in relationships" insight is correct (but mechanism is wrong)

The critic is right that Strand (token co-occurrence matrix) is a flawed mechanism:
- Symmetric in dialogue
- Redundant with BM25 inverted index
- Reinvents embeddings poorly

But the underlying insight IS valid: aggregation answers live in PATTERNS across facts, not in individual facts. The question is what MECHANISM captures these patterns without the flaws.

### 4. Corpus-specific signal adds value over general embeddings (hypothesis)

Embeddings know "swimming ≈ activities" (general language).
But embeddings DON'T know "in this agent's memory, melanie and swimming co-occur".

This is a testable hypothesis. If corpus-specific expansion (from any mechanism) improves over embedding-only retrieval, the concept is validated. The mechanism can be simple (overfetch + MMR) or complex (Strand). Test simple first.

---

## Reformulated Architecture

Strip everything to its essential components:

### Layer 0: Storage (existing, bug-fixed)
- Individual facts in SQLite
- Per-agent isolation (DB bug fixed)
- No changes needed

### Layer 1: Intent Classification (existing, extend)
- Detect query type: AGGREGATION, ENTITY_LOOKUP, TEMPORAL, INCIDENT, GENERAL
- AGGREGATION already partially implemented
- This layer DECIDES how retrieval will work

### Layer 2: Retrieval Objective Switch (THE contribution)

```
if intent == AGGREGATION:
    retrieve_for_coverage(query, facts, top_k)
elif intent == TEMPORAL:
    retrieve_for_recency(query, facts, top_k)
else:
    retrieve_for_relevance(query, facts, top_k)  # existing
```

**This is the architecture.** Everything else is mechanism.

### Layer 3: Coverage Retrieval Mechanism (implement simplest first)

Option A: **Overfetch + MMR** (simplest, no new data structures)
```
candidates = bm25.search(query, facts, top_k=top_k * 5)
result = mmr_rerank(candidates, top_k, lambda=0.7)
```

Option B: **Corpus-aware query expansion** (Strand-lite, no binary format)
```
cooccurrence = build_cooccurrence_dict(facts)  # plain Python dict
expanded_terms = cooccurrence.get_associated(query_tokens, top_k=10)
candidates = bm25.search(expanded_query, facts, top_k)
```

Option C: **Both** (expansion feeds overfetch, MMR diversifies)
```
expanded = expand_from_corpus(query, facts)
candidates = bm25.search(expanded, facts, top_k * 3)
result = mmr_rerank(candidates, top_k, lambda=0.7)
```

**Test A first. If insufficient, test B. If still insufficient, test C.**

### Layer 4: Forgetting (existing)
- Ebbinghaus decay
- Temporal validity
- Spacing effect

### Layer 5 (future): Schema evolution
- When enough new facts shift patterns, old associations naturally fade
- This IS "natural rescripting" — no explicit API needed
- Maybe someday: explicit `kb.rescript()` for therapeutic applications

---

## What's Unique (After Stripping Marketing)

| What we claim | Is it real? | Who else has it? |
|---|---|---|
| Intent-adaptive retrieval objective | Yes — architecture switches between coverage/relevance/recency | Nobody |
| 6-signal RRF with intent-dependent weights | Yes — existing code | Nobody |
| Coverage-optimized aggregation retrieval | Needs validation — MMR/expansion | Zep has MMR option but not intent-triggered |
| Ebbinghaus forgetting + spacing effect | Yes — existing code | Nobody in production |
| Slot-based CAS conflict resolution | Yes — existing code | Nobody |
| Multi-agent trust scoring | Yes — existing code | Nobody |

The COMBINATION is unique. No single piece is earth-shattering, but the integrated system — intent → objective → mechanism + forgetting + trust — is something no competitor has.

**The paper title should be about INTENT-ADAPTIVE RETRIEVAL, not about Strand or co-occurrence.** Strand is an optional mechanism. Intent-adaptive objective switching is the architecture.

---

## Honest Assessment of Expected Impact

### With DB fix only (existing code, clean data):
- Entity-scoping works on ~16% of facts (f.entity field)
- top_k=60 on ~700 facts (not 7000) = 8.6% coverage
- **Expected: 43% → 50-55%**

### With DB fix + overfetch + MMR for AGGREGATION:
- top_k=300 overfetch → MMR to 60 diverse facts
- Coverage for aggregation queries: 8.6% → ~25% effective (diversity ensures spread)
- **Expected: 50-55% → 58-65%**

### With DB fix + overfetch + MMR + corpus expansion:
- Expansion adds topic terms to query → BM25 boosts diverse facts higher
- Combined with MMR → maximum coverage
- **Expected: 58-65% → 62-68%** (incremental over MMR alone)

### Ceiling without changing storage model:
- ~70% (limited by extraction quality, judge model, question ambiguity)
- To reach 80%+: need session-level storage or cross-encoder reranking

---

## Concrete Next Steps

```
1. DONE:   Fix DB isolation (one-line fix, committed)
2. NEXT:   Run LOCOMO on clean DB → measure baseline
3. IF <55%: Implement overfetch + MMR in _execute_recall()
4. MEASURE: Run LOCOMO with MMR → compare
5. IF <60%: Add corpus expansion (simple dict, not Strand binary)
6. MEASURE: Run LOCOMO with expansion + MMR → compare
7. IF expansion helps: Consider optimizing storage (Strand) for production
8. IF expansion doesn't help: Drop it, focus on other levers
```

Each step is ~30 minutes of code + ~40 minutes of benchmark. Total: 2-3 hours
to go from theory to measured results.

---

## What Strand Becomes

Strand as a CONCEPT (corpus-specific associations) may survive validation.
Strand as a DATA STRUCTURE (2-bit bitmap, binary format) is premature.

If corpus expansion proves valuable:
- v1: Python dict, rebuilt per recall (acceptable for 700 facts, <1ms)
- v2: Cached dict, invalidated on add/learn
- v3: Optimized binary (only if profiling shows dict is bottleneck)
- v4: Strand format (only if shipping as a file makes product sense)

The cognitive model (encoding → forgetting → association → rescripting) is the
VISION. The implementation path is: measure → simplest mechanism → iterate.

---

## One-Sentence Summary

**ai-knot's real contribution is intent-adaptive retrieval that switches between
coverage and relevance objectives; the mechanism (MMR, expansion, Strand) is
secondary and must be validated empirically before architectural commitment.**
