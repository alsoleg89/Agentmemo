# Multi-Agent Memory V3 Retrieval Architecture

This document defines the next retrieval architecture for `ai-knot`.

V3 is not "more assembly". It is a separation-of-concerns rewrite for the
multi-agent retrieval plane.

Primary goal:
- stop mixing query semantics, source trust, canonical truth resolution, and
  answer-set composition inside one ranking loop.

North-star outcome:
- preserve the current protocol strengths;
- make retrieval stable under query order;
- improve `S8`, `S9`, `S16`, `S19`, and `S21` without overfitting to `S26`;
- support both small-pool and large-pool multi-agent retrieval.

## Why V3

Current strengths:
- slot CAS and temporal versions are strong;
- shared pool coherence is strong;
- private recall remains solid;
- facet-aware retrieval is a useful building block.

Current retrieval failure mode:
- the system often behaves like a lexical ranker with source bias;
- source trust is updated from retrieval exposure, not just truth signals;
- empty querier state can override query semantics;
- canonical conflict resolution is too weak for unslotted claims;
- set construction is treated as "diversified top-k", not answer assembly.

## Design Principles

V3 separates four layers that are currently entangled:

1. Query semantics
   What kind of question is this?

2. Truth resolution
   Does this query want canonical truth, multi-view evidence, or a timeline?

3. Source prior
   How much should we trust this publisher in general?

4. Answer-set optimization
   Which set of facts best covers the answer slots for this query?

These layers must interact, but they must not be the same scoring variable.

## Core Model

V3 introduces three orthogonal query dimensions.

### 1. Semantic Intent

What the user is asking for.

```python
class RetrievalIntent(StrEnum):
    CANONICAL = "canonical"
    INCIDENT = "incident"
    ASSEMBLY = "assembly"
    INTEGRATION = "integration"
    COMPARISON = "comparison"
    EXPLORATION = "exploration"
    GENERAL = "general"
```

Notes:
- `BROAD_DISCOVERY` should not remain a semantic intent.
- "cold start" is a search mode, not the meaning of the query.

### 2. Exploration Mode

How broadly we should search.

```python
class ExplorationMode(StrEnum):
    PRECISE = "precise"
    BALANCED = "balanced"
    WIDE = "wide"
```

Derived from:
- whether the querier has local knowledge;
- pool size;
- channel filters;
- prior low-coverage outcomes.

### 3. Answer Roles

What evidence types are valid for this query.

```python
class AnswerRole(StrEnum):
    POLICY = "policy"
    STATUS = "status"
    PRICING = "pricing"
    SLA = "sla"
    REGION = "region"
    INTEGRATION = "integration"
    SYMPTOM = "symptom"
    CHANGE = "change"
    MIGRATION = "migration"
    HISTORICAL = "historical"
    SUPPORT_STATUS = "support_status"
    GENERAL = "general"
```

Examples:
- "What is our Sev1 alert acknowledgement SLA?" -> `CANONICAL` + `SLA`
- "What errors is OrderService returning?" -> `INCIDENT` + `SYMPTOM`
- "What changed before the incident?" -> `INCIDENT` + `CHANGE`
- "Is the legacy v1 collector protocol still available?" -> `CANONICAL` + `SUPPORT_STATUS`
- "How does the frontend consume backend APIs?" -> `INTEGRATION` + `INTEGRATION`

## Retrieval Pipeline

V3 uses a multi-stage pipeline.

### Stage 0: Query Analysis

Input:
- raw query;
- requesting agent state;
- pool context.

Output:
- `RetrievalIntent`
- `ExplorationMode`
- `AnswerRole`
- optional `QueryFacet`s
- optional canonical claim family hints

### Stage 1: Candidate Generation

V3 does not rely on one retrieval path.

It unions candidates from several generators:

1. Flat lexical retrieval
   Baseline BM25 / hybrid retrieval across the active pool.

2. Canonical-family retrieval
   For canonical queries, fetch all facts from the same normalized claim family.

3. Bridge retrieval
   For relay/integration queries, perform a controlled second hop through bridge
   concepts extracted from the first-pass candidates.

4. Facet harvest
   For true conjunctive queries, run per-facet retrieval.

5. Optional dense retrieval
   Only when embeddings exist and help recall.

This should be implemented as candidate harvest, not winner-take-all routing.

### Stage 2: Candidate Annotation

Each candidate is annotated with:
- lexical score;
- dense score;
- canonical-family match;
- bridge-hop provenance;
- facet coverage;
- answer-role compatibility;
- publisher prior;
- freshness / recency;
- redundancy signature.

### Stage 3: Truth Resolution

Before final ranking:
- canonical queries must collapse competing claims into one competition set;
- incident queries must preserve different evidence roles;
- assembly queries may keep multiple viewpoints, but should still deduplicate
  near-identical claims.

Canonical truth resolution must happen before the final top-k cutoff.

### Stage 4: Answer-Set Optimization

The objective is not "best documents".

The objective is:
- maximize answer-slot coverage;
- preserve necessary diversity across sources and roles;
- penalize redundancy;
- obey canonical truth constraints.

