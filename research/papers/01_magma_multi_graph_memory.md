# MAGMA: Multi-Graph Agentic Memory Architecture

- **Paper**: arXiv 2601.03236, January 2026
- **Authors**: Fred Jiang et al.
- **Code**: https://github.com/FredJiang0324/MAMGA

## Key Technique

Represents each memory item across **four orthogonal graphs** (semantic, temporal, causal, entity). Retrieval is formulated as *policy-guided traversal* over these relational views -- an Adaptive Traversal Policy routes queries to the relevant graph(s), traverses them independently, and fuses the resulting subgraphs into a compact, type-aligned context.

A dual-stream memory evolution mechanism decouples latency-sensitive event ingestion from asynchronous structural consolidation.

## Results

- +45.5% reasoning accuracy vs baselines
- 95% token reduction in retrieved context
- State-of-the-art on LoCoMo

## Difference from Standard RAG

Instead of a single vector index, uses four parallel graph structures with learned routing. Retrieval is graph traversal, not nearest-neighbor search.

## Difference from memvid

memvid uses BM25+semantic hybrid over session storage. MAGMA decomposes memory into orthogonal relational planes and routes queries to the right plane. It has explicit causal graph edges, which neither memvid nor ai-knot model.

## Applicability to ai-knot

**High.** ai-knot already extracts entity/attribute/value facts. MAGMA suggests that separating temporal, causal, and entity relationships into parallel retrieval channels (rather than mixing them in a single BM25+dense search) could dramatically improve multi-hop and temporal queries.
