# Hindsight: Building Agent Memory that Retains, Recalls, and Reflects

- **Paper**: arXiv 2512.12818, December 2025
- **Authors**: Vectorize team + Virginia Tech
- **Code**: https://github.com/vectorize-io/hindsight

## Key Technique: TEMPR

**TEMPR** (Temporal Entity Memory Priming Retrieval) runs **four parallel retrieval channels**:
1. Semantic vector search
2. BM25 keyword search
3. Graph traversal through shared entities
4. Temporal filtering

Memory organized into **four logical networks**:
- World (objective facts)
- Bank (agent experiences)
- Opinion (beliefs with confidence)
- Observation (entity summaries)

## Results

- **89.61%** on LoCoMo (Gemini-3 Pro + TEMPR)
- **91.4%** on LongMemEval

## Difference from Standard RAG

Four parallel retrieval channels fused, not a single pipeline. Separate networks for facts vs opinions vs experiences.

## Difference from memvid

memvid does BM25+semantic hybrid. Hindsight adds entity graph traversal and temporal filtering as additional retrieval channels, plus distinguishes fact types.

## Applicability to ai-knot

**Very high and directly actionable.** ai-knot already does BM25+dense hybrid. Adding entity graph traversal as a third retrieval channel (follow entity links to find related facts) and explicit temporal filtering would be natural extensions. The four-network concept maps to ai-knot's memory types (semantic/procedural/episodic).
