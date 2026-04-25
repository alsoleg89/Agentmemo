# cat1 55% investigation — единый трек сессии (2026-04-23 → 2026-04-24)

Полный merge всех материалов попытки поднять LOCOMO cat1 с 30.23% до 55% на `p1-1b-2conv` (gpt-4o-mini × gpt-4o-mini).

Контекст на старте: 8 подряд reverts в ai-knot, cheap fix paths закрыты, текущий best-baseline — `p1-1b-2conv` (cat1 = 13/43 = 30.23%, cat1-4 = 62.7%, cat4 = 80.7%).

---

## Часть 1 — Reverse-engineering cat1 WRONG через gold-item recall

### Что сделали

Ранее принимали decomposition "19/30 materializer problems" (`project_locomo_cat1_rank_dilution_is_materializer.md`). Он был на метрике `_contains_all_gold` (все токены gold должны присутствовать в ctx), которая ломается:
- SET gold `"Pride parade, school speech, support group"` — токен `speech` = 0 раз в корпусе (ghost)
- `"dinosaurs, nature"` — `dinosaurs` = 0 раз.

Переделали метрику → **gold-item recall**: gold split по `,|;|\band\b|\bor\b|/`, item-match если любой content-token (len≥4, не стоп-слово) присутствует в ctx.

### Результат

На 30 cat1 WRONG Q после rendered-ctx measurement:

| Recall range | N Q | Root cause | Retrieval lever |
|---|---:|---|---|
| 1.00 (all items in ctx) | 9 | LLM extraction fail | NO — recall already max |
| (0.5, 1.0) | 5 | Partial ctx | Marginal (MMR tweaks) |
| (0, 0.5] | 10 | Partial retrieval | YES — SET boost / K-subquery |
| 0.0 (no item in ctx) | 6 | Hard retrieval miss | YES if pool_has |

**Retrieval-only ceiling** = 15 recall-fixable × ~30% win rate ≈ +4–6 Q → 17–19/43 ≈ **40–44%**. Target 55% (+11 Q) недостижим без LLM-level fix'а (9 Q — gold IS в context, но модель не extract'ит).

Перечёрквающе предыдущие memory-записи:
- `project_locomo_cat1_rank_dilution_is_materializer.md` — claim "19/30 materializer" был на strict-metric; реально materializer ≤ 6 Q.
- `project_locomo_cat1_bottleneck_audit_20260423.md` — undercount LLM-fail (5/30), реально 9/30.

---

## Часть 2 — Preflights ranking-level техник

### Preflight 1: PPR entity-only

Скрипт: `scripts/ppr_preflight.py`.

Граф `entity ↔ raw` через `_PROPER_NAME_RE`, seeds = `frame.focus_entities`, `networkx.pagerank(alpha=0.85)`.

| Metric | Count |
|---|---:|
| PPR top-12 gold-in-ctx | 2/30 |
| PPR top-18 gold-in-ctx | 3/30 |
| PPR top-30 gold-in-ctx | 5/30 |

**Verdict**: строго хуже baseline (7/30). PPR игнорирует query tokens; все Melanie-raws ранжируются высоко независимо от Q (instruments vs destress vs family-activities).

### Preflight 2: PPR entity + token

Скрипт: `scripts/ppr_preflight_v2.py`.

Расширили граф token-nodes (len≥4, df_cap=50). Seeds = entities ∪ query content-tokens.

| Metric | Count |
|---|---:|
| PPR-ent top-12 | 5/30 |
| PPR-ent top-18 | 7/30 (= baseline) |
| PPR-ent+tok top-12 | 5/30 |
| PPR-ent+tok top-18 | 5/30 |
| PPR-ent+tok top-30 | 9/30 |
| base ∪ PPR-ent+tok top-18 | 7/30 |

**Verdict**: нет uplift. Union = baseline → PPR top-18 ⊆ baseline top-18. Как 3-й RRF-канал не добавляет coverage которую не достигает alone.

**Root cause**: cat1 WRONG — vocab mismatch ("activities" ↔ "pottery"), а PPR — структурный сигнал. Без vocab matching не помогает.

### Preflight 3: HyDE-lite (claim-derived BM25 expansion)

Скрипт: `scripts/hyde_preflight.py`.

