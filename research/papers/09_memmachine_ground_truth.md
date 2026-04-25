# MemMachine: Ground-Truth-Preserving Memory System

- **Paper**: arXiv 2604.04853, April 2026
- **Website**: https://memmachine.ai/

## Key Technique

Stores **raw conversational episodes** rather than extracted facts, avoiding lossy extraction. Uses **contextualized retrieval** expanding nucleus matches with surrounding context.

Key insight: extraction is lossy — storing raw episodes preserves ground truth.

## Results

- **0.9169** (91.69%) on LoCoMo (gpt-4.1-mini) — among the strongest published results
- **80% token reduction** vs competitors

## Difference from Standard RAG

Rejects the "extract then search" paradigm. Stores raw episodes and uses contextualized retrieval to find and expand relevant passages.

## Difference from memvid

Similar philosophy (store more context, not less), but with explicit ground-truth preservation guarantees and nucleus expansion.

## Applicability to ai-knot

**Low-medium.** ai-knot's core value proposition IS structured extraction (entity/attribute/value). Adopting MemMachine's raw-episode approach would undermine ai-knot's unique architecture. However, the nucleus expansion concept (retrieve a fact, expand to surrounding context) is applicable.
