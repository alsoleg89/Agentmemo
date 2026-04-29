# Research Index — ai-knot

**Обновлён:** 2026-04-29

Навигация по всем материалам в `research/`. Организовано по темам.

---

## Session Reports (хронология)

| Файл | Дата | Что внутри |
|------|------|-----------|
| [d2_channel_e_replay_with_dense_20260429.json](d2_channel_e_replay_with_dense_20260429.json) | **2026-04-29** | **C2 dense rebaseline (OpenAI text-embedding-3-small).** v0_dense cat1=0.205 (PASS prod parity). Channel E no-op holds with dense pool (Δ=+0.000). |
| [d2_k1_ensemble_selector_20260429.json](d2_k1_ensemble_selector_20260429.json) | **2026-04-29** | **C1 ensemble selector.** ensemble_v2 (union): cat1 +0.090, cat2 +0.209, cat4 +0.179, cat5 +0.089. ensemble_v1 cat5 REGRESSION −0.069. pure BM25 cat5 +0.207 (RRF hurts synthesis). |
| [d2_oracle_pgr_ceiling_20260429.json](d2_oracle_pgr_ceiling_20260429.json) | **2026-04-29** | **B3 oracle PGR ceiling.** strict=0.121 (router blocks 69.5%). permissive=1.000. Extraction-first fails: ceiling < 0.25. |
| [d2_extraction_failure_modes_20260429.json](d2_extraction_failure_modes_20260429.json) | **2026-04-29** | **B2 failure breakdown.** 93.9% FACET_VOCAB_GAP but top-30 tokens are filler (great/thank/awesome). Vocab expansion adds noise, not signal. |
| [d2_cat1_per_question_audit_20260429.json](d2_cat1_per_question_audit_20260429.json) | **2026-04-29** | **B1 gold audit.** 86% pool_hit_pack_miss. **RANKING bottleneck confirmed.** Extraction is NOT the problem. stage1_miss_index_hit=0% confirms A3 no-op. |
| [d2_extraction_coverage_20260429.json](d2_extraction_coverage_20260429.json) | **2026-04-28/29** | **A1 extraction coverage.** with_full_triple=42.5% (FAIL), F1/F2 absent in c1-baseline. |
| [d2_k1_lookup_hit_rate_20260429.json](d2_k1_lookup_hit_rate_20260429.json) | **2026-04-29** | **A2 router+lookup.** cat1 router_hit=27.6% (FAIL), lookup_has_gold=50% (PARTIAL). |
| [d2_channel_e_replay_20260429.json](d2_channel_e_replay_20260429.json) | **2026-04-29** | **A3 Channel E replay.** v2 delta=+0.000 (complete no-op). exclusive gold=0/66. |
| [memory_kernel_v2_structural_recommendation_20260429.md](memory_kernel_v2_structural_recommendation_20260429.md) | **2026-04-29** | **АКТУАЛЬНО.** Full causal diagnosis B1-B3 + C1-C2. **BRANCH NEW: Entity-Pack Union (ranking fix)**. cat1 projected +9pp, cat5 +9pp via union approach. |
| [d1_alt_dense_rrf_20260428_205956.json](d1_alt_dense_rrf_20260428_205956.json) | **2026-04-28** | **D1-alt dense RRF.** Dense pool 5→20 + dense as 7th RRF signal (w=2.0): cat1 PGR 0.152→0.183 (+0.031), cat2 +0.040, cat4 +0.057. Ceiling pool=20: 47.2% gold reachable. Implemented in knowledge.py. |
| [d1_replay_results_20260428.md](d1_replay_results_20260428.md) | **2026-04-28** | **D1 KILL RULE.** Entity-boost falsified: +0.9pp cat1 PGR (need +55pp). Root cause: semantic mismatch — query "martial arts" vs fact "kickboxing". 44.8% gold facts rank >60 in BM25. Next: dense retrieval or wider pack. |
| [memory_kernel_v2_20260428.md](memory_kernel_v2_20260428.md) | **2026-04-28** | MemoryKernel v2 synthesis: 16 projects code-level audit (Mem0/Graphiti/LlamaIndex/etc). PackGoldRecall=58.5% windowed bottleneck. Entity-boost greenlit as D1 (now falsified). Stage D2-D5 on hold. |
| [session_report_20260428.md](session_report_20260428.md) | **2026-04-28** | **АКТУАЛЬНО.** Phase 3+4 results + полный анализ 10 фаз. cat1 trajectory: 17→18→15. Root cause: pack size=12 + vocabulary inflation. Next: Phase 5 + pack size increase. |
| [session_report_20260427.md](session_report_20260427.md) | 2026-04-27 | DSN bug fix + temporal anchor (+17pp cat2) + Codex data-audit: 3 ignored LoCoMo surfaces, +9 migration table. |
| [k1_metric_breakthrough_report_20260427.md](k1_metric_breakthrough_report_20260427.md) | 2026-04-27 | Codex full audit: coverage analysis, primary +9 migration, reserve bank, architecture hypothesis. |