Harvest content-tokens из `atomic_claims WHERE subject LIKE %seed%`, top-12 by frequency, concat к Q-токенам, center-only BM25 re-rank.

| Metric | Count |
|---|---:|
| plain BM25 replica top-18 | 2/30 |
| expanded BM25 top-18 | 4/30 (+2 over replica) |
| Q where expansion covers ≥1 gold token | 4/30 |
| NEW wins vs baseline | **1** ([0:24] Melanie destress; expansion contributes `running`) |

**Verdict**: слабый positive signal, bounded upside +1..+4 Q. Simple BM25 replica undermodels production (2/30 vs baseline 7/30).

### Preflight 4: HyDE v2 corrected metric + adjacent widening

Скрипт: `scripts/hyde_preflight_v2.py`.

Метрика `at_least_one_item_in_ctx` (item-split по comma/semicolon/and/or/slash). Pool widening через prev/next turn в session-order.

Result: baseline any-item = 24/30, pool_any = 28/30, pool_wide = 28/30 (adjacent widening дало **нулевой** diff).

### Preflight 5: pool-miss classification

Скрипт: `scripts/cat1_pool_miss_analysis.py`.

Для gold-misses (gold не в entity-filtered pool): классификация coref-pronoun / speaker-continuation / cross-turn-neighbour / pure-semantic-gap.

Result: 20/30 `pool_already_has_gold`, 8/10 `cross_turn_neighbour_mentions`, 1 coref, 1 pure semantic gap.

### Summary ranking-preflights

- 10/30 cat1 WRONG Q имеют gold в NO raw entity-filtered pool.
- Hard ceiling ranking-only: baseline 13/43 → +max 13 = 26/43 = 60.5% (теоретически).
- Practical ceiling HyDE-lite: 13 + 1..4 = 14..17/43 = 32.6..39.5%.
- **55% target требует pool widening, не ranking**. PPR закрыт, HyDE marginal.

---

## Часть 3 — Competitor research (первый research-agent)

### Техника 1: Personalized PageRank (HippoRAG)

Bipartite-граф `entity ↔ raw_episode`. На запрос: PPR с teleport=0.15, top-K по стационарному распределению. Fact-bearing turns связанные с entity через совместные nodes (kids, weekend) получают boost.

- Target bucket: "gold в пуле но rank 16-21"
- Adaptation: 3-й канал в RRF-fuse в `sqlite_storage.py:975-1036`
- Risk cat4: LOW-MED (малый вес в RRF)
- Deps: `networkx` (чистый Python)
- LOC: ~150
- **Preflight result: CLOSED** (entity-only хуже baseline, entity+token нет uplift)

### Техника 2: RAPTOR-lite session summaries (coarse-to-fine)

Детерминистическая concatenation raws сессии → embedding сессии (average of raw vectors). На запрос: top-3 сессий по embedding, потом BM25+cosine только внутри.

- Target bucket: pool composition (280 candidates → ~50)
- Adaptation: новая таблица `session_embeddings`
- Risk cat4: MED (если session-embedding промахивается — теряем gold сессию)
- Deps: существующие embeddings
- LOC: ~70
- **Не preflight'или**

### Техника 3: HyDE query expansion (claim-derived, LLM-free)

Для SET Q — "pseudo-answer" из existing STATE_TIMELINE/ENTITY_TOPIC bundles. Expanded token-set добавляется к Q-tokens в BM25.

- Target: vocab-gap между Q ("activities") и raw ("pottery")
- Adaptation: в `query_runtime.py` после `expand_claims`
- Risk cat4: LOW
- Deps: нулевые (existing pipeline)
- LOC: ~45
- **Preflight result: MARGINAL** (+1 NEW Q, upper bound +4)

### Техника 4: ColBERT-lite (sentence-level MaxSim re-rank)

После RRF-fuse top-40 — для каждого Q-token max cosine с token-embeddings raw, сумма = score. Re-rank финальный top-20. Sentence-level approximation без ColBERT-encoder.

- Target: 3-turn window dilution
- Adaptation: `_maxsim_rerank` в `sqlite_storage.py:1027`
- Risk cat4: MED (поднимает семантически близкие но фактологически неверные)
- Deps: cache sentence-level vectors
- LOC: ~100
- **Не preflight'или**

### Техника 5: GraphRAG map-reduce K-subquery

