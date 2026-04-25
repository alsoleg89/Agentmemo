# Competitor Retrieval Techniques Comparison (April 2026)

## Technical Retrieval Mechanisms

| Technique | Mem0 (48K) | Letta (21K) | Zep (24K) | Cognee (12K) | Supermemory (10K) | Hindsight | memvid (6K) | **ai-knot** |
|---|---|---|---|---|---|---|---|---|
| Vector similarity | YES (primary) | YES (primary) | YES | YES | YES | YES | YES (HNSW) | YES |
| BM25 keyword | partial | YES (newer) | YES (Okapi) | NO | YES | YES | YES (Tantivy) | YES (BM25F) |
| Knowledge graph | YES (triples) | NO | YES (temporal) | YES | YES (proprietary) | YES (4-network) | NO | Implicit (entity/attr) |
| Graph traversal (BFS) | NO (1-hop only) | NO | YES (configurable) | Partial | Unknown | YES | NO | Partial (entity-hop) |
| Temporal validity | Soft-delete | NO | YES (bi-temporal) | NO | Claimed | YES | NO | YES (valid_from/until) |
| Spreading activation | NO | NO | NO | NO | NO | **YES** | NO | NO |
| RRF fusion | NO | YES (newer) | YES | NO | YES (implied) | YES | YES (k=60) | YES (6-signal) |
| Cross-encoder rerank | NO | NO | YES (optional) | NO | YES (claimed) | YES | NO | NO |
| Hypergraph / n-ary | NO | NO | NO | NO | NO | NO | NO | NO |
| LLM-to-Cypher | NO | NO | NO | YES | NO | NO | NO | NO |
| Agentic self-search | NO | YES (core) | NO | NO | NO | NO | NO | NO |
| Ebbinghaus decay | NO | NO | NO | NO | NO | NO | NO | **YES** |
| Slot-based CAS | NO | NO | NO | NO | NO | NO | NO | **YES** |
| Multi-agent trust | NO | NO | NO | NO | NO | NO | NO | **YES** |
| Post-extraction consolidation | NO | NO | NO | NO | NO | NO | NO | NO |

## Genuinely Unused Techniques (by ALL major competitors)

1. **Hypergraph-based memory** — ZERO major competitors. Only RUNSTACK (tiny startup) + academic papers.
2. **Post-extraction fact consolidation** — ZERO competitors create aggregate summary facts from individual extracted facts.
3. **Topic-based fact clustering with coarse-to-fine retrieval** — ZERO competitors.
4. **N-ary relational grouping** — ZERO products (HyperGraphRAG is research only).

## Techniques Used by Only One Competitor

- **Spreading activation** — Only Hindsight (temporal SA)
- **Causal graph links** — Only Hindsight
- **LLM-to-Cypher** — Only Cognee
- **Agentic self-search** — Only Letta
- **Usage-based edge reweighting** — Cognee (memify), Hindsight (Hebbian)

## Sources

- [Mem0 Paper](https://arxiv.org/abs/2504.19413) | [Graph Memory Docs](https://docs.mem0.ai/open-source/features/graph-memory)
- [Letta Archival Memory](https://docs.letta.com/guides/core-concepts/memory/archival-memory)
- [Zep Paper](https://arxiv.org/abs/2501.13956) | [Blog](https://blog.getzep.com/how-do-you-search-a-knowledge-graph/)
- [Cognee Search Docs](https://docs.cognee.ai/core-concepts/main-operations/search)
- [Supermemory Tech](https://supermemory.ai/docs/supermemory-mcp/technology)
- [Hindsight Paper](https://arxiv.org/abs/2512.12818) | [SA Blog](https://hindsight.vectorize.io/blog/2026/03/12/spreading-activation-memory-graphs)
