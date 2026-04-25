# Supermemory — Technical Retrieval Analysis

- **Stars**: ~10K

## Retrieval Mechanism: Hybrid vector + BM25 + proprietary "memory graph"

### Hybrid Search
Vector embeddings + BM25 in parallel, merged and reranked against query context (user, timestamp, thread)

### Memory Graph
Custom vector-graph engine (not Neo4j). "Ontology-aware edges" — relationships carry semantic meaning. Handles knowledge updates, contradictions, merges, inferences.

### Five-Layer Stack
Connectors → Extractors → Super-RAG → Memory Graph → User Profiles

### Claims
Sub-300ms retrieval, #1 on LongMemEval (85.4%), LoCoMo, ConvoMem (self-reported)

### What it does NOT do
- Mostly closed-source/proprietary
- No published paper with algorithmic details
- "Ontology-aware edges" and "memory graph" lack technical specs
- No evidence of graph traversal, BFS, or spreading activation
