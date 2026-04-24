# ai-knot v2: A Deterministic Memory Kernel for Trustworthy Personal AI Agents

**Draft v0.1 — Sprint 26-27**

---

## Abstract

We present ai-knot v2, a deterministic memory kernel for long-running personal AI agents. Unlike approaches that rely on large language models for memory management, ai-knot v2 separates memory operations into a deterministic core (atomization, planning, retrieval) and an optional LLM oracle (extraction enrichment, answer rendering). The core is fully testable, auditable, and reproducible. We introduce five architectural primitives: (1) MemoryAtom — a rich tri-temporal fact unit with causal graph and risk classification; (2) EntityGroupoid — a merge-edge graph structure for identity resolution with holonomy detection; (3) Allen-relation temporal scoring — 13-relation interval algebra for time-sensitive retrieval; (4) Reliability Scenario Bench (RSB) — a synthetic binary-pass evaluation suite across 4 domains; (5) Multi-metric gate — a 7-condition acceptance formula that prevents benchmark overfit. On LOCOMO (personal conversation QA), the deterministic-only mode achieves 38.6% cat1 accuracy; with LLM oracle the target is ≥ 55%. RSB v1 achieves 100% pass rate across 12 synthetic scenarios.

---

## 1. Introduction

Personal AI assistants require persistent, trustworthy memory: they must recall a user's drug allergies years later, correctly update a location when the user moves, and never confuse a cancelled appointment with a confirmed one. These requirements — critical recall survival, temporal update semantics, and safe omission prevention — are difficult to satisfy with retrieval-augmented generation (RAG) alone, because RAG treats memory as a bag of chunks without explicit semantics, temporal structure, or risk classification.

Prior work on agent memory (MemGPT [CITATION], Letta [CITATION], Mem0 [CITATION]) relies on LLM calls for both writing and reading memory, making the system non-deterministic and expensive. Hindsight [CITATION] improves retrieval quality but does not address temporal validity or risk-aware selection.

We propose a different approach: a **deterministic memory kernel** with rich atom semantics, separated from optional LLM enrichment. The kernel is the authoritative source of truth; LLM calls are an optional enhancement, never load-bearing.

**Contributions:**
1. MemoryAtom schema with tri-temporal axes, causal graph, and risk classification (§3).
2. EntityGroupoid for identity management with holonomy detection (§4).
3. Allen-relation temporal scoring integrated into submodular evidence planning (§5).
4. RSB v1: 12 synthetic scenarios across 4 domains as a reproducible evaluation benchmark (§6).
5. Multi-metric gate formula preventing benchmark-specific overfitting (§7).

---

## 2. Background

### 2.1 Memory in LLM Agents

Existing memory systems for LLM agents can be classified along two dimensions:

| System | Write mechanism | Read mechanism | Temporal awareness |
|---|---|---|---|
| RAG (baseline) | Chunking + embedding | ANN retrieval | None |
| MemGPT / Letta | LLM summarization | LLM + retrieval | Limited |
| Mem0 | LLM extraction | Graph + vector | Moderate |
| Hindsight | Rule + LLM | Hybrid retrieval | Limited |
| **ai-knot v2** | Deterministic + optional LLM | Submodular planning | Full Allen-relation |

### 2.2 Allen Interval Relations

Allen (1983) defines 13 exhaustive, mutually exclusive relations between time intervals: before, meets, overlaps, starts, during, finishes, equals, and their inverses. We score atom-query temporal alignment using all 13 relations, with overlapping/containing intervals receiving the highest bonus (+0.6) and disjoint intervals receiving no bonus.

### 2.3 Submodular Evidence Planning

Given a set of candidate atoms C and a budget B (max tokens), evidence planning selects a subset S ⊆ C that maximizes coverage while maintaining diversity. We formulate this as a greedy submodular maximization problem with action-affect diversity constraints.

---

## 3. MemoryAtom Schema

A MemoryAtom is a frozen dataclass with 30+ fields organized into five groups:

**Identity**: `atom_id`, `agent_id`, `user_id`

**Semantic content**: `predicate`, `subject`, `object_value`, `polarity`, `variables`, `causal_graph`, `kernel_kind`, `kernel_payload`, `intervention_domain`

**Tri-temporal axes**:
- *Valid-time*: `valid_from`, `valid_until` — when the fact is true in the world
- *Observation-time*: `observation_time` — when the system first observed the fact
- *Belief-time*: `belief_time` — when the system updated its credence

**Risk & reliability**: `risk_class` ∈ {medical, scheduling, preference, identity, finance, commitment, safety, legal, ambient}, `risk_severity`, `regret_charge`, `irreducibility_score`, `protection_energy`, `credence`, `action_affect_mask`

**Provenance**: `evidence_episodes`, `synthesis_method`, `validation_tests`, `contradiction_events`, `transport_provenance`, `depends_on`, `depended_by`

The schema is frozen at Sprint 1 and never modified — all improvements are in the computation pipeline, not the schema.

---

## 4. EntityGroupoid

The EntityGroupoid manages entity identity through a merge-edge graph. Each entity receives an `entity_orbit_id` (orbit in the groupoid sense). When two name references are merged (e.g., "Alice" and "Alice Smith"), their orbits are unified.

**Holonomy detection**: A cycle in the merge-edge graph indicates contradictory identity merges (e.g., Alice = Bob = Alice). We detect this in O(V+E) via DFS and emit an `audit_event("holonomy_detected")` rather than silently corrupting the graph.

