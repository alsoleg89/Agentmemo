# MA Scenario Analysis for Entity-Scoped Retrieval

## Key Finding
Entity+attribute metadata is stored in pool facts but NOT indexed during recall(). All pool retrieval is keyword-based (BM25/dense), not entity-scoped.

## MA Scenarios That Would Benefit from Entity-Mention Index

| Scenario | Focus | How ESR Helps |
|----------|-------|---------------|
| S10 (CAS) | 4 agents publish salary v1-v4 | O(1) entity+attr lookup vs linear scan |
| S21 (assembly) | 5 specialists, cross-domain queries | Pre-filter to agents with relevant entities |
| S25 (conflict) | 10 slots, canonical authority | Direct slot lookup for verification |
| S26 (sparse assembly) | N=10/100/1000 specialists | Entity-scoped BM25 within relevant agent subsets |

## Pool Recall Path Differences
- Uses `SharedMemoryPool.recall()` with `requesting_agent_id`
- Trust discount per agent (Marsh 1994)
- Overfetch 3x top_k before trust discount
- Diversity caps for monopoly prevention
- MULTI_SOURCE queries → facet decomposition via `SharedPoolRecallService`

## Integration Point
Entity-mention index changes are in `knowledge.py:_execute_recall()` which is the single-agent path. Pool recall uses `_pool_recall.py` with `HybridRetriever`. To benefit MA:
- Phase 1 improvements propagate via shared intent classification (_query_intent.py)
- AGGREGATION intent + RRF weights apply to both paths
- Full entity-scoping for pool would require changes to _pool_recall.py (future work)
