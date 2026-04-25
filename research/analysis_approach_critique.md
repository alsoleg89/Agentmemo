# Analysis: Why Most Approaches Won't Work — and What Might

## Date: April 2026

---

## 1. The Core Problem

ai-knot scores ~50% on LOCOMO. Target: 70-75% (memvid -10-15%).

**Root cause breakdown:**
- Cat 1 (single-hop): 23% — but 66% of Cat 1 is actually AGGREGATION (need facts from 8+ sessions)
- Cat 2 (multi-hop): 57% — entity chains incomplete
- Cat 3/4: ~100% on small sample

**The fundamental issue:**
- ai-knot stores ~1,740 fine-grained facts per conversation
- top_k=60 = 3.4% coverage
- memvid stores 54 sessions, retrieves 10 = 16% coverage (4.7x more)
- 66% of Cat 1 questions need aggregation → need ALL mentions of a topic, not just best match

---

## 2. Three Approaches Considered and Why Each Has Problems

### Approach A: "Retrieve Wider" (memvid's approach)
- Adaptive top_k, multi-pass retrieval, session diversity, OR-expansion
- **Problem**: 70-80% overlap with memvid's actual implementation
- **Verdict**: Rejected — too close to memvid, not unique

### Approach B: "Extract Smarter" (consolidation approach)
- Better LLM extraction → more entity/attribute coverage → fact clustering → summary facts
- **memvid reviewer critique** (simulated):
  1. "Consolidation is session storage with extra steps" — 3 processing steps to get what session storage gives for free
  2. "Extraction is lossy" — if LLM misses a mention during extraction, consolidation can't include it. memvid stores raw text = zero information loss
  3. "Show the ablation" — remove LLM consolidation, what score? If it drops to 30%, the improvement is LLM generation quality, not retrieval
  4. "Zero LLM in retrieval vs N calls" — more LLM = more latency, cost, failure modes
  5. "Hyperedge grouping = named entity co-occurrence clustering from 2003" — not novel
  6. "We tested entity extraction (rules.rs) as enrichment, not foundation" — extraction is fragile as foundation
- **Verdict**: Rejected — lossy, LLM-dependent, not novel, ablation-vulnerable

### Approach C: "Graph-Based Retrieval" (MAGMA/SYNAPSE/TEMPR)
- Build entity graph from structured facts, use graph traversal or spreading activation as 3rd retrieval channel
- **Problem**: Depends on entity coverage (~1%). Sparse graph = no results.
- **Problem**: Spreading activation already done by Hindsight
- **Problem**: Standard graph traversal (BFS) already done by Zep/Graphiti
- **Problem**: Papers show SOTA but as complete systems, not single techniques
- **Problem**: Primarily helps multi-hop (Cat 2), NOT aggregation (Cat 1 — the bigger gap)
- **Verdict**: Partially viable but doesn't solve the main bottleneck

---

## 3. What Would Survive Peer Review

An approach that:
1. Does NOT depend on extraction quality (not lossy)
2. Improves the RETRIEVAL ALGORITHM itself, not preprocessing
3. Demonstrates improvement WITHOUT LLM in retrieval path
4. Is genuinely novel (not rebrand of known techniques)
5. Solves AGGREGATION (Cat 1) as well as multi-hop (Cat 2)
6. Is unique among competitors (not done by Mem0, Letta, Zep, Cognee, Supermemory, Hindsight, memvid)

---

## 4. What ai-knot Already Has That's Unique

| Feature | Competitors with similar |
|---------|------------------------|
| 6-signal RRF (BM25F + slot-exact + trigram + importance + retention + recency) | Nobody has this exact combination |
| BM25F with 4-field weighting (content, tags, canonical, evidence) | Zep has BM25 but not multi-field |
| Slot-based CAS conflict resolution | Nobody |
| Ebbinghaus forgetting curves | Nobody (FadeMem is academic only) |
| Multi-agent trust scoring (Marsh 1994) | Nobody |
| Intent-aware RRF weight routing | Nobody does this with 6 signals |
| PRF (pseudo-relevance feedback) in memory retrieval | Nobody |

The 6-signal RRF IS a retrieval contribution. The problem is that these signals don't solve aggregation.

---

## 5. Directions That Might Actually Work

### Direction 1: "Rank Differently" — Intent-Adaptive Signal Fusion
ai-knot already has intent classification and 6-signal RRF. The idea: for DIFFERENT query types, not just change weights, but change WHICH signals are active and add query-type-specific signals.