This is a set optimizer, not a simple reranker.

### Stage 5: Session-Safe Trust Update

Trust should not be directly inflated by repeated exposure in the same session.

V3 trust rules:
- publisher prior is slow-moving;
- retrieval-time local evidence confidence is query-local;
- per-query source credit is capped;
- optional: freeze trust within benchmark scenario execution;
- quick invalidations remain a strong negative signal.

## New / Changed Types

### `src/ai_knot/multi_agent/models.py`

Add:

```python
@dataclass(slots=True)
class QueryAnalysis:
    raw_query: str
    intent: RetrievalIntent
    exploration_mode: ExplorationMode
    answer_role: AnswerRole
    facets: tuple[QueryFacet, ...] = ()
    claim_family_hints: tuple[str, ...] = ()
    bridge_terms: tuple[str, ...] = ()


@dataclass(slots=True)
class CandidateEvidence:
    fact: Fact
    lexical_score: float = 0.0
    dense_score: float = 0.0
    final_score: float = 0.0
    publisher_prior: float = 0.0
    local_confidence: float = 0.0
    role_compatibility: float = 0.0
    canonical_match: float = 0.0
    bridge_match: float = 0.0
    facet_coverage: dict[str, float] = field(default_factory=dict)
    retrieval_sources: tuple[str, ...] = ()
    redundancy_key: str = ""


@dataclass(slots=True)
class AnswerSetResult:
    selected: list[CandidateEvidence] = field(default_factory=list)
    covered_slots: set[str] = field(default_factory=set)
    uncovered_slots: set[str] = field(default_factory=set)
    diagnostics: dict[str, float] = field(default_factory=dict)
```

Keep `QueryFacet`, but make it a reusable feature, not the center of the model.

## File-by-File Change Plan

### 1. `src/ai_knot/knowledge.py`

This remains the public API layer, but it should stop owning all retrieval logic.

Change:
- `_PoolQueryIntent` -> compatibility shim around V3 intent mapping.
- `_classify_pool_query()` -> replace with a wrapper that delegates to V3 analysis.
- `SharedMemoryPool.recall()` -> convert from "route then single path" to
  "analyze -> harvest candidates -> resolve truth -> optimize answer set".
- `SharedMemoryPool.get_trust()` -> keep as publisher prior only.
- `_extract_claim_key()` -> deprecate in favor of claim-family normalization.
- `_resolve_claim_conflicts()` -> move canonical resolution to V3 canonical module.
- keep `_pool_rerank()` only as a low-level utility if still useful.

New helper methods recommended inside `SharedMemoryPool`:

```python
def _analyze_query_v3(...)
def _collect_candidates_v3(...)
def _resolve_truth_v3(...)
def _optimize_answer_set_v3(...)
def _apply_session_credit_v3(...)
```

### 2. `src/ai_knot/multi_agent/router.py`

Repurpose from a simple intent router into a real query analyzer.

Change:
- `QueryShapeRouter.route()` should return `QueryAnalysis`, not only `RoutedPoolQuery`.
- split semantic intent from exploration mode.
- add answer-role classification.
- stop letting empty-querier state override semantic intent.

New methods:

```python
def classify_intent(...)
def classify_answer_role(...)
def classify_exploration_mode(...)
def analyze(...)
```

Recommendation:
- keep `route()` as a backward-compatible alias to `analyze()` during migration.

### 3. `src/ai_knot/multi_agent/facets.py`

Current planner is too dependent on comma lists and too aggressive about
classifying natural question forms as meta text.

Change:
- expand from clause splitting to slot extraction.
- support templates such as:
  - "What is X and what Y does it include?"
  - "How does A consume B?"
  - "What happens if X violates Y?"
- return answer slots, not just textual facets.

New methods:

```python
def extract_slots(...)
def decompose_question_template(...)
def decompose(...)
```

Important:
- keep single-facet output valid;
- do not require multi-facet decomposition for V3 to work.

### 4. `src/ai_knot/multi_agent/recall_service.py`

This file becomes the orchestrator for candidate generation.

Change:
- remove `_FACET_MIN_POOL_AGENTS` gating.
- stop requiring `intent == multi_source` as the only way into advanced retrieval.
- replace `_retrieve_per_facet()` with a union harvester.

New methods:

```python
def recall_v3(...)
def _harvest_flat(...)
def _harvest_canonical_family(...)
def _harvest_bridge(...)
def _harvest_facets(...)
def _merge_candidate_evidence(...)
```

Recommendation:
- keep the current V2 facet code as one harvester inside V3, not as the whole system.

### 5. `src/ai_knot/multi_agent/assembly.py`

Rename responsibility from "coverage-aware assembler" to answer-set optimization.

Change:
- replace `CoverageAwareAssembler` with `AnswerSetOptimizer`.
- objective should be slot coverage and marginal gain, not only facet presence.

New class:

```python
class AnswerSetOptimizer:
    def select(
        self,
        candidates: list[CandidateEvidence],
        *,
        top_k: int,
        answer_role: AnswerRole,
        canonical_mode: bool,
    ) -> AnswerSetResult: ...
```