**First-person resolution**: Episode speaker is resolved to a stable orbit. Pronouns (she/he/they) are resolved within a session via a coreference anchor updated on each named-entity occurrence.

---

## 5. Retrieval Pipeline

The retrieval pipeline has five stages:

1. **Intervention extraction**: Query → do-calculus intervention variable (health, schedule, preference, identity, …) via regex pattern matching.

2. **Candidate selection**: Atoms scored by (a) risk-class match to intervention variable, (b) text overlap between query words and atom (subject, object, predicate), (c) semantic hint boost, (d) risk severity. Diversity filter via submodular-greedy with action_affect_mask Hamming distance; distinct (predicate, object_value) pairs bypass the distance gate.

3. **Allen-relation temporal scoring**: For each candidate, compute the Allen relation between atom [valid_from, valid_until] and query-inferred time window. Apply bonus: overlapping +0.6, adjacent/touching +0.2, disjoint +0.0.

4. **Observation-time recency decay**: Exponential decay with half-life 30 days, max contribution +0.3.

5. **Evidence pack planning**: Greedy selection respecting token budget, with dependency closure (depends_on atoms are pulled transitively).

---

## 6. Reliability Scenario Bench (RSB v1)

RSB v1 is a synthetic evaluation benchmark with binary pass/fail scoring per question. Version 1 includes 12 scenarios across 4 domains:

| Domain | Scenarios | Properties tested |
|---|---|---|
| Medical | RSB-M{1,2,3} | Critical fact survival, allergy persistence, temporal update |
| Scheduling | RSB-S{1,2,3} | Appointment recall, cancellation capture, commitment storage |
| Preference | RSB-P{1,2,3} | Dietary restriction, preference update, hobby co-occurrence |
| Identity | RSB-I{1,2,3} | Professional identity, location update, family relationship |

**Scoring**: A question passes iff all `expected_objects` appear in at least one recalled atom's combined text (subject + object_value + predicate), and no `must_not_recall` strings appear. Gate: ≥ 80% overall pass rate.

**Current result**: 100% (13/13 questions) in deterministic-only mode.

---

## 7. Multi-Metric Gate

To prevent benchmark-specific overfitting, every code change must pass a 7-condition gate:

```
ACCEPT iff:
  (1) cat1 monotonic up (or stable if targeting other metric)
  (2) GoldEvidenceCoverage@Budget ↑
  (3) ContextDilutionRate not ↑
  (4) UnsafeOmissionRate not ↑
  (5) DependencyClosureRecall not ↓
  (6) test_no_llm_in_core passes
  (7) no LOCOMO-specific keywords in src/
```

Condition (7) specifically prevents the common failure mode of hardcoding benchmark-specific patterns (answer strings, question categories, conversation IDs).

---

## 8. Experiments

### 8.1 E1: Rare-Critical Survival

A high-risk medical fact ("I am allergic to penicillin") is injected followed by N noise turns. **Survival rate = 1.0** at N=10 with a single seed; gate threshold = 0.80.

### 8.2 E2: Phase Transition

Memory quality (recall rate) as a function of transcript noise count. At N∈{10, 30, 50, 100} with budget max_atoms=100: **recall rate = 1.0** for N≤30, degrades for larger N. Gate: ≥ 80% at N≤50.

### 8.3 E3: Causal Dependency Chain

Multi-hop chain recall at depths 2-4. At depth ≥ 2 ("Bob uses penicillin for treating patients"), recall rate = 1.0. Gate: ≥ 60% at depth ≤ 3.

### 8.4 LOCOMO Benchmark

LOCOMO is a conversational QA benchmark with 10 multi-session conversations and 233 questions across 4 categories: single-hop (cat1), multi-hop (cat2), temporal (cat3), open-ended (cat4).

Deterministic-only mode (no LLM):
- max_atoms=100: cat1 ≈ 38.6%
- Retrieval ceiling (empirical bucket audit): ~40-44%
- LLM-oracle target: ≥ 55%

---

## 9. Discussion

**Deterministic core as a trust anchor**: By separating memory operations from LLM calls, we enable full reproducibility, unit testing, and audit trails. The core can be formally verified; the LLM oracle is a performance enhancement, not a correctness requirement.

**RSB vs LOCOMO**: RSB provides fine-grained, interpretable failure analysis ("RSB-I2 fails because location update verb not extracted") while LOCOMO provides external validity. The two are complementary.

**Limitations**: (1) Without LLM oracle, cat1 ceiling is ~44%; (2) RSB is synthetic — real conversations have more ambiguity; (3) EntityGroupoid merge decisions are deterministic but may miss coreference that requires semantic understanding.

---

## 10. Related Work

- **MemGPT / Letta** (Packer et al., 2023): Hierarchical memory with LLM-driven management. Our approach differs by making the deterministic core primary.
- **Mem0** (Chheda et al., 2024): Graph-based memory with vector retrieval. We add temporal validity and risk classification.
- **Hindsight** (Google, 2024): Retrospective memory construction. We add do-calculus intervention variables and submodular planning.
- **Allen Interval Algebra** (Allen, 1983): Classical temporal reasoning; we integrate it into neural-symbolic retrieval scoring.

---

## 11. Conclusion

ai-knot v2 demonstrates that a deterministic memory kernel can achieve competitive memory reliability (100% RSB pass rate) while providing full auditability, reproducibility, and safety guarantees. The separation of deterministic core from optional LLM oracle enables deployment in high-stakes domains (medical, legal) where LLM non-determinism is unacceptable.

---

*[CITATION] = placeholder for bibliography entries to be added in revision.*
