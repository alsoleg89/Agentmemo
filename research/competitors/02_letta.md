# Letta (ex-MemGPT) — Technical Retrieval Analysis

- **Stars**: ~21K

## Retrieval Mechanism: Agentic tool-call vector search

### Architecture
Three-tier OS-inspired memory:
- **Core Memory**: In-context (like RAM) — always visible to LLM
- **Recall Memory**: Conversation log (like disk cache) — keyword search
- **Archival Memory**: Long-term vector store (like cold storage) — embedding search

### Archival Search
- Plain vector similarity search
- Each memory chunk embedded (default: text-embedding-3-small)
- `archival_memory_search` tool converts query → vector → top-k

### Hybrid (newer)
- Vector + keyword (full-text) search fused with RRF
- Available in hosted API (TurboPuffer) and self-hosted (pgvector)

### Key Differentiator
The retrieval is AGENTIC — LLM decides WHEN and WHAT to search by issuing tool calls. Agent can iteratively refine queries, search multiple times, compose results.

### What it does NOT do
- No knowledge graph
- No graph traversal
- No temporal reasoning
- No entity extraction
- No fact consolidation/grouping
- Intelligence is in agent's tool-calling, not retrieval algorithm
