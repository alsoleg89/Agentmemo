# A-MEM: Agentic Memory for LLM Agents (Zettelkasten)

- **Paper**: arXiv 2502.12110, NeurIPS 2025
- **Authors**: Wujiang Xu, Liang et al.

## Key Technique

Memory follows the **Zettelkasten method** -- each memory gets a structured note (context, keywords, tags) and **dynamic cross-links**. New memories trigger updates to existing memories' representations, enabling continuous self-refinement of the memory network.

## Difference from Standard RAG

Memory is not static -- ingesting new facts changes the representation of old facts.

## Difference from memvid

memvid stores sessions statically. A-MEM continuously refines the entire memory network when new facts arrive.

## Applicability to ai-knot

**Medium.** The concept of updating old facts' representations when new related facts arrive could improve ai-knot's consolidation logic. However, the continuous update mechanism adds write-amplification concerns.