For aggregation queries:
- Add 7th signal: "topic coverage" — how many DISTINCT topic mentions does this fact cover?
- Add 8th signal: "entity centrality" — how connected is this fact's entity in the co-occurrence graph?
- Suppress importance/retention signals (they bias toward few high-importance facts, bad for aggregation)
- Use DIFFERENT fusion strategy (not RRF but maybe a coverage-aware method)

For multi-hop queries:
- Add graph-distance signal: how far is this fact from the query entity in the entity graph?
- Boost entity-linked facts

This is genuinely novel: no one has intent-adaptive multi-signal retrieval with 8+ signals.

### Direction 2: "Coverage-Aware Retrieval" — Submodular Optimization
Instead of ranking by relevance (all systems do this), optimize for COVERAGE.

For "What books has Tim read?":
- Standard retrieval: finds the 60 MOST RELEVANT facts (may all be about the same book)
- Coverage-aware: finds 60 facts that MAXIMIZE TOPICAL COVERAGE (each fact adds new information)

This is Maximal Marginal Relevance (MMR, Carbonell & Goldstein 1998) but applied at the fact level with topic-diversity awareness. It's submodular optimization.

Key insight: aggregation queries need BREADTH not DEPTH. The retrieval objective function should change from "maximize relevance" to "maximize coverage while maintaining relevance."

### Direction 3: Hybrid — Adaptive signals + coverage optimization
Combine Direction 1 (intent-adaptive signals) and Direction 2 (coverage-aware retrieval):
- Detect query intent
- For aggregation: switch to coverage-maximizing retrieval with topic-diversity signals
- For point queries: use standard relevance-maximizing retrieval
- For multi-hop: add graph-distance signal

---

## 6. Competitor Overlap Check

| Technique | Mem0 | Letta | Zep | Cognee | Super | Hind | memvid |
|-----------|------|-------|-----|--------|-------|------|--------|
| Intent-adaptive multi-signal fusion | NO | NO | NO | NO | NO | NO | Partial* |
| Coverage-aware submodular retrieval | NO | NO | MMR option | NO | NO | NO | NO |
| 8+ orthogonal ranking signals | NO | NO | NO | NO | NO | NO | NO |
| Topic-diversity signal in retrieval | NO | NO | NO | NO | NO | NO | Partial** |

*memvid has query classification but applies it to top_k multiplier, not signal fusion
**memvid has diversify_hits_for_aggregation() but it's post-hoc filtering, not a retrieval signal

Overlap with memvid: ~10-15% (both classify queries, but mechanism is completely different)
Overlap with Zep: ~5% (Zep has MMR as option, but not intent-adaptive)
Overlap with others: ~0%

---

## 7. Why This Might Actually Work (for LOCOMO)

### For Cat 1 (Aggregation, 23% → target 70%):
- Coverage-aware retrieval ensures 60 facts SPAN different sessions/topics
- Instead of 60 facts about the same book, get 60 facts covering 5 different books
- Even if each individual fact is less relevant, the COVERAGE is much higher
- Answer model sees mentions of ALL books → can list them all

### For Cat 2 (Multi-hop, 57% → target 70%):
- Graph-distance signal helps find linked facts
- Entity-centrality signal boosts well-connected entities
- Intent-adaptive weights can boost entity signals for multi-hop queries

### Ablation-safe:
- Remove LLM → system still works (all signals are deterministic)
- Each signal is independently testable
- Coverage optimization is a mathematical formulation, not LLM-dependent

---

## 8. Open Questions

1. Can topic-diversity be computed efficiently (O(n) or O(n log n), not O(n²))?
2. How to define "topic" for coverage without LLM? (Options: entity-based, tag-based, embedding clusters)
3. Is MMR (greedy submodular) sufficient or do we need something more sophisticated?
4. How to set the relevance vs diversity tradeoff parameter?
5. Does this actually improve scores in practice? (Need to benchmark)

---

## 9. Conclusion

The most defensible approach is **NOT about extracting or storing differently**, but about **retrieving with a different objective function** depending on query type:
- Point queries → maximize RELEVANCE (existing approach, works fine)
- Aggregation queries → maximize COVERAGE (new approach, unique)
- Multi-hop queries → maximize REACHABILITY (graph signal, unique)

This is:
- A retrieval algorithm contribution (survives "show ablation" critique)
- Not extraction-dependent (survives "extraction is lossy" critique)
- Not session storage with extra steps (fundamentally different objective)
- Unique among all competitors
- Research-backed (MMR, submodular optimization, intent-adaptive retrieval all have literature)
- Compatible with ai-knot's existing 6-signal RRF architecture
