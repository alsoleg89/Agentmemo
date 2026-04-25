# Changes 2, 5, 6 — Multi-agent, Complexity, Effectiveness Research

**Date:** 2026-04-11

---

## Change 2: Post-extraction consolidation (entity-level aggregates)

### Multi-agent impact
- **No direct interference** — pool recall has its own facet-based retrieval, doesn't use `_execute_recall()`
- **Trust inflation risk** — aggregate gets retrieved for many different queries → inflates publisher's `used_count` → disproportionate trust boost
- **Cross-entity pollution** — aggregate mentioning "melanie" also mentions "oliver", "pottery" etc. If those are entities in entity_dict, the aggregate appears in their scoped sets too → noise

### Complexity
- **O(N)** grouping by entity — one pass over all facts
- **50 entities on 1000 facts** → 50 CAS checks, 50 extra facts stored = 5% storage overhead
- **Dominated by embedding** cost if `learn_async` embeds aggregates, not by logic

### BM25 effectiveness — PROBLEM FOUND
- **Length normalization penalty**: 60-token aggregate has `dl/avgdl ~ 6x` (if avg fact is 10 tokens). BM25F denominator `1 + 0.75*(6-1) = 4.75` → per-term score is **~4.7x lower** than matching atomic fact
- **Aggregates WON'T rank well** via BM25 content field alone
- **BUT**: AGGREGATION intent RRF override (BM25=3.0, slot=8.0) gives `slot_key="{entity}::_agg"` massive slot-exact boost → aggregate could over-rank atomic facts via slot signal
- **canonical_surface** (weight 1.5) helps if concise, but content field dilutes across 15+ pairs

### Verdict
- Aggregates help AGGREGATION-intent queries via slot-exact signal, but BM25 length normalization works against them for general queries
- Cross-entity pollution in scoped sets is a real risk
- Trust inflation is minor but worth noting

---

## Change 5: Intent-adaptive overfetch for AGGREGATION

### Multi-agent impact
- **Pool recall**: doesn't use this path → no multi-agent impact
- **No diversity cap** for AGGREGATION (`_INTENT_DIVERSITY_CAP` only covers MULTI_SOURCE and BROAD_DISCOVERY)
- **`_sandwich_reorder()`** works fine — receives already-trimmed pairs

### Performance
- **Near zero overhead** — BM25 index building is O(n_facts), doesn't depend on top_k. Six ranker sorts are O(n log n) regardless. top_k only affects final slice
- **PRF unaffected** — uses hardcoded `_PRF_TOP_K = 3`, independent of search top_k

### CRITICAL RISK: Faithfulness floor bypass
- Floor gate at `_bm25.py:274` checks `len(eligible_ids) >= top_k`
- With overfetch `top_k=180`: if only 100 facts have lexical matches, floor activates at 60 (100 >= 60) but falls back to unfiltered RRF at 180 (100 < 180)
- **Overfetch could disable the faithfulness floor**, letting importance/recency push unrelated facts into results
- **FIX**: pass original `top_k` to faithfulness floor, not overfetched value

### Does overfetch actually help diversity?
- **YES, real gain** — wider initial pool means more entity facts have real BM25 scores instead of artificial `min_score * 0.9` discount from entity-boost
- Entity-boost/hop have more "room" — fewer real results get displaced during `[:top_k]` trim
- Main gain from both BM25 diversity AND entity-boost/hop having more candidates

### Verdict
- Low cost, real diversity gain
- Must fix faithfulness floor to use original top_k
- Clean for multi-agent (private KB only)

---

## Change 6: Content-based entity dictionary enhancement

### Multi-agent impact
- **Private KB only** — pool recall has own facet-based retrieval, doesn't call `_build_entity_dictionary` or entity scoping
- **No multi-agent interference**

### CRITICAL BUG: Stopword false positives
- `"What"[0].isupper()` = True, `len("what") > 2` = True
- "what" appears in many facts → passes 3-fact threshold → added as "entity"
- Same for "The", "How", "Where", "Does", etc.
- **FIX**: filter through existing `_QUERY_STOPWORDS` from `tokenizer.py:403` before scanning

### Complexity
- **3 proper nouns x 1000 facts**: ~300K char comparisons — under 1ms
- **10,000 facts**: ~3M char comparisons — under 10ms
- **Acceptable** — existing `_build_entity_mention_index` already does same-scale scans

### Edge cases
- **"LGBTQ"** — correctly detected as entity (uppercase, meaningful)
- **"tell me about caroline"** — all lowercase, detection fails. Acceptable as fallback — if learn() produced `entity="caroline"`, primary path handles it
- **3-fact threshold** — too low without stopword filter; fine with it

### Verdict
- Simple, effective, low cost
- **Must add stopword filter** — without it, "What"/"The"/"How" pollute entity_dict
- Only helps private KB with empty entity fields (raw facts from add())
