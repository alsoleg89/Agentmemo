# SYNAPSE: Episodic-Semantic Memory via Spreading Activation

- **Paper**: arXiv 2601.02744, January 2026
- **Authors**: University of Georgia researchers

## Key Technique

Constructs a **Unified Episodic-Semantic Graph** where raw interaction logs (episodic nodes) are synthesized into abstract concept nodes (semantic nodes). Retrieval uses **spreading activation** (borrowed from cognitive science) -- querying a node causes activation energy to propagate through the graph with lateral inhibition and temporal decay, highlighting relevant subgraphs while filtering interference.

Uses a **Triple Hybrid Retrieval** strategy: geometric embeddings + activation-based graph traversal.

## Results

- Significantly outperforms SOTA on temporal and multi-hop reasoning on LoCoMo

## Difference from Standard RAG

Retrieval is not search -- it is *energy propagation through an associative network*. Relevance emerges from network structure, not from embedding similarity.

## Difference from memvid

memvid classifies queries and searches wider. SYNAPSE lets the graph topology determine what is relevant through activation propagation -- fundamentally different from any search-based approach.

## Applicability to ai-knot

**Very high.** ai-knot's entity/attribute/value facts are already a graph implicitly (entities link to attributes). Spreading activation over this implicit graph could surface related facts that BM25+dense misses, particularly for multi-hop questions ("What does X's employer do?") where the link is structural, not textual.
