# ai-knot v2 — Full Product Kernel with Metric Gates

## Не MVP. Не research prototype. Не benchmark hack.

**Дата:** 2026-04-24
**Источники:** `research/rcmt_program_ru.md`, `research/invariant_witness_theory_program.md`, `research/memory_substrate_v1_article_and_plan_20260424.md`

---

## 0. Manifest

```text
ai-knot v2 is not a retrieval system and not an LLM wrapper.

It is a deterministic memory kernel that transforms history into typed,
temporally scoped, causally linked, risk-aware memory atoms, then reconstructs
bounded evidence packs through dependency closure and reader-budget planning.

LLMs may assist extraction or final answer rendering in optional modes,
but the memory core must remain auditable, reproducible, and independently measurable.
```

Translation:

```text
ai-knot v2 — детерминированное ядро памяти:
история → типизированные атомы → временная/каузальная/рисковая структура
       → evidence planner → объяснимый recall.

Метрики достигаются повышением плотности правильных доказательств
в ограниченном reader-бюджете, а не расширением контекста и не LLM-magic.
```

**Три железных принципа:**

1. **Full product kernel from day one.** Полная схема, полный pipeline, полное API — с Sprint 1. Точность отдельных модулей растёт по спринтам, но архитектурная форма финальная сразу. **Никаких schema-rewrite-ов** в середине пути.
2. **No LLM in product memory core.** LLM — внешний слой (extraction-oracle опционально, answer/judge только в bench). Memory operations (write/read/consolidate/forget/dependency-closure/evidence-planning) — **детерминированно**.
3. **Метрики ≠ только LOCOMO.** Multi-metric gates: финальный answer-score не растёт ценой ухудшения evidence-метрик. Иначе «метрики есть, продукта нет».

---

## 1. LLM Policy (явно запретное и явно разрешённое)

### 1.1 Product default

```text
deterministic memory core, no LLM in memory operations.

write/read/forget/consolidate/dependency-closure/evidence-planning =
  rule-based + structural + temporal + risk-class operations,
  fully reproducible, auditable, embeddable on-prem без сетевой связи.
```

### 1.2 Optional modes (изолированы, явно включаемые)

| Mode | Назначение | Включается через | Влияние на core |
|---|---|---|---|
| `llm_oracle_mode` | extraction-ablation, ceiling analysis, benchmark experiments | `--llm-oracle gpt-4o-mini` | замещает `synth/oracle_regex.py` на `synth/oracle.py` |
| `llm_answer_mode` | external answer rendering для bench | `--llm-answerer gpt-4o-mini` | только в `bench/`, не в memory |
| `llm_judge_mode` | benchmark evaluation | `--llm-judge gpt-4o-mini` | только в `bench/`, не в memory |

### 1.3 Forbidden

```text
- Making LLM extraction mandatory for ai-knot memory correctness.
- Hiding memory quality inside LLM reasoning.
- Calling LLM from any module under src/ai_knot_v2/{core,ops,store,api}/.
- Using LLM as the source of dependency / temporal / identity decisions.
```

Архитектурное правило: `grep -r "openai\|anthropic\|gpt\|claude" src/ai_knot_v2/{core,ops,store,api}/` должен возвращать **пустой** результат. CI гарантирует это через `tests/architecture/test_no_llm_in_core.py`.

### 1.4 Costs (на 233-question 10-conv LOCOMO)

| Конфигурация | LM-вызовов | $ (gpt-4o-mini) |
|---|---:|---:|
| **Product default** (deterministic core, bench-only LLM) | ~470 (answer + judge) | ~$0.5 |
| `llm_oracle_mode` (extraction LLM, остальное детерм.) | ~1170 | ~$1 |
| Старый v0.9.5 (для сравнения) | ~470 + embedding-API | ~$0.5 |

---

## 2. MemoryAtom — Full Schema, Growing Precision

**Полная схема — с Sprint 1. Никакого позднего schema-rewrite.** Каждое поле существует с самого начала; некоторые изначально используют deterministic placeholder rules и эволюционируют по спринтам к полной точности.

