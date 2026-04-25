# LOCOMO Deep Analysis — Retrieval Gap Research Notes

## 1. Dataset Anatomy

**Source**: Maharana et al., "LoCoMo: Long Context Memory", ACL 2024

| Metric | Value |
|--------|-------|
| Conversations | 10 |
| Total QA pairs | 1,986 |
| Cat 1 (single-hop) | 282 |
| Cat 2 (multi-hop) | 321 |
| Cat 3 (temporal) | 96 |
| Cat 4 (world-knowledge) | 841 |
| Cat 5 (adversarial) | 446 |
| Sessions per conv | 38–64 (avg 56) |
| Turns per session | 10–47 (avg 21.6) |
| Turn length | 2–454 chars (avg 124) |
| Total turns per conv | 845–1,479 (avg 1,334) |

### Key Structural Insight

Каждая "conversation" — это **extended multi-session dialogue** между двумя спикерами
(e.g. Tim & Jolene, Caroline & Melanie), разворачивающийся на протяжении месяцев.
Session = один разговорный блок с датой. Вопросы задаются POST-HOC по всей истории.

## 2. Cat 1 (Single-Hop) — Не "Simple Fact Lookup"

### Question Pattern Distribution (N=282)

| Pattern | Count | % |
|---------|-------|---|
| what_general | 112 | 40% |
| what_does | 53 | 19% |
| other (which/when/why) | 46 | 16% |
| how_many | 25 | 9% |
| enumeration (books/activities/things) | 20 | 7% |
| who | 11 | 4% |
| how | 8 | 3% |
| where | 7 | 2% |

### Answer Complexity

| Type | Count | % |
|------|-------|---|
| Multi-item answers (commas, "and") | 187 | **66%** |
| Short answers (<30 chars) | 141 | 50% |
| Long answers (>80 chars) | 40 | 14% |

**CRITICAL FINDING**: **66% of Cat 1 answers require aggregation across multiple sessions**.

Examples:
- "What books has Tim read?" → "Harry Potter, Game of Thrones, the Name of the Wind, The Alchemist, The Hobbit"
  - 5 books mentioned across **8 different sessions**, **20 individual turns**
- "What activities has Melanie done with her family?" → "Pottery, painting, camping, museum, swimming, hiking"
  - 6 activities scattered across conversation
- "What causes has John done events for?" → "Toy drive, Community food drive, veterans, domestic violence"

**Cat 1 is NOT "simple single-fact retrieval" — it is AGGREGATION RETRIEVAL.**

This redefines the problem: retrieval must surface ALL mentions of a topic, not just the best match.

## 3. Coverage Analysis — Why top_k=60 Fails

### ai-knot (dated-learn mode)

```
Conv 0: 1,340 turns + ~400 extracted facts ≈ 1,740 total facts
top_k = 60 → coverage = 60/1740 = 3.4%

For "What books has Tim read?":
  - 20 book-related turns out of ~420 in Tim's conversation
  - BM25 must find ALL 20 in top-60 → impossible at 3.4% coverage
  - BM25 matches "book" and "read" but misses:
    "I just finished Harry Potter" (no "book"/"read")
    "Started the Hobbit last week" (no "book"/"read")
```

### memvid

```
Conv 0: 54 sessions stored as frames
top_k = 60, context from top 10 → 10 sessions × ~21 turns = 210 turns
Coverage = 210/1340 = 15.7%

Each session is a FULL conversation block (~2,500 chars).
If 8 sessions mention books, 8/54 = 15% → all 8 likely in top-60.
Answer model sees full dialogue context → can extract all books.
```

### Coverage Multiplier

| System | Storage units | Retrieved | Effective turn coverage |
|--------|-------------|-----------|----------------------|
| memvid | 54 sessions | top 10 | ~210 turns (16%) |
| ai-knot | ~1,740 facts | top 60 | 60 facts (3.4%) |

**memvid has 4.7× more context coverage** per conversation.

## 4. Memvid Architecture Deep Dive

Source: `/Users/alsoleg/Documents/github/memvid/memvid-main/src/memvid/ask.rs`

### Retrieval Pipeline

```
ask():
  1. Question classification (aggregation/recency/analytical/update)
  2. Adaptive top_k: analytical ×5, aggregation ×3, recency ×2
  3. Query sanitization + stopword removal
  4. Primary Tantivy search (with stemming)
  5. Multi-pass fallback:
     a. Disjunctive OR query (term1 OR term2 OR term3)
     b. Lexical fallback (capitalized words only)
     c. Expanded queries (singular/plural variants)
     d. Timeline fallback (recent frames)
  6. RRF fusion of ALL candidate lists
  7. Vector search candidates (HNSW)
  8. Semantic re-ranking (cosine similarity)
  9. Temporal promotion (for update/recency questions)
  10. Correction boost (user overrides)
  11. Aggregation diversification (unique sessions)
```

### Key Techniques

1. **Session-level storage**: Each frame is a full session (~2,500 chars), NOT individual turns
2. **Rules-based entity extraction**: ~30 regex patterns for employment, relationships, etc. (enrich/rules.rs:170-417)
3. **Third-person extraction**: "Alice works at Google" → entity=alice, slot=employer, value=google
4. **MemoryCards**: Structured entity/slot/value with versioning and cardinality
5. **Graph search**: QueryPlanner detects relational patterns → entity-first retrieval (graph_search.rs)
6. **Tantivy**: Full-text search engine with proper linguistic analysis (stemming, analyzers)
7. **HNSW**: Hierarchical Navigable Small World graph for fast ANN vector search

### What memvid does NOT do