---

## Текущая работа — Cat1/Cat2 улучшение

| Файл | Что внутри |
|------|-----------|
| [phase_e_query_shape_routing.md](phase_e_query_shape_routing.md) | **АКТИВНЫЙ.** Phase E: Query Shape Router (6 интентов), Stage-3 RRF fusion, MMR slot protection, Channel C token match. Baseline TOT=52%, target ~70%. Бенчмарк pending. |
| [phase_c_c6b_c6c_implementation.md](phase_c_c6b_c6c_implementation.md) | Phase C реализация: C6b enumeration split (все режимы) + C6c date enrichment. Baseline Cat1=39% Cat2=53%. |
| [aggregation_design.md](aggregation_design.md) | **АКТИВНЫЙ.** Дизайн lookup index для aggregation recall. Метрики: +14.4pp теоретический максимум Cat1. Два режима (learn-ON/OFF). API A/B/C сравнение. TurboQuant контекст. |
| [cat1_per_conv_analysis.md](cat1_per_conv_analysis.md) | **АКТИВНЫЙ.** Per-conv breakdown: aggregation vs point вопросы, MMR churn анализ, failure type по conv. Вывод: entity-grouped format — единственный lever для M-type. |
| [locomo_learn_off_partial_results.md](locomo_learn_off_partial_results.md) | Результаты v095-learn-off-all (conv 0–5): Cat1=35.2%, Cat2=50%. Breakdown: 83% M-type, 17% R-type. Off-by-1 и vague-gold патерны. |
| [locomo_fails_report.md](locomo_fails_report.md) | Детальный per-question анализ (conv 0, gpt-4o). Таблица 24 WRONG Cat1 с классификацией R/M/J. Промпты v1/v2/v3. learn() изоляционный эксперимент. |
| [phase2_research.md](phase2_research.md) | Phase 2 результаты — overfetch, raw-aware RRF, skip PRF. Все "мимо". Диагноз: bottleneck в post-retrieval selection. |
| [pipeline_diagnosis_plan.md](pipeline_diagnosis_plan.md) | Диагностика pipeline: где теряются очки. Анализ BM25 IDF, sliding window overlap, near-duplicate saturation. |
| [cat12_improvement_plan.md](cat12_improvement_plan.md) | Ранний план Cat1/Cat2 улучшений (до MMR). |
| [cat12_plan_status.md](cat12_plan_status.md) | Статус полного плана Cat1/Cat2. |
| [cat12_changes_research.md](cat12_changes_research.md) | Исследование изменений по категориям 2, 5, 6. Multi-agent, complexity, effectiveness. |

---

## Диагностика и changelog

| Файл | Что внутри |
|------|-----------|
| [locomo_diagnostic_20260410.md](locomo_diagnostic_20260410.md) | Найден критический баг: DB corruption — все запуски писали в общую БД. Isolation fix. |
| [changelog_v094_entity_scoped_retrieval.md](changelog_v094_entity_scoped_retrieval.md) | Changelog v0.9.4: entity-scoped retrieval, что изменилось, что добавлено. |
| [fixes_11052026.md](fixes_11052026.md) | OpenAI embeddings support — статус, конфиг, баг asyncio event loop. |
| [impact_analysis_pattern_facts.md](impact_analysis_pattern_facts.md) | Анализ влияния pattern facts на LOCOMO conv-0. |
| [locomo_analysis.md](locomo_analysis.md) | Dataset anatomy: 1986 QA pairs, 10 convs. Категории, distribution вопросов. |

---

## Архитектурные исследования

| Файл | Что внутри |
|------|-----------|
| [architecture_synthesis.md](architecture_synthesis.md) | Синтез архитектуры: что выжило после критики. Финальные принципы дизайна. |
| [approach_evolution_20260410.md](approach_evolution_20260410.md) | Эволюция подходов: entity scoping → pattern memory. История решений. |
| [analysis_approach_critique.md](analysis_approach_critique.md) | Критика подходов: почему большинство не сработает. Что может. |
| [implementation_plan_v2.md](implementation_plan_v2.md) | Plan v2: entity-scoped retrieval для LOCOMO. (Предшественник текущего плана.) |
| [ma_scenario_analysis.md](ma_scenario_analysis.md) | Multi-agent scenario analysis для entity-scoped retrieval. |