Scoring should include:
- role coverage gain;
- source diversity;
- redundancy penalty;
- canonical family constraints;
- bridge utility.

### 6. `src/ai_knot/multi_agent/scoring.py`

Split generic scoring into separate concerns.

Keep:
- specificity scoring;
- near-miss detection.

Add:
- answer-role compatibility scorer;
- redundancy signature builder;
- local confidence scorer.

New methods:

```python
def role_compatibility(...)
def redundancy_key(...)
def local_confidence(...)
```

Important:
- publisher prior and local evidence confidence must be separate values.

### 7. `src/ai_knot/retriever.py`

This remains the low-level retriever, but it needs better candidate diagnostics.

Change:
- keep `search()` for compatibility;
- add a richer API returning full rankings and per-ranker components.

New methods:

```python
def search_full(...)
def rank_components(...)
```

Why:
- V3 needs candidate provenance, not only final fused score.

### 8. New file: `src/ai_knot/multi_agent/canonical.py`

Purpose:
- normalize unslotted claims into stable claim families;
- resolve canonical competition sets before final ranking.

Core responsibilities:
- map policy/support/status claims into normalized families;
- group competing facts;
- choose canonical winner for canonical queries;
- preserve multi-view evidence for non-canonical queries.

Suggested interface:

```python
class ClaimFamilyResolver:
    def family_for_fact(self, fact: Fact) -> str: ...
    def family_hints_for_query(self, query: str, answer_role: AnswerRole) -> tuple[str, ...]: ...
    def resolve(self, candidates: list[CandidateEvidence], *, canonical_mode: bool) -> list[CandidateEvidence]: ...
```

### 9. New file: `src/ai_knot/multi_agent/bridge.py`

Purpose:
- handle relay and integration questions that require a concept bridge.

Examples:
- frontend -> API gateway -> GraphQL client
- enterprise tier -> SLA
- violation -> service credits

Suggested interface:

```python
class BridgeRetriever:
    def extract_bridge_terms(...)
    def second_hop(...)
```

Safety rule:
- bridge retrieval should be a controlled second hop over top-N first-pass
  candidates, not an unrestricted graph walk.

### 10. New file: `src/ai_knot/multi_agent/roles.py`

Purpose:
- classify answer roles from query text.

Suggested interface:

```python
class AnswerRoleClassifier:
    def classify(self, query: str, *, intent: RetrievalIntent) -> AnswerRole: ...
```

This file directly addresses the `S19` failure mode.

## Trust Model Change

### Current Problem

Current trust is updated from retrieved results.

That creates:
- order dependence;
- winner-take-more feedback loops;
- contamination of later queries in a scenario.

### V3 Trust Rules

Publisher prior:
- computed from publish / invalidate / validated-use history;
- changes slowly.

Local confidence:
- computed per query from lexical fit, role fit, canonical fit, and bridge fit;
- never persisted as global trust.

Session credit:
- at most one bounded credit per source per query;
- optional scenario-level trust freeze for benchmark mode.

## Rollout Plan

### Phase 0: Structural Fixes

Minimal-risk changes:
- separate intent from exploration mode;
- cap trust credit per query;
- remove small-pool facet gate;
- broaden canonical conflict resolution entry conditions.

Expected impact:
- immediate improvement on `S8`, `S9`, and order sensitivity.

### Phase 1: Truth Plane

Add:
- claim-family normalization;
- canonical resolution before top-k.

Expected impact:
- strongest on `S9` and canonical policy/status questions.

### Phase 2: Bridge Retrieval

Add:
- bridge term extraction;
- controlled second hop.

Expected impact:
- strongest on `S16` and integration-style `S21` queries.

### Phase 3: Answer-Set Optimization

Add:
- slot-aware set optimizer.

Expected impact:
- strongest on `S8`, `S19`, `S21`, and large-pool fan-in.

## Benchmark Expectations

V3 should specifically improve:
- `S8 overlap_coverage`
- `S9 conflict_resolution`
- `S9 precision_at_3`
- `S16 layer_c_recall`
- `S16 chain_depth`
- `S19 evidence_precision`
- `S21 cross_agent_recall`
- `S21 assembly_depth`

V3 should also introduce new invariants:
- retrieval should be less sensitive to query order;
- warm-session and cold-session results should be closer;
- canonical queries should not surface stale competing claims in top-k;
- incident queries should separate symptom/change/migration roles.

## Tests to Add

Add unit tests for:
- semantic intent vs exploration mode separation;
- answer-role classification;
- claim-family normalization for unslotted policy docs;
- bridge retrieval on relay chains;
- set optimization preferring complementary evidence over redundant evidence;
- per-query trust credit caps.

Add benchmark-style tests for:
- query-order invariance;
- cold vs warm session invariance;
- canonical-family collapse;
- incident role precision.

## Summary

V2 was the right step for sparse large-pool assembly.

V3 is the step that turns multi-agent retrieval into a real architecture:
- semantics are classified explicitly;
- truth is resolved before ranking when needed;
- trust becomes a prior, not a popularity loop;
- answer sets are optimized as sets, not treated as a diversified top-k list.