- No LLM in retrieval path (everything deterministic)
- No pseudo-relevance feedback (PRF)
- No complex RRF multi-signal fusion (only lexical + semantic via RRF k=60)
- No decay/forgetting
- No trust mechanisms

## 5. Literature Review — State of the Art

### 5.1 Chunking and Retrieval Granularity

**RAPTOR** (Sarthi et al., 2024) — Recursive Abstractive Processing for Tree-Organized Retrieval.
Creates hierarchical summaries: chunk → cluster → summary → meta-summary.
Retrieval matches at ANY level of the tree. For aggregation queries, higher-level nodes
provide pre-aggregated context.

**Parent Document Retriever** (LangChain pattern) — Store small chunks for matching,
but return the parent document for context. Match at turn-level, return session-level.
Simple and effective.

**Sentence Window Retrieval** — Store individual sentences, but at retrieval time expand
to a window of N surrounding sentences. Provides local context.

### 5.2 Query Understanding

**RAG-Fusion** (Rackauckas, 2023) — Generate multiple query variants using LLM,
search with each, fuse results via RRF. Directly addresses vocabulary mismatch.
*Мы не можем использовать LLM в retrieval path (latency), но можем генерировать
варианты статически.*

**HyDE** (Gao et al., 2023) — Hypothetical Document Embeddings. Generate a hypothetical
answer using LLM, embed it, use for dense retrieval. For "What books has Tim read?",
LLM generates "Tim has read books including fiction novels" → embedding matches
book-related turns.
*Тоже требует LLM вызов, но можно кэшировать для benchmark.*

**Query Decomposition** (Bai et al., 2023) — For complex aggregation questions,
decompose into sub-queries. "What books has Tim read?" → ["Tim reading", "Tim book",
"Tim finished", "Tim started"]. Search each, merge results.
*Можно делать статически через синонимы.*

### 5.3 Multi-hop Retrieval

**IRCoT** (Trivedi et al., 2023) — Interleaving retrieval and chain-of-thought.
Retrieve → reason → generate new query → retrieve again.
For "Where does Alex's wife work?": retrieve "Alex's wife is Maria" → generate
"Maria workplace" → retrieve "Maria works at Google".
*Entity-hop в ai-knot — упрощённая версия.*

**ITER-RETGEN** (Shao et al., 2023) — Iterative retrieval-generation synergy.
Multiple rounds of retrieval, each informed by previous generation.
*Дорого по latency, но для benchmark допустимо.*

### 5.4 Lost in the Middle

**Liu et al., NeurIPS 2024** — "Lost in the Middle: How Language Models Use Long Contexts"
LLMs perform best when relevant information is at the BEGINNING or END of context.
Facts in the middle are often ignored.

*Implications*: With 60 facts in recall output, the answer model may ignore facts
at positions 20-40. Need to put most relevant facts first AND last.
*Или: лучше 15 высокорелевантных фактов чем 60 средних.*

### 5.5 Re-ranking

**Cross-encoder reranking** (Nogueira et al., 2020) — After initial BM25 retrieval
with top_k=200, use cross-encoder to re-rank to top_k=60.
Cross-encoders jointly encode query+document → much better semantic matching than
bi-encoder or BM25.
*Models: ms-marco-MiniLM-L-6-v2 (22M params, runs on CPU in <100ms per pair).*

## 6. Gap Analysis per Category

### Cat 1: 30% → 70% (target)

**Root cause**: Aggregation retrieval failure.
- 66% of questions need multi-session aggregation
- 3.4% fact coverage at top_k=60 vs memvid's 16%
- Vocabulary mismatch for paraphrased mentions
- No question-type awareness (aggregation vs point query)

**Theoretical maximum with perfect retrieval**: ~90% (limited by answer model quality
and judge leniency).

### Cat 2: 57% → 70% (target)

**Root cause**: Multi-hop chain incompleteness.
- Entity-hop works (improved 35%→57%) but needs higher entity coverage
- Only 1.1% facts have entity/attribute
- Temporal questions need date-aware retrieval

**Entity-hop ceiling**: With 1% entity coverage, hop coverage is ≈1%.
If rules extraction raises it to 30%, hop coverage → 30% → substantial improvement.

### Cat 3: 100% (above target)

No changes needed. Temporal questions answered by date-prefixed facts.

### Cat 4: 100% (above target)

No changes needed. World-knowledge handled by LLM parametric knowledge + facts.

## 7. Proposed Architecture Changes

### Level 1: Ingest Architecture (Fundamental)

**Session-level aggregation facts** — During ingest, create session-level summary
facts in addition to turn-level facts. Each summary contains key entities and topics
from the session. BM25 can match these for aggregation queries.

**Context expansion at recall** — When a fact is retrieved, include N surrounding
turns from the same session in the output. This gives the answer model dialogue context.

### Level 2: Retrieval Improvements

**Multi-pass with per-token OR** — If initial BM25 returns sparse results, run
individual-token queries and fuse via RRF. Matches memvid's multi-pass pattern.

**Query-aware top_k** — Detect aggregation questions, increase effective top_k.
Simple keyword heuristics: "all", "every", "list", "how many", "what are".

**Stopword removal before BM25** — Remove question words that add noise.

### Level 3: Entity/Extraction Improvements

**Rules-based entity extraction** — Regex patterns parallel to LLM extraction.
Based on memvid enrich/rules.rs patterns. Increases entity coverage from 1% → 30%+.

**Extract → Tag propagation** — When LLM extracts "Tim read Harry Potter", add
tags=["books", "reading", "harry_potter"]. BM25 field weight on tags = 2.0 (highest).

### Level 4: Pool Recall (Multi-Agent)

Port all improvements to `_pool_recall.py` which uses a different retrieval path
(HybridRetriever instead of _execute_recall).
