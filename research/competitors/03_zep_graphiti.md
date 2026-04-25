# Zep / Graphiti — Technical Retrieval Analysis

- **Stars**: ~24K
- **Paper**: arXiv 2501.13956

## Retrieval Mechanism: Triple-hybrid (cosine + BM25 + BFS graph traversal)

### Three Channels
1. **Semantic (cosine)**: Entity nodes and fact edges have embeddings. Cosine KNN via Neo4j/FalkorDB Lucene vector indexes.
2. **Keyword (BM25)**: Okapi BM25 full-text over node names and fact strings via Lucene.
3. **Graph traversal (BFS)**: Breadth-first search from seed nodes. Two modes:
   - Explicit seed nodes
   - "Land and expand" — semantic+BM25 results as BFS seeds → find adjacent within N hops

### Reranking
Five options: RRF, MMR, cross-encoder, node_distance, episode_mentions

### Temporal Layer
- Bi-temporal: each fact has valid_from, valid_to
- Old facts invalidated, not deleted
- Queries filter by time

### Search Scopes
Edges (facts), Nodes (entities), Communities — each independently searchable

### What Makes It Unique
Most complete graph-retrieval among competitors. Bi-temporal + BFS + hybrid.

### What it does NOT do
- No spreading activation
- No hypergraph/n-ary grouping
- No fact consolidation
- No Ebbinghaus decay
- Standard binary-edge graph only
