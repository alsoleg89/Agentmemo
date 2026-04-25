# TiMem: Temporal-Hierarchical Memory Consolidation

- **Paper**: arXiv 2601.02845, January 2026

## Key Technique

Organizes conversations into a **Temporal Memory Tree (TMT)** with progressive abstraction:
- Level 0: Raw observations
- Level 1: Fact-level extractions
- Level 2: Entity summaries
- Level 3: Persona representations

Memory Recall uses a **complexity-aware planner** that selects appropriate hierarchy levels based on query complexity. Consolidation uses level-specific prompts controlling abstraction level.

## Results

- **75.30%** on LoCoMo (lower than competitors)
- But reduces recalled memory length by **52.20%** (efficiency win)

## Difference from Standard RAG

Retrieval selects the right *abstraction level*, not just the right document. RAPTOR-like tree but with temporal ordering and dynamic consolidation.

## Difference from memvid

memvid searches at one level. TiMem builds a tree and retrieves from different levels depending on query complexity.

## Applicability to ai-knot

**Medium.** Adding a hierarchy (fact → entity summary → persona summary) with level selection could improve high-level queries while keeping precision for specific queries. But 75.3% LoCoMo score suggests the approach alone is insufficient.
