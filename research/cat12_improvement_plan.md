# Cat1 & Cat2 Improvement — Research & Plan

**Date:** 2026-04-11

---

## Root Cause Analysis

### Cat1 (25-37%) — Aggregation failure

24 провала из 32 вопросов:

| Тип | Кол-во | % | Описание |
|-----|--------|---|----------|
| M — Model incomplete | 11 | 46% | Факты В контексте, модель перечислила не все |
| R — Retrieval failure | 9 | 37% | Нужный факт НЕ попал в top-60 |
| J — Judge strict | 4 | 17% | Ответ верный, судья срезал |

**Главная проблема:** 66% Cat1 вопросов = агрегация через 3-8 сессий. top_k=60 на ~1740 фактов = 3.4% покрытие. Математически невозможно найти все упоминания.

**Entity pipeline мёртв:**
- `_build_entity_dictionary` смотрит только `f.entity` и `f.value_text`
- Raw turns от `add()` — entity field пустой
- Только ~16% extracted фактов имеют entity
- Весь entity pipeline (scoping, boost, hop) работает на 16% данных

**AGGREGATION intent не срабатывает:**
- Классификатор (`_query_intent.py:157-158`) требует entity field match в facts
- Нет entity → нет AGGREGATION → нет специальных RRF weights
- Все Cat1 вопросы классифицируются как GENERAL

**3-turn windows разбавляют сигнал:**
- "swimming" = 1 слово в чанке из 30 токенов → TF ≈ 0.03
- BM25 даёт минимальный score

### Cat2 (60-68%) — Temporal precision failure

12-15 провалов из 37 вопросов. 100% = найти ОДНУ строку с датой.

- Нет TEMPORAL intent → "When did X?" = GENERAL
- Дата в факте (`[7 May 2023]`), но query не содержит дату
- BM25 матчит по content-словам ("caroline", "lgbtq"), которые есть во многих фактах
- Датированный факт тонет в шуме

### Critical Discovery: Benchmark DB has ZERO entity fields

Background agent проверил реальные DB:
- `v094-4o-cat12-1conv`: 440 facts, 0 with entity, ALL dated raw turns
- `v094-openai-2conv-full`: 828 facts, 0 with entity, ALL dated raw turns
- Даже в `dated-learn` mode, learn() не производит structured extracted facts

**Причина:** `tool_learn` в `_mcp_tools.py:197-198` проверяет `AI_KNOT_API_KEY`, но не fallback на `OPENAI_API_KEY`. Пользователь ставит `OPENAI_API_KEY` + `AI_KNOT_PROVIDER=openai`, но learn() работает в degraded mode → stores only last user message.

---

## Competitor Research

### What's unique to ai-knot (ZERO competitors have this)

1. **Post-extraction fact consolidation** — cluster extracted facts by entity, create aggregate summary facts. Zep, Mem0, Letta, Hindsight, memvid, MAGMA — все хранят атомарные факты.

2. **Date-pattern boosting for temporal queries** — boost facts containing date patterns when query asks "When did X?". memvid does recency (frame metadata), not temporal precision. Zep/Hindsight/Letta — no temporal intent.

3. **Intent-adaptive retrieval objective switching** — changes entire retrieval OBJECTIVE per intent, not just weights/top_k. No competitor does this as first-class architecture.

4. **Ebbinghaus forgetting + spacing effect** — biological memory decay model.

5. **Slot-based CAS with temporal versioning** — deterministic fact lifecycle management.

### What's commoditized (competitors also do this)

- Adaptive top_k based on question type (memvid, Zep)
- Question classification (aggregation/recency/analytical) (memvid)
- Multi-pass fallback retrieval (memvid: AND→OR→lexical→expanded→timeline)
- Entity extraction from conversations (Mem0, Zep, Letta)
- RRF fusion of multiple retrieval signals (Zep, memvid)

### TEMPORAL intent research detail

| System | Temporal handling | Date-boost? |
|--------|-----------------|-------------|
| memvid | `is_recency_question()` — "current", "latest", "today" keywords → boost by frame timestamp | NO — boosts recency, not date precision |
| Zep | Temporal edges in knowledge graph | NO — graph-level, not retrieval-level |
| Hindsight | No temporal handling | NO |
| Letta | No temporal handling | NO |
| Mem0 | No temporal handling | NO |
| MAGMA | Temporal context in retrieval | NO — temporal context, not date boosting |

