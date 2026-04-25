# Multi-Agent Memory V2 Plan

This document turns the 4-layer memory architecture into a concrete code plan
for `ai-knot`.

Primary goal:
- stop solving multi-agent assembly as flat top-k retrieval over one shared pool.

North-star outcome:
- preserve protocol correctness from current MA scenarios;
- improve sparse fan-in retrieval and assembly quality at large scale;
- make "who knows what" and "what the team has learned" first-class memory layers.

## Why V2

Current strengths:
- private memory is solid;
- slot-addressing and temporal versions are solid;
- shared pool + trust + CAS are strong protocol primitives.

Current gap:
- `SharedMemoryPool.recall()` is still the main retrieval plane for both:
  - raw shared facts;
  - organizational knowledge about expert agents;
  - emergent team-level reusable insights.

That works for canonical truth and small fan-in, but breaks under scenarios like
`S26`, where the system needs to:
- decompose the query into facets;
- route each facet toward likely expert agents;
- assemble a set of facts with coverage across facets;
- suppress near-miss overview facts.

## 4 Memory Layers

### 1. Private Memory

Scope:
- per-agent `episodic`, `procedural`, `semantic`.

Owned by:
- `KnowledgeBase`

Primary use:
- local recall;
- user-specific truth;
- procedural preferences;
- short-term episodic state.

### 2. Shared Fact Pool

Scope:
- raw published cross-agent facts.

Owned by:
- `SharedMemoryPool`

Primary use:
- direct cross-agent retrieval;
- slotted truth sharing;
- evidence exchange.

### 3. Agent Expertise Memory

Scope:
- which agents are strong for which domains, tags, concepts, and task facets.

Owned by:
- new `AgentExpertiseIndex`

Primary use:
- route-before-retrieve for `MULTI_SOURCE`;
- reduce search fan-out;
- distinguish "correct domain" from "correct source agent".

### 4. Team Insight Memory

Scope:
- reusable team-level summaries, bridges, lessons, and past successful
  multi-agent assemblies.

Owned by:
- new `TeamInsightStore`

Primary use:
- avoid re-solving the same multi-hop synthesis repeatedly;
- preserve cross-agent patterns that are more abstract than raw facts.

## Package Layout

New package:

```text
src/ai_knot/multi_agent/
  __init__.py
  models.py
  router.py
  facets.py
  expertise.py
  scoring.py
  assembly.py
  insights.py
  recall_service.py
  shared_pool.py
```

Existing files that stay but change responsibility:

```text
src/ai_knot/knowledge.py
src/ai_knot/retriever.py
src/ai_knot/types.py
tests/test_shared_pool.py
tests/eval/benchmark/backends/ai_knot_multi_agent_backend.py
```

## File-by-File Plan

### `src/ai_knot/multi_agent/models.py`

Purpose:
- shared dataclasses for the multi-agent retrieval pipeline.

Classes:

```python
@dataclass(slots=True)
class QueryFacet:
    facet_id: str
    text: str
    tokens: tuple[str, ...]
    facet_type: str  # "entity", "domain", "constraint", "time", "general"
    weight: float = 1.0


@dataclass(slots=True)
class RoutedPoolQuery:
    raw_query: str
    intent: str
    facets: tuple[QueryFacet, ...]
    topic_channel: str = ""
    use_expertise_routing: bool = False
    use_insight_boost: bool = False
    use_llm_expansion: bool = False


@dataclass(slots=True)
class CandidateFact:
    fact: Fact
    base_score: float
    facet_scores: dict[str, float]
    specificity_score: float
    near_miss_penalty: float
    expertise_boost: float


@dataclass(slots=True)
class AssemblyResult:
    selected: list[CandidateFact]
    covered_facets: set[str]
    uncovered_facets: set[str]
    coverage_score: float
```

Notes:
- keep these types local to the new package;
- do not overload `Fact` with planner-only fields.

### `src/ai_knot/multi_agent/router.py`

Purpose:
- query-shape routing for pool retrieval.

Class:

```python
class QueryShapeRouter:
    def route(
        self,
        query: str,
        *,
        requesting_agent_id: str,
        active_facts: list[Fact],
        requesting_agent_fact_count: int,
        topic_channel: str = "",
    ) -> RoutedPoolQuery: ...
```

