# Phase C — C6b + C6c Implementation

**Дата:** 2026-04-12  
**Статус:** Реализовано, бенчмарк запущен (результаты pending)

---

## Baseline (до Phase C)

| Метрика | Значение |
|---------|---------|
| Cat1 (single-hop) | 29/74 = **39%** |
| Cat2 (multi-hop) | 48/90 = **53%** |

**Диагностика Cat1 WRONG (45 total):**
- `answered_wrong_judge` — 31 (69%) — retrieval/ranking/ответ, prompts off-limits
- `extraction_miss` — 9 (20%) — **цель C6b**
- `select_topk_drop` — 5 (11%) — частично адресует C6c

---

## C6c — Date tag enrichment

**Цель:** Cat2 — temporal queries плохо матчатся в BM25F.

**Реализация:**
- Новый модуль `src/ai_knot/_date_enrichment.py` (pure-regex, без python-dateutil)
- Паттерны: `[27 June, 2023]`, `June 27, 2023`, `2023-06-27`, `June 2023`
- `enrich_date_tags(fact)` инжектирует в `fact.tags`: ISO, month-year, month, year (cap 10)
- Работает на `fact.content` + `fact.witness_surface`
- BM25F tags weight = 2.0 → прямой буст для date-queries

**Hooks (mode-agnostic):**
- `KnowledgeBase.add()` — покрывает `raw`, `dated`
- `Extractor.extract()` конец — покрывает `learn`, `dated-learn`

**Тесты:** 16 тестов в `tests/test_date_enrichment.py`

---

## C6b v1 — Enumeration split (learn/dated-learn only)

**Цель:** Cat1 `extraction_miss` — список-факты ("pottery, camping, painting, swimming") остаются неразбитыми, при точечном запросе не матчатся.

**Реализация:**
- `split_enumerations(facts)` в `src/ai_knot/extractor.py`
- Паттерны: comma `A, B, C, and D` + semicolon `A; B; C`
- Требования: ≥3 items, ≤20 chars/item (защита от "New York, NY")
- Дочерние факты: `dataclasses.replace` с новым id, `importance -= 0.05`, `tags=list(f.tags)` (copy), `source_snippets=[]`
- Hook: `Extractor.extract()` между parse и `deduplicate_facts`

**Gap v1:** работало только в learn/dated-learn. В `dated` и `raw` экстрактор не вызывается.

---

## C6b v2 — Enumeration split в ВСЕХ режимах

**User request:** «C6b ❌ → enumeration split только в dated-learn — надо сделать в dated»

**Дополнения к v1:**
1. `_build_verb_prefix(content, match_start)` — новая функция:
   - Сохраняет `[date]` bracket на дочерних фактах (нужен для date enrichment)
   - Тримит prefix по `/` или `. ` — убирает предыдущие turns из window
   - Пример: `[2023-06-27] Bob: hi / Alice: I love pottery, camping...`
     - До: child = `[2023-06-27] Bob: hi / Alice: I love pottery` (шум)
     - После: child = `[2023-06-27] Alice: I love pottery` (чисто)
2. Semicolon pattern `_ENUM_PATTERN_SEMI` добавлен (агрегации вида `A; B; C`)
3. `split_enumerations` сделан публичным (импортируется из `knowledge.py`)

**Hook в `KnowledgeBase.add()`:**
```python
fact = Fact(content=..., ...)
enrich_date_tags(fact)
all_facts = split_enumerations([fact])
# per-child dedup vs previously STORED facts only
# (не vs parent и не vs siblings — Jaccard prefix-артефакт ≈0.71)
for child in all_facts[1:]:
    if not is_near_dup(child, reference_window):
        enrich_date_tags(child)
        accepted_children.append(child)
facts.append(fact)
facts.extend(accepted_children)
```

**Важное решение:** дедупликация дочерних только vs ранее сохранённых фактов.
- Parent исключён: дети наследуют все его токены → Jaccard будет ≥0.7 → все дети подавились бы.
- Siblings исключены: у них общий date-prefix + verb → pairwise Jaccard ≈ 0.71 → 3 из 4 детей подавлялись.

**Файлы изменены:**
- `src/ai_knot/extractor.py` — `split_enumerations` (public), `_build_verb_prefix`, semicolon pattern
- `src/ai_knot/knowledge.py` — import + hook в `add()`
- `tests/test_extractor_enumeration.py` — +10 тестов (semicolon, dated-prefix, boundary trim)
- `tests/test_knowledge_enumeration.py` — новый файл, 13 integration тестов

---

## Aggregation — scope решение

Запрос пользователя: «не только enumeration но и сразу понять что это aggregation».

| Форма | Пример | Решение |
|-------|--------|---------|
| Comma ≥3 items | `A, B, C, D` | ✅ реализовано |
| Semicolon ≥3 items | `A; B; C` | ✅ реализовано |
| 2-item conjunction | `A and B` | ❌ high FP rate |
| Sentence parallelism | `Went to X. Visited Y. Ate Z.` | ❌ нужен LLM |
| Multi-subject | `Alice plays X; Bob sings` | ❌ verb_prefix нельзя шарить |

---

## Verification

```bash
# 849 tests pass, coverage 84%
pytest tests/ --ignore=tests/test_performance.py --ignore=tests/test_mcp_e2e.py -q

# npm rebuild done
cd npm && npm run build
```

**Benchmark commands (user запускает):**
```bash
cd aiknotbench
npx tsx src/index.ts run -r phase-c-v2-dated       --ingest-mode dated       --top-k 60 --force
npx tsx src/index.ts run -r phase-c-v2-raw         --ingest-mode raw         --top-k 60 --force
npx tsx src/index.ts run -r phase-c-v2-dated-learn --ingest-mode dated-learn --top-k 60 --force
```

---

## Ожидания

- **Cat2:** +3-5pp (C6c date tags → BM25F tag-weight 2.0)
- **Cat1 extraction_miss:** 9 → ≤6 (C6b v2 в dated/raw режимах)
- **answered_wrong_judge bucket (69% Cat1 wrongs):** не затронут — нужен Phase D
