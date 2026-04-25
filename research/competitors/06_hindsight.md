# Hindsight / Vectorize (TEMPR) — Technical Retrieval Analysis

- **Paper**: arXiv 2512.12818, December 2025
- **Code**: https://github.com/vectorize-io/hindsight

## Retrieval Mechanism: TEMPR — Four-way parallel retrieval

### Four Channels
1. **Semantic**: Vector similarity over fact embeddings
2. **BM25**: Keyword matching over fact text
3. **Entity graph traversal**: Walk edges through shared entities. Edges weighted via decay and similarity.
4. **Temporal**: Time-window filtering + temporal spreading activation

### Temporal Spreading Activation
- Time-anchored graph traversal from temporal window
- Walks causal and temporal links to build coherent event sequence
- Based on Collins & Loftus (1975)
- 30-80 nodes per query (budget: 100)
- +15-40ms latency

### Graph Link Types
Four edge types: temporal, semantic, entity, causal

### Fusion
RRF across four channels → cross-encoder reranking

### Four Memory Networks
- World (objective facts)
- Experience (agent actions)
- Opinion (beliefs with confidence)
- Observation (entity summaries)

### Results
- 89.61% on LoCoMo (Gemini-3 Pro + TEMPR)
- 91.4% on LongMemEval

### What Makes It Unique
Only major framework using spreading activation. Four parallel channels. Causal links. Confidence-scored beliefs.

### What it does NOT do
- No hypergraph/n-ary grouping
- No fact consolidation/summarization
- No Ebbinghaus decay
- No slot-based CAS