```python
# src/ai_knot_v2/core/atom.py
@dataclass(frozen=True, slots=True)
class MemoryAtom:
    # === Идентификация ===
    atom_id: str                                  # ULID, immutable
    agent_id: str
    user_id: str | None

    # === Каузальная структура ===
    variables: tuple[str, ...]                    # V_α
    causal_graph: tuple[tuple[str, str], ...]     # рёбра parent → child
                                                   #  Sprint 1: shallow dependencies (явные refs)
                                                   #  Sprint 5+: typed SCM fragment с inferred-edges
    kernel_kind: Literal["point","categorical","structural"]
    kernel_payload: dict

    intervention_domain: tuple[str, ...]

    # === Констрейнт ===
    predicate: str                                # canonical relation
    subject: str                                  # canonical entity reference (через groupoid)
    object_value: str | None
    polarity: Literal["pos","neg"]

    # === Tri-temporal ===
    valid_from: int | None                         # epoch-seconds; None = always
    valid_until: int | None                        # None = open-ended
    observation_time: int                          # когда увидели
    belief_time: int                               # когда назначили credence
    granularity: Literal["instant","day","month","year","interval"]

    # === Identity ===
    entity_orbit_id: str
                                                   #  Sprint 1: canonical entity_id (string match)
                                                   #  Sprint 3+: groupoid transport с holonomy detection
    transport_provenance: tuple[str, ...]

    # === Dependency boundary ===
    depends_on: tuple[str, ...]                    # ∂α
    depended_by: tuple[str, ...]                   # обратные ссылки

    # === Risk / protection ===
    risk_class: Literal["safety","identity","finance","legal","medical",
                        "commitment","scheduling","preference","ambient"]
    risk_severity: float                          # D_α ∈ [0,1]
    regret_charge: float
                                                   #  Sprint 1: risk-based heuristic (D_α × 1[has-action-effect])
                                                   #  Sprint 5+: full IWT charge через action_calculus
    irreducibility_score: float
                                                   #  Sprint 1: simple dominance rule
                                                   #  Sprint 3b: full Action Calculus dominance check
    protection_energy: float                      # E_α — эволюционирует ODE

    # === Action fingerprint (вычисляется на WRITE) ===
    action_affect_mask: int                       # bitmap: на какие action-classes влияет атом

    # === Credence + provenance ===
    credence: float
    evidence_episodes: tuple[str, ...]            # raw-episode pointers
    synthesis_method: Literal["regex","llm","fusion","oracle","manual"]
    validation_tests: tuple[str, ...]
    contradiction_events: tuple[str, ...]
```

**Правило эволюции:** placeholders в Sprint 1 заменяются полными реализациями в Sprint 3-5. **Schema не меняется**.

---

## 3. Архитектура (директории)

```
src/ai_knot_v2/
├── core/                       # 100% детерминированно, no LLM imports
│   ├── atom.py                 # MemoryAtom (полная schema)
│   ├── library.py              # AtomLibrary с typed-индексами
│   ├── episode.py              # RawEpisode (immutable)
│   ├── evidence.py             # EvidenceSpan, EvidencePack
│   ├── dependency.py           # DependencyEdge, dependency-closure
│   ├── groupoid.py             # EntityGroupoid + holonomy
│   ├── temporal.py             # Allen interval algebra + survival hazard
│   ├── risk.py                 # RiskClass taxonomy
│   ├── action_calculus.py      # ★ Action Fingerprint Calculus
│   ├── action_taxonomy.py      # ★ action-classes per domain
│   ├── probe_templates.py      # ★ probe-queries per risk-class
│   ├── templates/              # ★ YAML domain-templates
│   │   ├── medical.yaml scheduling.yaml preference.yaml identity.yaml
│   │   └── (finance.yaml legal.yaml — позже)
│   ├── provenance.py           # AuditTrail
│   └── types.py                # Query, Intervention, RecallQuery, RecallResult, ReaderBudget
├── ops/                        # детерминированные операции
│   ├── atomizer.py             # deterministic write-path (regex + rules)
│   ├── write.py                # WRITE: atomize → coverage → irreducibility → risk-override → normalize
│   ├── read.py                 # READ: intervention → submodular → dependency-closure → evidence-pack
│   ├── planner.py              # ★ Evidence Planner (reader_cost, reduction_score, utility)
│   ├── consolidate.py          # interval-merge + categorical refactoring
│   └── forget.py               # protection-energy ODE
├── store/                      # тонкий sqlite-слой
│   ├── sqlite.py               # stdlib sqlite3 (без ORM до stable metrics)
│   ├── schema.py               # SQL DDL + migrations (текстом, без Alembic)
│   └── _sql/                   # raw SQL files
├── synth/                      # ИЗОЛИРОВАННЫЙ optional LLM-слой
│   ├── oracle.py               # LLM-extraction (опц., llm_oracle_mode)
│   ├── prompts/                # YAML/Jinja
│   └── (никаких других LLM-вызовов нигде в коде)
├── api/                        # public surface — С SPRINT 4
│   ├── product.py              # MemoryAPI: learn/recall/explain/trace/inspect
│   ├── sdk.py                  # Python SDK (pydantic v2)
│   ├── cli.py                  # ai-knot CLI
│   └── mcp.py                  # MCP server (Sprint 22+)
├── bench/                      # benchmark adapters
│   ├── locomo.py               # adapter к aiknotbench
│   ├── synthetic.py            # 700-session synthetic для metrics-harness
│   ├── longmemeval.py beam.py memoryarena.py
│   ├── scorecard.py            # ★ multi-metric scorecard
│   └── rsb/                    # Reconstruction-Sufficiency Benchmark (новый)
└── tests/
    ├── unit/ integration/ e2e/
    └── architecture/           # ★ test_no_llm_in_core, test_schema_stability
```

