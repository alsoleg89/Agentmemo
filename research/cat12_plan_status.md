# Cat1/Cat2 Improvement — Full Status

**Date:** 2026-04-11

---

## Completed

### Phase 1 ✅
- API key fallback (`_mcp_tools.py`, `mcp_server.py`)
- AGGREGATION fallback без entity match (`_query_intent.py`)

### Phase 2 ✅
- **Consolidation** (`learning.py`): `_consolidate_phase()`, threshold >= 2, compact format
- **Overfetch** (`knowledge.py`, `_bm25.py`): `effective_top_k = top_k * 3` for AGGREGATION, `faithfulness_k` floor fix
- **Raw-aware RRF** (`knowledge.py`): zeroes out dead signals when <10% facts have slot_key
- **Skip PRF** (`_bm25.py`, `knowledge.py`): skips PRF for AGGREGATION intent
- Tests: 11 new consolidation tests, all pass. Full suite: 739 passed, 2 pre-existing failures.

### Phase 3 ✅
- Docstring fix в `_consolidate_phase()` — generic example вместо Cat1-specific

---

## Benchmark results (before Phase 2)
- Cat1: 21 WRONG (11 M/J + 10 R) — learn() не вытащил swimming/sunrise/museum
- Cat2: 18 WRONG — 6 off-by-1, 6 relative date, 5 R, 1 wrong

---

## Текущий статус: ждём benchmark

Пользователь запускает в двух режимах:
- `--ingest-mode dated-learn` (learn ON) → consolidation + entity pipeline + raw improvements
- `--ingest-mode dated` (learn OFF) → только raw improvements (overfetch, raw RRF, skip PRF)

---

## Нерешённые проблемы (Phase 4 — после benchmark)

### 1. Off-by-1 date (6 Cat2 вопросов)
- **Причина:** `dated-learn` хранит raw turns с session date `[8 May]` рядом с extracted facts `7 May`. Raw доминируют.
- **Варианты:** learn-only mode / приоритизация extracted / dedup raw vs extracted
- **Решение зависит от benchmark результатов**

### 2. TEMPORAL intent (отложен)
- "When did X?" → GENERAL intent → нет date-aware ranking
- Предыдущий подход (vocabulary list `_TEMPORAL_PREFIXES`) отклонён как слишком специфичный
- Нужен generic подход или отказ

### 3. Relative date failures (6 Cat2 вопросов)
- Gold: "the week before 9 June" → Got: "9 June"
- Это M-failure (model precision), не retrieval — факт в контексте, но LLM упрощает

### 4. Retrieval failures (5 Cat2 + 10 Cat1 R-failures)
- Анализ конкретных промахов после benchmark → возможны точечные улучшения

---

## Исследования (файлы)

- `research/cat12_improvement_plan.md` — исходный план с root cause analysis
- `research/cat12_changes_research.md` — multi-agent/complexity/effectiveness анализ Changes 2,5,6
- `research/phase2_research.md` — off-by-1 date bug, raw facts analysis, competitive analysis