Responsibilities:
- reuse current intent classification rules;
- decide whether the query is:
  - `ENTITY_LOOKUP`
  - `INCIDENT`
  - `BROAD_DISCOVERY`
  - `MULTI_SOURCE`
  - `GENERAL`
- switch on facet decomposition only for `MULTI_SOURCE`;
- enable optional low-coverage semantic boost only for suitable intents.

Migration:
- move `_classify_pool_query()` logic out of `knowledge.py` into this file;
- keep a thin compatibility wrapper in `knowledge.py` during transition.

### `src/ai_knot/multi_agent/facets.py`

Purpose:
- facet decomposition for conjunctive multi-source queries.

Class:

```python
class ConjunctiveFacetPlanner:
    def decompose(self, routed: RoutedPoolQuery) -> tuple[QueryFacet, ...]: ...
```

Responsibilities:
- split requests like "integrate X, Y, and Z";
- detect conjunctions and comma-separated technical facets;
- extract 2-5 independent facet queries;
- normalize facet tokens with the shared tokenizer;
- stay algorithmic by default.

Independence guardrails:
- do not treat every conjunction as multi-facet;
- candidate facets count as independent only when each clause contains enough
  content-bearing tokens after stopword/common-verb filtering;
- explanatory tails like "how does it work", "why is it useful", "what is X and
  how does it work" should stay single-facet by default;
- ambiguous decompositions fall back to the original query rather than forcing
  synthetic facets.

Suggested Phase-1 heuristic:
- split only if each candidate clause has at least 2-3 non-trivial tokens;
- require domain-bearing terms in each clause, not just verbs/prepositions;
- reject decomposition when one clause is obviously meta-explanatory rather than
  an independent retrieval target.

Optional extension:
- `LLMFacetExpander` can be added later, but only as a gated fallback.

### `src/ai_knot/multi_agent/expertise.py`

Purpose:
- build and query agent expertise memory.

Classes:

```python
@dataclass(slots=True)
class ExpertiseProfile:
    agent_id: str
    domains: Counter[str]
    tags: Counter[str]
    canonical_terms: Counter[str]
    useful_hits: int
    published_facts: int
    trust_score: float


@dataclass(slots=True)
class ExpertiseHit:
    agent_id: str
    score: float
    matched_terms: tuple[str, ...]


class AgentExpertiseIndex:
    def build(self, active_facts: list[Fact], get_trust: Callable[[str], float]) -> None: ...
    def top_agents_for_facet(self, facet: QueryFacet, *, top_n: int = 8) -> list[ExpertiseHit]: ...
```

Phase-1 implementation:
- derived in memory from active pool facts;
- no storage migration required.

Cache lifecycle:
- build lazily on the first routed `MULTI_SOURCE` recall;
- cache the built index together with a shared-pool frontier/version marker;
- invalidate and rebuild when the active pool changes via publish, CAS
  supersession, promotion, or pool GC;
- do not rebuild on every recall.

Phase-2 implementation:
- optional persisted snapshots in a dedicated namespace if needed.

Responsibilities:
- convert raw shared facts into "who is likely useful for this facet";
- score by tags, canonical terms, fact utility, and trust;
- route retrieval to smaller candidate agent sets before final assembly.

### `src/ai_knot/multi_agent/scoring.py`

Purpose:
- non-retriever scoring helpers used after candidate generation.

Classes:

```python
class SpecificityScorer:
    def score(self, fact: Fact) -> float: ...


class NearMissDetector:
    def penalty(self, fact: Fact) -> float: ...


class DiversityPolicy:
    def per_agent_cap(self, *, top_k: int) -> int: ...
    def per_domain_cap(self, *, top_k: int) -> int: ...
```

Responsibilities:
- reward implementation-specific facts;
- penalize overview-like facts;
- cap duplicates from the same agent and the same domain cluster;
- remain model-free and deterministic.

Suggested Phase-1 near-miss algorithm:
- start with generic cue phrases:
  - `"overview"`
  - `"conceptual level"`
  - `"without implementation specifics"`
  - `"general introduction"`
- compute technical-density as a deterministic proxy for shard specificity;
- initial formula can be:
  - `technical_density = technical_token_count / total_token_count`
  - where `technical_token_count` is based on non-stopword, domain-bearing, or
    corpus-rare tokens;
- increase penalty when:
  - generic cue phrases are present;
  - technical density is low;
  - the fact looks summary-like rather than implementation-like.