---

## 4. Sprint Roadmap

### Sprint 0 — Greenfield Skeleton [DONE]

- `feat/v2-product-kernel` branch
- Skeleton directories + `__init__.py` + `py.typed`
- `pyproject.toml` updated (v2 package + pydantic dep + mypy + pytest)
- `src/ai_knot_v2/CLAUDE.md` — architectural invariants
- `tests/architecture/test_no_llm_in_core.py` — CI gate
- Research docs: `aiknot_v2_product_kernel_plan.md` + `implementation_workflow_claude.md`
- Draft PR

### Sprint 1 — Full Product Schema [TC: M]

- `core/types.py`: Query, Intervention, RecallQuery, RecallResult, ReaderBudget, ContradictionEvent, ActionPrediction
- `core/atom.py`: **полная** MemoryAtom (см. §2)
- `core/episode.py`: RawEpisode (immutable, frozen)
- `core/evidence.py`: EvidenceSpan, EvidencePack
- `core/dependency.py`: DependencyEdge
- `core/library.py`: AtomLibrary с typed-индексами + dependency-closure stub
- `tests/unit/test_*.py`: schema-сериализация, immutability, schema-stability gate
- `mypy --strict src/ai_knot_v2/core` зелёный
- **Acceptance:** все типы экспортируются, schema-tests проходят, mypy чисто

### Sprint 2 — Store + Provenance [TC: M]

- `store/schema.py`: SQL DDL — episodes, atoms, evidence, dependencies, action_scores, audit_trail
- `store/sqlite.py`: stdlib `sqlite3` wrapper с typed-row-mappers
- `core/provenance.py`: AuditTrail
- API skeleton: `trace(atom_id) -> AuditTrail`, `explain(answer_id) -> Explanation`
- `tests/integration/test_sqlite_roundtrip.py`
- **Acceptance:** ingest → SQLite → читать обратно идентичные атомы

### Sprint 3 — Deterministic Write Path [TC: L]

- `ops/atomizer.py`: regex + temporal + entity + risk + dependency + protection_score
- `ops/write.py`: atomize → coverage → irreducibility → risk-override → normalize
- `core/temporal.py`: Allen interval algebra (13 relations)
- `core/groupoid.py`: EntityGroupoid (Sprint 1: canonical-id)
- `core/risk.py`: RiskClass taxonomy + 9 declared classes
- **Acceptance:** на 1 LOCOMO conv — атомы ≥ 70% gold-evidence-coverage (sanity, не bench)

### Sprint 3b — Action Fingerprint Calculus [TC: M] ★

- `core/action_taxonomy.py`: ActionClass enum (medical / scheduling / preference / identity)
- `core/action_calculus.py`: compute_action_affect_mask, canonical_action_signature, action_distance, predict_action
- `core/probe_templates.py` + 4 YAML в `core/templates/`
- `core/groupoid.py`: holonomy detection
- `ops/irreducibility.py`: structural-enumeration witness builder via action_calculus
- **Acceptance gate:** synthetic-suite ≥ 95%

