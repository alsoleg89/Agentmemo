# Zep: Temporal Knowledge Graph Architecture for Agent Memory

- **Paper**: arXiv 2501.13956, January 2025
- **Authors**: Preston Rasmussen et al.
- **Code**: https://github.com/getzep/graphiti

## Key Technique

Three-tier knowledge graph:
1. **Episodes** — raw interaction records
2. **Semantic entities** — extracted entities with attributes
3. **Communities** — clustered entity groups

Powered by **Graphiti** engine. Each edge has **four timestamps**: t_created, t_expired, t_valid, t_invalid (bi-temporal model). Dynamic updates via temporal extraction and edge invalidation. Incremental graph construction without batch recomputation.

## Results

- Outperforms MemGPT on DMR benchmark (94.8% vs 93.4%)

## Difference from Standard RAG

Full temporal provenance on every edge. Can answer "what did the agent know in March 2025?" by filtering on validity windows.

## Difference from memvid

memvid has no explicit temporal graph structure. Zep maintains bi-temporal validity windows on every fact.

## Applicability to ai-knot

**Very high.** ai-knot already has valid_from/valid_until on facts and slot-based CAS. Adding bi-temporal edge tracking and entity-to-entity links would enable temporal reasoning ("What was X's job before the current one?") and proper multi-hop traversal.