Important nuance:
- use this as a ranking penalty, not a hard filter in Phase 1;
- avoid relying only on "unique token ratio", because random rare markers can be
  noisy without also checking generic-summary cues.

Important:
- this is where we solve the limitation of plain monopoly breaking;
- `per-agent cap` alone is not enough for `S26`, because many different agents
  can still represent the same facet/domain.

### `src/ai_knot/multi_agent/assembly.py`

Purpose:
- coverage-aware selection of the final top-k.

Class:

```python
class CoverageAwareAssembler:
    def assemble(
        self,
        *,
        candidates_by_facet: dict[str, list[CandidateFact]],
        top_k: int,
    ) -> AssemblyResult: ...
```

Selection objective:
- maximize facet coverage;
- maximize source diversity;
- maximize specificity;
- minimize redundancy;
- minimize near-miss overviews.

Implementation:
- greedy max-coverage / set-cover style selection is enough for V1;
- no need for expensive global optimization at first.

This is the heart of the `S26` fix.

### `src/ai_knot/multi_agent/insights.py`

Purpose:
- team insight memory.

Classes:

```python
@dataclass(slots=True)
class TeamInsight:
    insight_id: str
    summary: str
    supporting_fact_ids: tuple[str, ...]
    supporting_agents: tuple[str, ...]
    tags: tuple[str, ...]
    reuse_count: int = 0


class TeamInsightStore:
    def remember(self, insight: TeamInsight) -> None: ...
    def retrieve(self, query: str, *, top_k: int = 5) -> list[TeamInsight]: ...
    def promote_from_assembly(self, result: AssemblyResult) -> list[TeamInsight]: ...
```

Phase-1 implementation:
- in-memory only, derived from successful assemblies.

Phase-2 implementation:
- persist in a dedicated namespace or dedicated storage API.

Use carefully:
- do not store every answer as an insight;
- only promote stable, repeated, high-value assemblies.

### `src/ai_knot/multi_agent/recall_service.py`

Purpose:
- orchestrate the full pool retrieval pipeline.

Class:

```python
class SharedPoolRecallService:
    def recall(
        self,
        query: str,
        *,
        requesting_agent_id: str,
        active_facts: list[Fact],
        top_k: int,
        topic_channel: str = "",
        query_vector: list[float] | None = None,
    ) -> list[tuple[Fact, float]]: ...
```

Pipeline:
1. route query;
2. decompose facets if needed;
3. query team insights if enabled;
4. build expertise shortlist;
5. retrieve facet candidates from pool;
6. optionally run facet-local PRF or facet-local expansion;
7. apply specificity and near-miss scoring;
8. run coverage-aware assembly;
9. return final `(Fact, score)` pairs.

This service should own complex retrieval logic instead of `knowledge.py`.

PRF policy for `MULTI_SOURCE`:
- do not use one global PRF expansion over the whole mixed query;
- use per-facet PRF instead:
  - each facet gets its own top-3 feedback docs;
  - expansion terms are derived only from that facet's candidate set;
- require light guardrails before PRF:
  - minimum lexical relevance;
  - minimum source diversity;
  - avoid PRF when initial facet hits are dominated by near-miss overview facts.

Rationale:
- global PRF over mixed facets can reinforce the wrong cluster and collapse
  coverage;
- facet-local PRF is much safer for sparse assembly.

### `src/ai_knot/multi_agent/shared_pool.py`

Purpose:
- home for `SharedMemoryPool` after extraction from `knowledge.py`.

Class:

```python
class SharedMemoryPool:
    ...
```

Responsibilities retained:
- register agents;
- publish facts;
- sync deltas;
- trust accounting;
- promotion and pool GC.

Responsibilities removed:
- direct ownership of the complex query planner.

Instead:
- `SharedMemoryPool.recall()` delegates to `SharedPoolRecallService`.

## Changes To Existing Files

### `src/ai_knot/knowledge.py`

Target state:
- keep `KnowledgeBase` public API;
- remove most shared-pool-specific planner logic;
- re-export `SharedMemoryPool` from `multi_agent.shared_pool` for compatibility.

What moves out:
- query intent classification;
- monopoly breaker internals;
- multi-source routing policy;
- assembly logic.

What stays:
- private KB learn/recall;
- storage access;
- decay and extraction orchestration.