### Sprint 4 — Deterministic Read Path + SDK + CLI [TC: L]

- `ops/read.py`: extract_intervention → select_candidates → submodular-greedy → dependency-closure → RecallResult
- `api/product.py`: MemoryAPI (learn / recall / explain / trace / inspect_memory)
- `api/sdk.py`: pydantic v2 DTOs
- `api/cli.py`: `ai-knot learn|recall|explain|trace|inspect-memory`
- **Acceptance:** working CLI demo; e2e smoke

### Sprint 5 — Evidence Planner [TC: L] ★

- `ops/planner.py`: reader_cost, reduction_score, utility, plan_evidence_pack, handle_contradictions
- **Acceptance:** evidence-pack-density ≥ 0.7 на synthetic 700-session

### Sprint 6 — Metrics Harness + 1st BG-run [TC: L]

- `bench/scorecard.py`: 8 internal evidence-метрик
- `bench/synthetic.py`: 700-session generator (medical domain)
- `bench/locomo.py`: adapter к aiknotbench
- 1st 2-conv LOCOMO BG-run (3 parallel: legacy v0.9.5 / v2 det / v2 + llm_oracle)
- **Acceptance:** cat1 ≥ 35%

### Sprints 7-13 — Iteration to multi-metric gate [TC: M each]

- Sprint 7: atomizer fixes → cat1 ≥ 40%
- Sprint 8: forget + consolidate; memory-volume sublinear
- Sprint 9-10: cat1 ≥ 50%, evidence-utility-density growing
- Sprint 11: tri-temporal activation in planner
- Sprint 12: identity-holonomy + LongMemEval temporal ≥ 55%
- Sprint 13: reader-budget sweep

### Sprint 14 — Mid-program Gates F1, A0, A1 [TC: L + BG ~6h]

- Full 10-conv LOCOMO (BG-1)
- F1-ablation: 4 parallel runs (BG-2)
- A0-ablation: det-oracle vs llm_oracle (BG-3)
- A1 NEW: LLM-dependency-leak check (BG-4)
- **GATE-F1:** cat1 ≥ 55% on 10-conv + multi-metric
- **GATE-A0:** LLM vs regex gap < 5pp
- **GATE-A1:** det vs LLM gap ≤ 10pp → deterministic = production default

### Sprints 15-17 — RSB v1

- `bench/rsb/generator.py` (medical, scheduling domains)
- `bench/rsb/scorer.py`
- 2 scenarios YAML

### Sprints 18-20 — BG experiment runs (E1, E2, E3)

E1 rare-critical survival / E2 phase transition / E3 causal dependency.

### Sprints 21-23 — Production polish

- Sprint 21: Postgres backend (`store/postgres.py`)
- Sprint 22: MCP server (`api/mcp.py`)
- Sprint 23: Docker + mkdocs-material docs

### Sprints 24-30 — RSB completion + paper + OSS release

- Sprint 24-25: RSB final scenarios
- Sprint 26-27: workshop paper
- Sprint 28: legacy rename (`src/ai_knot/` → `src/ai_knot_legacy/`); v2 → main package
- Sprint 29-30: OSS release (Apache 2.0) + announcement

---

## 5. Целевые метрики

### 5.1 Внешние (бенчмарки)

| Sprint | Метрика | Цель |
|---|---|---:|
| 6 | LOCOMO 2-conv cat1 | ≥ 35% |
| 10 | LOCOMO 2-conv cat1 | ≥ 50% |
| 12 | LongMemEval temporal | ≥ 55% |
| 14 | LOCOMO 10-conv cat1 (★ MAIN) | ≥ 55% |
| 14 | LOCOMO 10-conv cat1-4 | ≥ 70% |
| 18 | RSB-Rare RWAA | ≥ 0.85 |
| 19 | E2 phase-transition | clear inflection at B*∈[3%,15%] |
| 20 | MemoryArena CPS depth≤4 | ≥ 0.70 |
| 25 | LOCOMO 10-conv cat1 final | ≥ 58% |

