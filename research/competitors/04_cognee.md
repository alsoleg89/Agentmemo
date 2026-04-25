# Cognee — Technical Retrieval Analysis

- **Stars**: ~12K

## Retrieval Mechanism: 14 retrieval modes

### Key Modes
1. **SummariesRetriever**: Vector search over summary embeddings
2. **InsightsRetriever**: Entity-relationship triples from KG
3. **GraphCompletionRetriever**: Vector search → extract local subgraph → LLM completion (primary hybrid)
4. **GraphCompletionCotRetriever**: Above + chain-of-thought
5. **NaturalLanguageRetriever**: LLM translates query → Cypher → graph DB query
6. **RAG_COMPLETION**: Standard chunk-based RAG

### Graph Backends
Kuzu, Neo4j, Memgraph, NetworkX

### Unique Feature: memify
Prunes stale nodes and reweights edges based on usage signals. Adaptive element.

### What it does NOT do
- No BM25 keyword search
- No temporal validity windows
- No spreading activation
- No hypergraph/n-ary grouping
- No fact consolidation
