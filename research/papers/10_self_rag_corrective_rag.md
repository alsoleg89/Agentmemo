# Self-RAG and Corrective RAG (CRAG)

## Self-RAG
- **Paper**: ICLR 2024 Oral, arXiv 2310.11511
- **Authors**: Akari Asai et al.

Uses special **reflection tokens** to decide:
1. When to retrieve (vs relying on parametric knowledge)
2. Whether retrieved content is relevant
3. Whether the generation is supported by retrieved evidence

## Corrective RAG (CRAG)
- **Paper**: arXiv 2401.15884, 2024
- **Authors**: Shi-Qi Yan et al.

Adds a lightweight **retrieval evaluator** that scores retrieved documents as Correct/Ambiguous/Incorrect:
- Correct → use directly
- Ambiguous → refine and decompose query
- Incorrect → trigger web search fallback

## Applicability to ai-knot

**Medium.** Adding a retrieval quality check ("is this fact actually answering the question?") before returning results could improve precision. The CRAG decompose-on-ambiguity pattern could replace brute-force multi-query approaches.