Для SET Q — K параллельных подзапросов по sub-topic tokens из claims. Каждый sub-query → top-3 raws. Финальный render = union, dedup.

- Target: enumeration через K прохода, не через BM25 diversity
- Adaptation: в operator `set_collect` (`query_operators.py`)
- Risk cat4: LOW-MED (только при `answer_space=SET`)
- Deps: нулевые
- LOC: ~50
- **Не preflight'или**

### Anti-patterns из research

НЕ брать:
1. Full ByteRover-style LLM-curated Context Tree (LLM-extraction на write — forbidden)
2. Cognee-style LLM-to-Cypher (LLM на retrieval path — latency+cost)
3. Letta agentic tool-call self-search (multi-turn loop — не решает retrieval)
4. Hindsight 4-network spreading activation (LLM-extraction causal links — forbidden)
5. Cross-encoder rerank (BGE/Cohere — +200ms latency, unknown interaction)
6. Расширение FP_EVENT_PATTERNS новыми verbs (cherry-pick — feedback_no_benchmark_cherrypick_patterns)

---

## Часть 4 — Architectural research (второй research-agent)

`research/architectural_ideas_cat1_20260423.md` — три архитектурных сдвига:

### Shift A — Deterministic Answer Sheet Materialization

Новая таблица `entity_answer_sheets(entity, predicate_bucket, value, evidence_episode_ids)`. Background rollup триггерится `materialization.py`. Buckets: `activity, location, role, preference, relation, possession` (~6). Render hook в `query_runtime.py` — если `answer_space==SET` → prepend sheet block.

LOC: ~300. Projected: **+9–15pp → 45–55%**.

### Shift B — Query-time Self-Consistency Voting

Для `answer_space=SET`: n=3 параллельных samples с T=0.7, затем детерминистический SET-union (merge + normalize + dedup via Jaccard).

LOC: ~80 (только `aiknotbench/src/evaluator.ts`). Projected: **+7–12pp → 37–42%**.

### Shift C — Contextual Retrieval + Late Chunking

Anthropic 2024 + Jina Late Chunking 2024. На ingest перед embedding **детерминистически prepend** compact session-summary: `"Melanie's Session 6: pottery, kids, weekend. TURN: I enjoy pottery..."`.

LOC: ~150. Projected: **+3–6pp**.

### Projected combinations

- A+B cumulative: 50–58%
- A+B+C: 60–68%

---

## Часть 5 — Preflights архитектурных shift'ов

Учитывая 8 подряд reverts в истории, реализовали offline preflight'ы до написания production-кода.

### Preflight Shift A: answer sheet prepend

Скрипт: `scripts/answer_sheet_preflight.py`.

Механика:
- Для `focus_entities(Q)` — `SELECT relation, value_text, source_episode_id FROM atomic_claims WHERE subject LIKE %entity%`
- Group by relation, рендер `# Answer sheet for <entity>\n- relation: val1 [ep1]; val2 [ep2]…`
- Prepend к baseline ctx, gpt-4o-mini (bench-identical ANSWER_SYSTEM), judge gpt-4o-mini (bench-identical JUDGE_SYSTEM)

| Режим | NEW-CORRECT | Projected cat1 |
|---|---:|---:|
| `prepend` (sheet + raw ctx) | 2/30 | 15/43 = **34.9%** |
| `sheet_only` (sheet заменяет raw) | 0/30 | 13/43 = 30.2% |
| `prepend_clean` (filter value<12 chars + pronoun-starts) | 2/30 | 15/43 = 34.9% |

**Projected +9–15pp → actual +4.7pp.** Off by 10–20pp.

**Почему Shift A не дал ожидаемого**:
- Q15 activities (gold: pottery, camping, painting, swimming): Sheet содержит 13 claims, из них 9 — `likes: it / likes: your help / likes: it!` (noise от FP.likes). `likes: camping trips with my fam…` present, но спрятан. LLM отвечает "pottery, running, hiking" — берёт из sheet pottery+running, hiking из raw ctx, camping **игнорирует** даже когда он в sheet.
- Q23 Melanie books (gold: "Nothing is Impossible", "Charlotte's Web"): claims не содержат gold titles. Sheet не помогает.
- Q11 Caroline moved from (gold: "Sweden"): gold vocab absent from claims.

