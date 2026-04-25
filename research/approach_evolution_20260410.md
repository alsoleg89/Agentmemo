# Approach Evolution — From Entity Scoping to Pattern Memory

## Date: 2026-04-10

## Timeline of Thinking

### Starting point: Entity-Scoped Retrieval (previous session)
- Built entity-mention inverted index, scoped BM25 to entity subsets
- Results: 43.2% overall (Cat 1: 25%, Cat 2: 40.5%, Cat 3: 38.5%, Cat 4: 63.9%)
- Appeared to not work — but actually broken by DB corruption (16x duplication)

### Diagnostic: DB corruption discovered
- All benchmark runs share one SQLite DB
- 6,959 records instead of ~700
- Entity-scoping was working on garbage data
- Entity coverage appeared 1.6% but with clean DB would be ~16%

### Iteration 1: "Fix DB + session-level extraction + drop raw turns"
**Rejected**: analysis_approach_critique.md says extraction is lossy. MemMachine (91.69%) proves raw storage + good retrieval wins. "Drop raw turns" = Approach B from critique = already rejected.

### Iteration 2: "Fix DB + speaker-name entity detection"
**Rejected by user**: detecting "Caroline:" patterns is LOCOMO-format-specific. Not product-grade.

### Iteration 3: "Fix DB + frequency-based proper noun detection"
**Rejected by user**: capitalization = English-specific. Entity scoping in general = person-centric assumption. Not general enough.

### Iteration 4: "Fix DB + overfetch + MMR"
Proposed: for AGGREGATION intent, BM25 top_k×5 then MMR diversity reranking.
**Not rejected but insufficient**: user pushed for deeper thinking. MMR is a known technique. What's genuinely new?

### Iteration 5: Biological analogy → "information is relationships, not data"
User's prompt: "DNA stores information, ants too, 3nm processors — what unites them?"

Key insight: **information is not in individual data points but in RELATIONSHIPS between them.**
- DNA: gene regulatory networks, not individual genes
- Ants: pheromone gradients, not individual pheromone dots
- Processors: access patterns, not individual addresses

### Iteration 6: Token co-occurrence as corpus-aware query expansion
Co-occurrence graph captures ALL relationships between tokens in the corpus.
Query expansion from this graph finds associated concepts that BM25 alone would miss.
E.g., "melanie" expands to {pottery, camping, swimming, ...} because they co-occur in facts.

### Iteration 7: Pattern Memory — persistent binary structure (CURRENT)
User's insight: "we'll store mini-aggregations? then we need super-efficient packing and very simple fast search"

This transforms co-occurrence from an ephemeral computation into a **persistent data structure**:
- 110 KB binary format (fits in L2 cache)
- Bitvector candidate selection (CPU-native operations)
- Incremental updates on add/learn/forget
- This IS the semantic memory layer — not a metadata tag, a real structure

## Key Rejections and Why

| Approach | Rejected because |
|----------|-----------------|
| Better extraction | Lossy, LLM-dependent, ablation-vulnerable |
| Drop raw turns | MemMachine proves raw + good retrieval wins |
| Speaker-name detection | LOCOMO-format-specific |
| Proper noun frequency | English-specific, entity-centric assumption |
| Entity scoping (general) | Person-centric, doesn't work for all query types |
| Standard MMR | Known technique, not novel enough |

## Why Pattern Memory Survives These Critiques

| Critique | Response |
|----------|----------|
| "Extraction is lossy" | Pattern memory works on ALL facts (raw + extracted) |
| "Format-specific" | Token co-occurrence is format-agnostic |
| "Language-specific" | Works for any tokenizable language |
| "Entity-centric" | No entity assumption — works on any co-occurring tokens |
| "Not novel" | No competitor has persistent binary co-occurrence + intent-adaptive expansion |
| "Show ablation" | ON/OFF is trivial — expansion ON vs OFF |
| "LLM in retrieval" | Zero LLM — purely statistical |
| "Scales?" | 110KB at 700 facts, ~6MB at 10K facts (still L3 cache) |

## What Remains To Validate

1. Does pattern memory actually improve LOCOMO scores? (Need benchmark)
2. Does the expansion find the RIGHT terms? (Need examples)
3. Does overfetch + expansion + BM25 outperform standard BM25? (Need A/B)
4. Is incremental update fast enough for real-time use? (Need profiling)
5. Does it work on non-LOCOMO data? (Need diverse benchmarks)