### `src/ai_knot/retriever.py`

Keep:
- BM25 / Dense / Hybrid retrievers;
- PRF;
- low-level scoring.

Do not force it to solve assembly.

Minimal additions:
- optional helper to retrieve larger candidate pools efficiently;
- optional facet-aware helper if needed, but keep it generic;
- add helper support for caller-scoped PRF so `MULTI_SOURCE` can use
  facet-local feedback rather than one global PRF pass.

PRF rule:
- for standard recall, current global PRF behavior can stay;
- for `MULTI_SOURCE`, PRF must be driven per facet by the orchestration layer,
  not implicitly over the full mixed query.

### `src/ai_knot/types.py`

Preferred approach:
- no major expansion of `Fact` for planner-only metadata.

Allowed small additions later:
- none required for Phase 1.

Rationale:
- keep organizational memory metadata out of core fact shape until clearly stable.

### `tests/eval/benchmark/backends/ai_knot_multi_agent_backend.py`

Add flags:

```python
class AiKnotMultiAgentBackend(...):
    def __init__(
        ...,
        enable_embeddings: bool = False,
        enable_facet_planner: bool = True,
        enable_expertise_routing: bool = True,
        enable_team_insights: bool = False,
    ) -> None: ...
```

Purpose:
- benchmark old vs new behavior behind explicit switches.

## Test Plan

New unit tests:

```text
tests/test_multi_agent_router.py
tests/test_multi_agent_facets.py
tests/test_multi_agent_expertise.py
tests/test_multi_agent_scoring.py
tests/test_multi_agent_assembly.py
tests/test_multi_agent_insights.py
```

New benchmark scenarios:

```text
tests/eval/benchmark/scenarios/s27_expertise_routing.py
tests/eval/benchmark/scenarios/s28_insight_reuse.py
tests/eval/benchmark/scenarios/s29_facet_coverage.py
```

Existing scenarios to guard:
- `S10`, `S11`, `S13`, `S17`, `S20`, `S25`: no regression allowed;
- `S21`, `S24`: must improve or stay flat;
- `S26`: primary target scenario.

## Rollout Plan

### Step 1. Extract shared-pool planner code

Create:
- `multi_agent/models.py`
- `multi_agent/router.py`
- `multi_agent/recall_service.py`
- `multi_agent/shared_pool.py`

Keep behavior unchanged initially.

### Step 2. Add facet decomposition

Create:
- `multi_agent/facets.py`
- `multi_agent/assembly.py`

Turn on only for `MULTI_SOURCE`.

### Step 3. Add specificity and near-miss scoring

Create:
- `multi_agent/scoring.py`

Wire into the new assembler.

### Step 4. Add facet-local PRF hooks

Add:
- caller-scoped PRF support in `retriever.py`
- facet-local expansion logic in `recall_service.py`

Keep it gated and deterministic.

### Step 5. Add expertise memory

Create:
- `multi_agent/expertise.py`

Keep it derived and in-memory first.

### Step 6. Add team insight memory

Create:
- `multi_agent/insights.py`

Enable behind a flag.

## Metrics Targets

Primary targets:
- `S26 target_shard_recall_at_1000 >= 0.45` after facet planning;
- `S26 target_shard_recall_at_1000 >= 0.65` after expertise routing;
- `S26 distractor_rate_at_1000 <= 0.60` after specificity scoring;
- `S26 all_shards_covered_at_1000 >= 0.20`, then `>= 0.40`.

Guardrail targets:
- no regressions on protocol correctness scenarios;
- no meaningful regression on `ENTITY_LOOKUP` latency.

## What Not To Do

- do not solve `S26` only by retuning BM25 weights;
- do not make LLM expansion mandatory;
- do not add global novelty gating to pool publish in Phase 1;
- do not overload `Fact` with every planner concern;
- do not leave this logic inside one growing `knowledge.py`.

## Recommended First Implementation Slice

If we want the highest impact with the least architectural risk, implement in this order:

1. `models.py`
2. `router.py`
3. `facets.py`
4. `assembly.py`
5. `scoring.py`
6. `recall_service.py`
7. `shared_pool.py` extraction
8. `expertise.py`
9. `insights.py`

That gives:
- immediate `S26` attack path;
- minimal disruption to private memory;
- a clean runway for the full 4-layer architecture.
