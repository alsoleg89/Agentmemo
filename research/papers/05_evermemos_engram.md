# EverMemOS: Self-Organizing Memory Operating System

- **Paper**: arXiv 2601.02163, January 2026

## Key Technique

Three-phase lifecycle inspired by neuroscience "engram" concept:

1. **Episodic Trace Formation** — converts dialogue into MemCells capturing atomic facts and time-bounded **Foresight signals** (predictions of what info will be needed later)
2. **Semantic Consolidation** — organizes MemCells into thematic **MemScenes** (groups of related facts)
3. **Reconstructive Recollection** — performs MemScene-guided agentic retrieval

## Results

- **93.05%** accuracy on LoCoMo
- +12.1% on multi-hop vs baselines
- +16.1% on temporal vs baselines

## Difference from Standard RAG

Retrieval is guided by pre-organized thematic scenes, not raw similarity. "Foresight signals" predict what information will be needed later -- anticipatory indexing.

## Difference from memvid

memvid stores and searches. EverMemOS pre-organizes memories into thematic clusters with anticipatory signals.

## Applicability to ai-knot

**High.** The MemCell concept maps to ai-knot's structured facts. MemScene grouping could be implemented as fact clusters by entity+attribute domain. Foresight signals could improve retrieval for multi-hop queries.
