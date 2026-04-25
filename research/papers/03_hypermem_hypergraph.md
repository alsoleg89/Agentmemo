# HyperMem: Hypergraph Memory for Long-Term Conversations

- **Paper**: arXiv 2604.08256, April 2026

## Key Technique

Uses **hyperedges** (edges connecting more than two nodes) to model high-order associations between topics, episodes, and facts. Memory is structured into three levels (topics, episodes, facts), and hyperedges group related episodes and facts into coherent units.

Retrieval uses a **hybrid lexical-semantic index** with a **coarse-to-fine** strategy.

## Results

- **92.73%** LLM-as-judge accuracy on LoCoMo (state-of-the-art)

## Difference from Standard RAG

Standard graphs model pairwise relations; hypergraphs model n-ary associations. A single hyperedge can say "these 5 facts from 3 episodes relate to this topic."

## Difference from memvid

memvid stores sessions and searches linearly. HyperMem explicitly models the grouping structure (which facts belong together) using hypergraph topology.

## Applicability to ai-knot

**Medium-high.** ai-knot facts are currently flat (entity, attribute, value, timestamp). Hyperedge grouping could cluster related facts (e.g., all facts about a user's job) into retrievable units, improving multi-hop coherence. The coarse-to-fine retrieval pattern (topic → episode → fact) is particularly relevant for aggregation queries.