### 5.2 Внутренние evidence-метрики (каждый sprint после Sprint 6)

| Метрика | Threshold |
|---|---:|
| `RequiredAtomRecall@Budget` | ≥ 0.85 |
| `GoldEvidenceCoverage@Budget` | ≥ 0.80 |
| `DependencyClosureRecall` | ≥ 0.95 |
| `TemporalValidityAccuracy` | ≥ 0.90 |
| `ContextDilutionRate` | ≤ 0.15 |
| `UnsafeOmissionRate` | ≤ 0.05 |
| `EvidenceUtilityDensity` | growing |
| `NoiseAtomRatio` | ≤ 0.20 |

### 5.3 Multi-metric gate-formula

```text
ACCEPT change iff:
   cat1 monotonic up (or stable если targeting другую метрику)
   AND GoldEvidenceCoverage@Budget up
   AND ContextDilutionRate not up
   AND UnsafeOmissionRate not up
   AND DependencyClosureRecall not down
   AND test_no_llm_in_core passes
   AND no LOCOMO-specific code/keywords added
REJECT и REVERT иначе.
```

---

## 6. Stop-conditions / Risk register

| Риск | Условие | Действие |
|---|---|---|
| LLM dependency leak | v2-core теряет >10pp без LLM oracle | Classify llm_oracle как non-product mode |
| Benchmark overfit | answer-score ↑ но evidence-метрики ↓ | Reject even if cat1 higher; revert |
| Cat1 застрял <50% к Sprint 10 | 3 sprint без прогресса | 3 parallel Plan-agents |
| Schema drift | mypy fails / schema-snapshot fails | HARD STOP, revert |
| test_no_llm_in_core fails | LLM-import в core/ops/store/api | HARD STOP, delete import |
| LOCOMO-specific код | grep находит LOCOMO-keywords в src/ | REVERT |
| Все gate провалены (F1,F2,F3) | Sprint 14 | Dead-end: RSB + product schema как standalone |

---

## 7. Что не делает Claude (зона пользователя)

| Действие | Sprint |
|---|---|
| Бюджет на RSB annotators | 15-17 |
| LLM-провайдер default (OpenAI vs Anthropic) | 4 |
| Postgres deployment infrastructure | 21 |
| OSS license + business model | 28-30 |
| Production deployment (cloud) | 23+ |
| Code review больших архитектурных PR | каждый GATE-* |

---

## 8. Decision-points

| Когда | Что | Default если молчишь |
|---|---|---|
| Sprint 4 | Default LLM provider в bench | `gpt-4o-mini` (OpenAI) |
| Sprint 6 | Synthetic-domain первый | `medical` |
| Sprint 14 | Multi-metric gate failed | revert |
| Sprint 15 | RSB annotator-бюджет | RSB-Lite синтетика |
| Sprint 21 | Postgres сейчас или later | Sprint 21 |
| Sprint 28 | Renaming legacy | подтверди вручную |

---

## 9. Порядок создания файлов

```
Sprint 0:  pyproject.toml edit, skeleton, CLAUDE.md, test_no_llm_in_core, research docs
Sprint 1:  core/types.py → atom.py → episode.py → evidence.py → dependency.py → library.py
Sprint 2:  store/schema.py → store/sqlite.py → core/provenance.py
Sprint 3:  core/temporal.py → core/groupoid.py → core/risk.py → ops/atomizer.py → ops/write.py
Sprint 3b: core/action_taxonomy.py → core/action_calculus.py → core/probe_templates.py
           → core/templates/{medical,scheduling,preference,identity}.yaml
           → ops/irreducibility.py
Sprint 4:  ops/read.py → api/product.py → api/sdk.py → api/cli.py
Sprint 5:  ops/planner.py (★) → core/evidence.py extend → ops/read.py update
Sprint 6:  bench/scorecard.py → bench/synthetic.py → bench/locomo.py → 1st BG-run
Sprint 7-13: iteration на existing files
Sprint 14: GATE F1+A0+A1
Sprint 15-17: bench/rsb/generator.py → scorer.py → scenarios/*.yaml
Sprint 18-20: BG-runs only
Sprint 21: store/postgres.py
Sprint 22: api/mcp.py
Sprint 23: Dockerfile, docs/
```