**Conclusion:** Date-pattern boosting для "When did X?" queries is NOVEL. Но подход `_TEMPORAL_PREFIXES` со списком фраз — слишком специфичен. Нужен более generic подход.

### Overfetch research detail

| System | Overfetch? | How? |
|--------|-----------|------|
| memvid | YES — `analytical×5, aggregation×3, recency×2` | Static multiplier per question type |
| Zep | YES — node expansion in graph | Graph traversal, not retrieval-level |
| Letta | NO | Fixed context window |
| Mem0 | NO | Standard top_k |

**Conclusion:** Overfetch alone is commoditized. But intent-adaptive coverage optimization (changing retrieval OBJECTIVE, not just multiplier) is unique to ai-knot.

---

## Decided Changes

### Phase 1 — Two fixes (immediate)

#### Fix 1: `tool_learn` API key fallback

**Files:** `src/ai_knot/_mcp_tools.py`, `src/ai_knot/mcp_server.py`

**Problem:** `tool_learn` checks only `AI_KNOT_API_KEY`, doesn't fallback to `OPENAI_API_KEY`. Users with `OPENAI_API_KEY` + `AI_KNOT_PROVIDER=openai` get degraded mode → 0 extracted facts, dead entity pipeline.

**Fix:** Add fallback chain:
```python
effective_key = (
    api_key
    or os.environ.get("AI_KNOT_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY")
)
```

Same pattern already used for `embed_api_key` in `_build_kb()`.

#### Fix 2: AGGREGATION fallback without entity match

**File:** `src/ai_knot/_query_intent.py`

**Problem:** AGGREGATION intent requires `f.entity` match in entity loop (line 157-158). If entity fields empty → AGGREGATION never fires.

**Fix:** One line after entity loop:
```python
if has_agg_signal:
    return _PoolQueryIntent.AGGREGATION
```

Uses EXISTING `has_agg_signal` — no new words/patterns.

### Phase 2 — Research needed (pending benchmark results)

#### Change 2: Post-extraction consolidation

Group by entity → create keyword-dense aggregate per entity. Needs research on:
- Multi-agent impact: how do aggregates behave in shared pools?
- Complexity: O(F) per learn() call
- Effectiveness: does one giant aggregate per entity actually help BM25?

#### Change 5: Overfetch for AGGREGATION

`effective_top_k = top_k * 3` for AGGREGATION intent. Needs research on:
- Multi-agent impact: overfetch on large shared pools — performance?
- Does overfetch + trim actually increase diversity?

#### Change 6: Content-based entity dictionary

Extract entities from query proper nouns → verify in corpus. Needs research on:
- Multi-agent impact: proper noun detection in multi-agent queries?
- O(E × F) complexity — acceptable for large pools?

### Rejected/Deferred

| Change | Status | Reason |
|--------|--------|--------|
| Speaker entity backfill | REJECTED | LOCOMO-specific `Speaker: text` regex |
| AGGREGATION specific phrases | REJECTED | Tailored to Cat1 questions |
| WINDOW 3→1 | REJECTED | Benchmark adapter change |
| TEMPORAL intent | DEFERRED | Too specific in current form, needs rethinking |
| Jaccard dedup | DROPPED | Existing exact-match dedup sufficient |

---

## Benchmark Run History

| Run | Answer model | Prompt | Cat1 | Cat2 | Cat3 | Cat4 | Overall |
|-----|-------------|--------|------|------|------|------|---------|
| v094-openai-1conv-4o | gpt-4o | v1 original | 25% | 67.6% | 38.5% | 87.1% | 56.6% |
| v094-new-prompt-1conv | gpt-4o-mini | v2 detailed | 21.9% | 59.5% | 61.5% | 87.1% | 64.5% |
| v094-minimal-prompt-1conv | gpt-4o-mini | v3 minimal | 21.9% | 35.1% | 76.9% | 87.1% | 59.9% |
| v094-4o-cat12-1conv | gpt-4o | v3 minimal | 37.5% | 59.5% | — | — | 49.3% |

### Best per category

| Cat | Best | Run |
|-----|------|-----|
| Cat1 | 37.5% | gpt-4o + v3 minimal |
| Cat2 | 67.6% | gpt-4o + v1 original |
| Cat3 | 76.9% | gpt-4o-mini + v3 minimal |
| Cat4 | 87.1% | any |
