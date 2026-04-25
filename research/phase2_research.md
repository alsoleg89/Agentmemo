# Phase 2 Research Results

**Date:** 2026-04-11

---

## 1. Off-by-1 Date Bug Investigation

**Symptoms:** Cat2 dates shifted +1 day (Gold: 7 May → Got: 8 May).

**Root cause:** НЕ timezone/UTC. Это data duplication в `dated-learn` mode.

`aiknotbench/src/aiknot.ts` lines 45-49 в dated-learn mode вызывает:
1. `ingestDated(sessions)` → stores raw turns с **session date** prefix: `[8 May, 2023] Caroline: I went to a LGBTQ support group yesterday`
2. `ingestLearn(datedTurns)` → LLM extracts: `Caroline attended LGBTQ support group on 7 May 2023`

Session date ≠ event date. Events referenced as "yesterday" happened -1 day.

При recall оба типа фактов попадают в результаты. Raw turns (много) prominently показывают `[8 May, 2023]`. Answer LLM читает session date вместо correctly resolved event date из extracted facts.

**Это design issue benchmark adapter, не core ai-knot bug.**

Возможные решения:
- learn-only mode (без ingestDated)
- Приоритизация extracted facts над raw turns при overlap
- Dedup между raw и extracted (сложно — разный формат)

---

## 2. Raw Facts Retrieval Analysis

### Dead RRF signals

Для raw add() фактов (без entity/slot_key/canonical):

| Сигнал | RRF Weight (default) | Weight (AGG) | Status |
|--------|---------------------|--------------|--------|
| BM25F | 5.0 | 3.0 | DEGRADED — только content field active |
| slot-exact | 3.0 | **8.0** | **DEAD** — slot_key empty → score=0 |
| trigram | 2.0 | 2.0 | WORKS — content trigrams |
| importance | 1.5 | 2.5 | NON-DISCRIMINATIVE — все 0.8 |
| retention | 1.5 | 1.0 | NON-DISCRIMINATIVE — все 1.0 |
| recency | 1.0 | 0.5 | WORKS — created_at varies |

**Default:** 43% dead weight (slot + importance + retention = 6.0 / 14.0)
**AGGREGATION:** 67% dead weight (8.0 + 2.5 + 1.0 = 11.5 / 17.0)

### PRF anti-diversity problem

PRF extracts expansion terms from top-3 BM25 results. For aggregation:
- Top-3 are facts about the SAME sub-topic (e.g. all mention "pottery")
- Expansion terms reinforce that sub-topic (e.g. "pottery", "class", "studio")
- Facts about OTHER sub-topics (swimming, camping, violin) get NO boost
- Result: PRF concentrates results around first few matches instead of broadening

### Content-based entity detection approaches

**Approach 1 (dropped): Capitalized words in query**
- Problem: "What"[0].isupper() = True → added "what" as entity
- Same for "The", "How", "Where"
- Dropped by user: "6 не нравится"

**Approach 2 (from research): DF-band filtering**
- Tokens in 5%-60% document frequency = entity candidates
- "What" at 90%+ DF → filtered out
- "Melanie" at ~15% DF → passes
- Problem: adds too many non-entity tokens to entity_dict
- Problem: stemmed tokens ("melani") don't match raw query ("melanie")

**Decided approach: Raw-aware RRF weights**
- Zero out dead signals when <10% facts have slot_key
- Simple, no entity detection needed
- Combined with skip PRF for AGGREGATION

### Speaker IDF analysis

At 1740 facts with speaker appearing in ~50%:
- Speaker IDF = log(1740/870) = 0.69
- Activity word "swim" at df=3: IDF = log(1740/3) = 6.21 → 9x higher
- BM25 ranks by rare keyword match, not by speaker → finds facts WITH matching keywords but misses other facts about same speaker

---

## 3. Competitive Analysis (complete)

### Post-extraction consolidation

| System | Entity-level aggregate? | How they store facts |
|--------|------------------------|---------------------|
| Mem0 | NO | Atomic extracted facts |
| Zep | NO (graph relations) | Knowledge graph: entity→relation→entity |
| Letta | NO | Raw messages, LLM summarizes at retrieval |
| Hindsight | NO | Raw storage |
| memvid | NO | Raw chunks + embeddings |
| MAGMA | NO | Atomic facts |

**ai-knot consolidation is UNIQUE.** Zep's knowledge graph stores relationships between entities but doesn't create keyword-dense aggregate facts optimized for BM25 retrieval.

### Overfetch

| System | Overfetch? | Method |
|--------|-----------|--------|
| memvid | YES | Static multiplier: analytical×5, aggregation×3, recency×2 |
| Zep | YES | Graph node expansion |
| Letta | NO | Fixed context window |
| Mem0 | NO | Standard top_k |
| Hindsight | NO | Standard retrieval |

Overfetch alone = commoditized. But intent-adaptive with faithfulness_k floor protection = unique.

### Multi-signal RRF

NO competitor uses 6-signal RRF fusion. All use simpler approaches:
- Mem0: cosine similarity
- Zep: graph traversal
- memvid: cosine + metadata scoring
- Letta: LLM-based retrieval
- Hindsight: embedding similarity

### PRF (Pseudo-Relevance Feedback)

NO competitor uses PRF. All use either:
- Dense retrieval (embeddings/cosine)
- Knowledge graph traversal
- LLM-based query expansion (not statistical PRF)

---

## 4. BM25 Length Normalization for Aggregates

**Problem:** 60-token aggregate has `dl/avgdl ~ 6x` (if avg fact is 10 tokens). BM25F denominator `1 + 0.75*(6-1) = 4.75` → per-term score ~4.7x lower than matching atomic fact.

**Solution:** Keep aggregates SHORT:
- Content: `"melanie: pottery, camping, swimming, Oliver, Luna"` (~12 tokens)
- Canonical: `"melanie pottery camping swimming oliver luna"` (~6 tokens)
- Length penalty: dl/avgdl ~1.5x → denominator ~1.375 → only ~1.4x lower (acceptable)

**Slot-exact signal for aggregates:**
- `slot_key = "melanie::_agg"` → slot_tokens = {"melani", "_agg"}
- Query "What activities does Melanie do?" → query_tokens include "melani"
- slot_score = 1/2 = 0.5 (one token matches)
- Same as individual facts like "melanie::hobby" → slot_score = 1/2 = 0.5
- No special advantage, but no disadvantage either

**Aggregate ranks via CONTENT match + entity scoping, not via slot-exact boost.**