Ключевой insight: LLM не воспринимает sheet как authoritative list. Junk-claims размывают сигнал. Shift A упирается в materialization quality.

### Preflight Shift B: self-consistency n=3 T=0.7

Скрипт: `scripts/self_consistency_preflight.py`.

Механика: 3 independent answer calls T=0.7, item-split `,|;|\band\b|\bor\b|/`, dedup lowercase-stem[:40], union → judge.

| Результат | Значение |
|---|---:|
| NEW-CORRECT | **0/30** |
| Projected cat1 | 13/43 = 30.2% (zero delta) |

**Projected +7–12pp → actual 0pp.** Off by 7–12pp.

**Почему полный провал**:
- Q60 instruments: 3 samples все "Melanie plays the clarinet" → union = то же самое (нет violin ни в одном семпле, т.к. нет в ctx).
- Q15 activities: samples pottery+hiking / pottery+hiking / pottery+hiking+exploring → union не добавляет camping, painting, swimming.
- Q75 "How many children": 3 samples все "not specified" → union = "not specified".

Fundamental: **union усиливает информацию, не добавляет её**. Если gold absent in all 3 samples (потому что absent from ctx), union не вернёт. Self-consistency работает при latent knowledge, не при missing ctx.

Дополнительно union добавляет лексический шум: "pottery, running" + "running to destress" + "runs to destress" → длинный noisy answer, судья WRONG.

### Preflight Shift A+B stacked

Скрипт: `scripts/shift_ab_combined_preflight.py`.

Механика: prepend sheet (A, clean filter) + n=3 T=0.7 + item-union (B).

| Результат | Значение |
|---|---:|
| NEW-CORRECT | **1/30** |
| Projected cat1 | 14/43 = **32.6%** |
| vs Shift A alone | **−1 Q (regress)** |

**Projected +19–28pp → actual +2.3pp.** Off by 18–25pp. **Хуже A alone.**

Регрессия: Q66 marshmallows (gold: Roast marshmallows, tell stories) — в Shift A alone ответ содержал "roast marshmallows" (CORRECT). В A+B три T=0.7-семпла смыли фрагмент шумом ("enjoys exploring nature, connecting, bonding…"), union = длинный ответ без "marshmallows", judge WRONG. Новый flip Q29 (Jon visited Paris+Rome) — один семпл случайно упомянул Paris, union захватил, compensated partial.

**Вывод**: stacking не аддитивен. Union-noise ломает sheet-effect на Q, где sheet alone работал.

---

## Часть 6 — Финальная таблица реальности vs прогноза

