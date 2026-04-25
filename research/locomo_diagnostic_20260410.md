# LOCOMO Diagnostic — 2026-04-10

## DB Corruption Finding

**Critical bug**: Per-run DB isolation is broken. `dbPath` passed to `AiknotAdapter` doesn't reach the MCP subprocess. All benchmark runs write to a shared `aiknotbench/.ai_knot/ai_knot.db`.

Evidence:
- `aiknotbench/data/runs/*/knot.db` — NONE exist (all NOT FOUND)
- All data in `aiknotbench/.ai_knot/ai_knot.db` — 9,323 total records
- conv-0 has 6,959 facts from ~10 overlapping ingestion passes
- 82 distinct ingestion minutes across 2 days (2026-04-09 to 2026-04-10)
- Expected per-run: ~700 facts (434 raw + 270 extracted)
- Actual: 6,959 = ~10x expected

### Fact Quality in Corrupted DB

| Metric | Value |
|--------|-------|
| Total records (conv-0) | 6,959 |
| Distinct content | 1,508 |
| Raw turns (speaker prefix) | 1,238 (82% of distinct) |
| Extracted facts | 270 (18% of distinct) |
| Duplication ratio | 4.6x average |
| With entity field | 114 (1.6% of total, 42% of extracted) |
| With slot_key | 89 (1.3%) |

### Impact on Entity-Scoped Retrieval

The entity-scoped retrieval implemented in the previous session operates on corrupted data:
- Entity dictionary built from 114 facts with entity field (1.6% of 6,959)
- Entity-mention index scans 6,959 records (94.7% are duplicated raw turns)
- Scoped retrieval narrows from 6,959 to ~2,000 (still huge, still noisy)
- All entity-scoping improvements measured on this data are meaningless

With clean DB (700 facts):
- Entity dictionary from ~114 extracted facts = 16% coverage
- Scoping would narrow from 700 to ~200 = meaningful
- top_k=60 out of 200 = 30% coverage (vs 3.4% now)

## Benchmark Results (conv-0, 118 questions)

| Cat | Pass | Total | Rate |
|-----|------|-------|------|
| 1 (single-hop/aggregation) | 8 | 32 | 25.0% |
| 2 (multi-hop/temporal) | 15 | 37 | 40.5% |
| 3 (reasoning/inference) | 5 | 13 | 38.5% |
| 4 (world-knowledge) | 23 | 36 | 63.9% |
| **Overall** | **51** | **118** | **43.2%** |

### Extraction Gap Analysis

For failing Cat 1 questions, checked if gold answer keywords exist in extracted facts vs raw turns:

| Question | Gold keywords | In extracted? | In raw turns? |
|----------|--------------|---------------|---------------|
| Instruments Melanie plays | clarinet, violin | Both YES | YES |
| What Melanie painted | horse, sunset, sunrise | All YES | YES |
| Books Melanie read | "Nothing is Impossible" | NO (nowhere) | NO |
| Musical artists seen | Summer Sounds | NO | YES (raw only) |
| Activities Melanie does | swimming | NO | YES (raw only) |
| Pottery types | cup | NO | YES (raw only) |
| Symbols for Caroline | transgender symbol | NO | NO |

Three failure types:
1. Fact EXISTS in extracted — retrieval doesn't find it (retrieval gap)
2. Fact EXISTS only in raw turns — extraction missed it (extraction gap)
3. Fact DOESN'T EXIST anywhere — gold answer requires inference (impossible without world knowledge)

## Approaches Considered and Rejected

### 1. "Drop raw turns, improve extraction" (Approach B from critique)
- Rejected by analysis_approach_critique.md as lossy and ablation-vulnerable
- MemMachine (91.69% on LOCOMO) proves: raw storage + good retrieval beats extraction
- Conclusion: raw turns should stay, extraction isn't the bottleneck

### 2. Speaker-name entity detection
- Detecting "Caroline:" / "Melanie:" patterns in content
- Rejected as LOCOMO-format-specific (not product-grade)
- Real conversations don't have speaker prefixes in fact content

### 3. Frequency-based proper noun detection
- Capitalized words appearing in 3+ facts = entities
- Rejected as English-specific and entity-centric assumption
- Doesn't work for Russian, Chinese, or non-person-centric queries

### 4. Entity scoping in general
- The whole paradigm of "narrow to entity → search within" is optimized for person-centric questions
- Real product queries: "What config changes last week?" — no entity
- Entity scoping is a narrow optimization, not a general solution

## Direction Chosen: Pattern Memory

See `pattern_memory_architecture.md` for the full design.

Core idea: store token co-occurrence as a persistent binary structure (~110 KB).
At query time: expand query from co-occurrence graph, then BM25 on candidates.
This is corpus-aware, language-agnostic, format-agnostic, and LLM-free.