---

## Экспериментальные идеи (исследовались, не реализованы)

| Файл | Что внутри |
|------|-----------|
| [pattern_memory_architecture.md](pattern_memory_architecture.md) | Pattern Memory: ассоциативный retrieval на основе co-occurrence. Биологическая аналогия. |
| [strand_data_structure.md](strand_data_structure.md) | Strand: DNA-inspired binary co-occurrence структура. Технический дизайн. |
| [strand_stress_test_critique.md](strand_stress_test_critique.md) | Стресс-тест критика Strand: где ломается. |
| [biological_mechanisms_deep_dive.md](biological_mechanisms_deep_dive.md) | Биологические механизмы памяти: что организмы реально делают. Hippocampus, engram. |
| [cognitive_memory_model.md](cognitive_memory_model.md) | ai-knot как психологическая модель памяти. Теоретическая база. |

---

## Конкуренты

| Файл | Что внутри |
|------|-----------|
| [competitors/00_comparison_table.md](competitors/00_comparison_table.md) | **Главная таблица сравнения.** Retrieval техники всех конкурентов. Уникальность ai-knot. |
| [competitors/01_mem0.md](competitors/01_mem0.md) | Mem0: семантический search + get_all + graph memory. API паттерны. |
| [competitors/02_letta.md](competitors/02_letta.md) | Letta (MemGPT): archival memory, 3-tier architecture. Только semantic search. |
| [competitors/03_zep_graphiti.md](competitors/03_zep_graphiti.md) | Zep/Graphiti: temporal knowledge graph, entity nodes, BFS traversal. |
| [competitors/04_cognee.md](competitors/04_cognee.md) | Cognee: knowledge graph + vector hybrid. |
| [competitors/05_supermemory.md](competitors/05_supermemory.md) | Supermemory: simple vector store. |
| [competitors/06_hindsight.md](competitors/06_hindsight.md) | Hindsight/Vectorize: TEMPR, spreading activation. |

---

## Академические статьи

| Файл | Что внутри |
|------|-----------|
| [papers/00_index.md](papers/00_index.md) | Главный индекс статей с оценкой применимости. |
| [papers/01_magma_multi_graph_memory.md](papers/01_magma_multi_graph_memory.md) | MAGMA: multi-graph agentic memory (arXiv 2601.03236, Jan 2026) |
| [papers/02_synapse_spreading_activation.md](papers/02_synapse_spreading_activation.md) | SYNAPSE: episodic-semantic via spreading activation (arXiv 2601.02744) |
| [papers/03_hypermem_hypergraph.md](papers/03_hypermem_hypergraph.md) | HyperMem: hypergraph для long-term conversations (arXiv 2604.08256, Apr 2026) |
| [papers/04_hindsight_tempr.md](papers/04_hindsight_tempr.md) | Hindsight TEMPR: retains, recalls, reflects (arXiv 2512.12818) |
| [papers/05_evermemos_engram.md](papers/05_evermemos_engram.md) | EverMemOS: self-organizing memory OS (arXiv 2601.02163) |
| [papers/06_zep_graphiti_temporal_kg.md](papers/06_zep_graphiti_temporal_kg.md) | Zep temporal KG (arXiv 2501.13956) |
| [papers/07_timem_temporal_tree.md](papers/07_timem_temporal_tree.md) | TiMem: temporal-hierarchical consolidation (arXiv 2601.02845) |
| [papers/08_amem_zettelkasten.md](papers/08_amem_zettelkasten.md) | A-MEM: Zettelkasten для LLM agents (arXiv 2502.12110, NeurIPS 2025) |
| [papers/09_memmachine_ground_truth.md](papers/09_memmachine_ground_truth.md) | MemMachine: ground-truth preserving (arXiv 2604.04853, Apr 2026) |
| [papers/10_self_rag_corrective_rag.md](papers/10_self_rag_corrective_rag.md) | Self-RAG + CRAG: corrective retrieval augmented generation |
| [papers/11_surveys_benchmarks.md](papers/11_surveys_benchmarks.md) | Surveys + benchmarks: LoCoMo, LOCOMO10, LongMemEval |

---

## Публикации / маркетинг

| Файл | Что внутри |
|------|-----------|
| [paper_plan.md](paper_plan.md) | Plan академической статьи: entity-scoped retrieval для LLM agent memory. |
| [marketing_paper_plan.md](marketing_paper_plan.md) | Маркетинговый план публикации. |