| Техника | Projected | Actual | Δ |
|---|---:|---:|---:|
| Baseline `p1-1b-2conv` | — | 30.23% | — |
| Ranking-only ceiling | 40–44% | — | — |
| PPR entity-only (top-12/18) | — | 6.7–10.0% | strongly negative |
| PPR entity+token (top-12/18) | — | 11.6–16.3% | below baseline |
| HyDE-lite | 32.6–39.5% | ~+1 Q | marginal |
| **Shift A (answer sheet)** | **45–55%** | **34.9%** | **−10–20pp** |
| **Shift B (self-consistency ×3)** | **37–42%** | **30.2%** | **−7–12pp** |
| **Shift A+B stacked** | **50–58%** | **32.6%** | **−18–25pp** |
| Shift C (not preflight'ed) | 48–52% (w/ A+C) | unvalidated | — |
| **Target** | **55%** | — | **gap −20pp** |

**Архитектурная research переоценила прирост в 2–3 раза.** Причины:
1. LLM-fail bucket (9/30, recall=1.0) считался "trivially fixable by concentrated answer list" — на практике LLM не treats sheet as authoritative, junk-claims размывают сигнал.
2. Claim vocabulary coverage слишком слабая: 6 hard-miss Q имеют gold absent from claims совсем → sheet пустой или без gold items.
3. Self-consistency требует latent knowledge, не missing ctx. При фундаментальных vocab gaps union бесполезен.
4. Stacking shift'ов НЕ additive. Union-noise может убить sheet-effect.

---

## Часть 7 — Артефакты сессии

### Preflight scripts (в `scripts/`)

- `ppr_preflight.py` — entity-only PPR
- `ppr_preflight_v2.py` — entity+token PPR
- `hyde_preflight.py` — claim-derived BM25 expansion (strict metric)
- `hyde_preflight_v2.py` — at-least-one-item metric + adjacent widening
- `cat1_pool_miss_analysis.py` — coref/speaker/neighbour/semantic buckets
- `answer_sheet_preflight.py` — Shift A (3 modes)
- `self_consistency_preflight.py` — Shift B
- `shift_ab_combined_preflight.py` — Shift A+B stacked

### Research docs (в `research/`)

- `competitor_ideas_cat1_20260423.md` — 5 техник из competitor research
- `architectural_ideas_cat1_20260423.md` — Shift A/B/C proposal
- `cat1_preflight_findings_20260423.md` — PPR/HyDE summary (заменён этим файлом)
- `architectural_preflight_findings_20260423.md` — Shift A/B/A+B summary (заменён этим файлом)
- `session_log_cat1_preflights_20260423.md` — session trace (заменён этим файлом)
- `cat1_55_investigation_20260423.md` — **этот файл** (единый merged-трек)

### Per-run outputs (в `aiknotbench/data/runs/p1-1b-2conv/`)

- `ppr_preflight.json`, `ppr_preflight_v2.json`
- `hyde_preflight.json`, `hyde_preflight_v2.json`
- `cat1_pool_miss.json`
- `answer_sheet_preflight_prepend.json`, `_prepend_clean.json`, `_sheet_only.json`
- `self_consistency_preflight_n3.json`
- `shift_ab_combined_preflight_n3.json`

### Memory entries (в `~/.claude/projects/.../memory/`)

- `project_locomo_cat1_true_ceiling_20260423.md` — gold-item recall decomposition (9+5+10+6), ceiling 40–44%
- `project_locomo_cat1_shift_ab_negative_20260423.md` — A=34.9%, B=30.2%, A+B=32.6%
- `project_cat1_session_artifacts_20260423.md` — index of scripts/docs/outputs

`MEMORY.md` — updated index.

### Git status

**Ничего не закоммичено.** Все изменения в `scripts/`, `research/`, memory. Production-код в `src/` и `aiknotbench/src/` не трогали.

Branch: `feature/configurable-mcp-env-v0.9.4`. HEAD: `32fa6fa docs: record F1-alone ACCEPT-no-promote and Move M REVERT verdicts`.

---

## Часть 8 — Остановленные / неначатые направления

1. **Shift C (Contextual Retrieval)** — не валидирован. Требует re-embedding корпуса (~$0.05–0.10, migration runtime). Best case по research: +3–6pp. Учитывая Shift A/B off-by-factor-2-3, реально ожидать ≤1 Q. Не пробивает 55% даже в лучшем случае (~36%).

2. **ColBERT-lite / RAPTOR-lite / GraphRAG map-reduce** — упомянуты в competitor research, не preflight'ились. Late-interaction/multi-query — complex additions, выгода не доказана.

3. **Pool widening с cat4 tolerance** — нарушает stop-rule (cat4 floor 68.1%, cat5 floor 20%). Явно forbidden.

4. **Materializer refactor** — 8 consecutive reverts в истории (phase1e relative-time, claims-first promotion). Cheap patch path closed. Глубокий refactor = multi-week проект, не в scope 55%-target'а.

5. **Self-RAG / Corrective RAG** — упомянуто, не preflight'ились. Требует ReAct-loop в evaluator, нарушает "no prompt engineering".

---

## Часть 9 — Final recommendation

**55% cat1 на `p1-1b-2conv` × gpt-4o-mini × текущий materializer — недостижимо** без одного из:

- Смены answer-модели (явно forbidden)
- Fundamental materializer refactor (claim vocabulary coverage от 23% rate → 50%+) — отдельный multi-week проект
- Tolerance к cat4 precision regression (forbidden stop-rule)

Реалистичный ceiling текущей архитектуры = **34.9%** (Shift A production impl, +2 Q). Проведение production Shift A (~300 LOC, ~2 weeks) для +4.7pp при риске regression другим категориям — не окупается.

Честная позиция для пользователя:
- Закрыть line of investigation "55% cat1"
- Переформулировать цель: "cat1-4 aggregate improvement" с другим target
- Или зафиксировать `p1-1b-2conv` как финальный baseline для v0.9.4 и работать над другими направлениями (cat2, cat5, MA scenarios)

---

## Часть 10 — Что НЕ сделано в этой сессии

- Никаких production-изменений в `src/` или `aiknotbench/src/`
- Никаких bench runs — все validation через preflight scripts с заморозкой baseline из `log.jsonl`
- Git commits, PRs — нет
- Updates DECISIONS.md — нет
- Shift C preflight — намеренно skipped (see часть 8)

---

## Appendix A — Mindset shifts из architectural research

1. **Raw-first ≠ Raw-only на read-path**. Raw = DRAM (authority), aggregates = L1 cache (derivative, rebuildable). Разрешает Shift A без нарушения core-контракта.
2. **"LLM extraction на write" ≠ "deterministic rollup из claims"**. Агрегация по `AtomicClaim` — это index, не extraction.
3. **Retrieval completeness ≠ answer completeness**. 9/30 recall=1.0 и всё равно WRONG → LLM extraction из длинного ctx самостоятельный bottleneck.
4. **Single-sample temperature=0 — артефакт cost-optimization**. Для enumeration self-consistency/union — first-class design tool (на деле оказался неработающим для missing-info cases).
5. **Fixed-granularity chunking — legacy from static-corpus RAG**. В conversational memory session-level semantic glue теряется в fixed ±1 window. Contextual Retrieval + late chunking — SOTA 2024.

---

## Appendix B — Радикальное "что если" (не реализовано)

Что если ai-knot перестаёт быть **retrieval system** и становится **pre-materialized answer-graph system**? Build step: при ingest строить per-`(entity, predicate_bucket)` "materialized views" (SQL-style), где каждая view — answer-ready SET list с embedded evidence pointers. Materializer v7 эмитит не claims, а **answer-artifacts**. Retrieval деградирует до "найти правильную view + её evidence", answer LLM — до "format this list as prose". Cat1 SET потенциально достигает 80-90%, потому что LLM перестаёт быть extraction-engine. Cat2 multi-hop остаётся на текущем pipeline. ~2 недели работы.

Учитывая провал Shift A preflight (LLM не воспринимает answer sheet как authoritative), это "что если" скорее всего тоже не сработает без prompt engineering — LLM генерирует нарративный ответ поверх structured input, а не копирует список.

---

## Appendix C — Ссылки на академические источники

Из competitor research:
- HippoRAG 2 — https://arxiv.org/abs/2405.14831
- RAPTOR — https://arxiv.org/abs/2401.18059
- Mem0 — https://arxiv.org/abs/2504.19413
- HyDE — https://aclanthology.org/2023.acl-long.99/
- ColBERT — https://arxiv.org/abs/2004.12832
- GraphRAG Global Search — https://microsoft.github.io/graphrag/query/global_search/
- Zep / Graphiti — https://arxiv.org/abs/2501.13956

Из architectural research:
- Mem0 architecture paper — https://arxiv.org/abs/2504.19413
- Self-Consistency (Wang 2022) — https://arxiv.org/abs/2203.11171
- Universal Self-Consistency (Chen 2023) — https://arxiv.org/abs/2311.17311
- Anthropic Contextual Retrieval (2024) — https://www.anthropic.com/news/contextual-retrieval
- Jina Late Chunking (2024) — https://arxiv.org/abs/2409.04701
- Self-RAG (Asai 2023) — https://arxiv.org/abs/2310.11511
- Corrective RAG — https://arxiv.org/abs/2401.15884

---

## Appendix D — Файлы в ai-knot, на которые ссылались

- `src/ai_knot/storage/sqlite_storage.py:825-1042` — `search_episodes_by_entities` + RRF
- `src/ai_knot/query_runtime.py:140-205` — pipeline orchestration + caps
- `src/ai_knot/query_operators.py` — `set_collect` operator
- `src/ai_knot/materialization.py:220-685` — FP extractor + pattern regex
- `aiknotbench/src/evaluator.ts:31-66` — `answerQuestion` + `ANSWER_SYSTEM`
- `~/.claude/projects/.../memory/project_locomo_cat1_retrieval_diagnostic.md` — bottleneck decomposition
- `~/.claude/projects/.../memory/project_locomo_cat1_rank_dilution_is_materializer.md` — overturned claim
