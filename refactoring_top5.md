# Топ-5 файлов для рефакторинга

## 1. `src/ai_knot/knowledge.py` — 1517 строк
**Проблема:** файл совмещает несколько крупных зон ответственности: `KnowledgeBase`, pipeline обучения, recall, эпизодическую консолидацию и `SharedMemoryPool`.

**Что вынести:**
- `knowledge_base.py` — публичный API `KnowledgeBase`
- `learning_pipeline.py` — `learn`, `alearn`, `learn_async`
- `recall_service.py` — `_expand_query`, `_execute_recall`, `recall*`
- `episodic.py` — `add_episodic`, `consolidate_episodic`
- `shared_pool.py` — `SharedMemoryPool`

**Эффект:**
- меньше связности между LLM/extraction/storage/retrieval
- проще тестировать независимо
- ниже риск регрессий при изменении multi-agent логики

---

## 2. `tests/eval/benchmark/fixtures.py` — 2461 строка
**Проблема:** это гигантский “data dump” с EN/RU фикстурами, multi-agent сценариями и bundle-конфигурацией в одном модуле.

**Что вынести:**
- `fixtures_profile.py`
- `fixtures_dedup.py`
- `fixtures_consolidation.py`
- `fixtures_multi_agent.py`
- `fixtures_bundles.py`

**Лучший вариант:**
- большие наборы данных хранить в `json`/`yaml`
- в Python оставить только dataclass + loader

**Эффект:**
- модуль перестанет быть нечитаемым
- фикстуры станет проще расширять и ревьюить
- уменьшится шум в git diff

---

## 3. `tests/eval/datasets.py` — 3478 строк
**Проблема:** весь golden dataset зашит прямо в Python-код.

**Что вынести:**
- `tests/eval/data/retrieval_dataset_en.jsonl`
- `tests/eval/data/retrieval_dataset_ru.jsonl` или тематические чанки
- `datasets.py` оставить как loader + `RetrievalCase`

**Рефакторинг структуры:**
- хранить один case = одна запись
- валидировать схему при загрузке
- добавить helper `load_retrieval_dataset()`

**Эффект:**
- данные отделятся от логики
- легче обновлять датасет без правки кода
- проще делать генерацию/валидацию и сравнение версий датасета

---

## 4. `tests/eval/benchmark/runner.py` — 852 строки
**Проблема:** в одном месте находятся CLI, выбор backend’ов, orchestration, multi-agent path, long-run logic и serialization отчётов.

**Что вынести:**
- `benchmark_cli.py` — Click CLI
- `benchmark_executor.py` — `_run`, `_run_backend`, `_run_timed_scenario`
- `backend_factory.py` — `_build_backends_*`
- `scenario_factory.py` — `_build_scenarios`, `_bind_bundle`
- `reporting.py` — `_append_jsonl`, `_write_reports`, `_to_raw_json`

**Эффект:**
- проще добавлять новые backend’ы и режимы
- меньше условной логики в одном файле
- runner станет понятнее как orchestration layer

---

## 5. `src/ai_knot/storage/sqlite_storage.py` — 557 строк
**Проблема:** здесь смешаны schema definition, migrations, CRUD, snapshot logic и сериализация `Fact`.

**Что вынести:**
- `sqlite/schema.py` — DDL и индексы
- `sqlite/migrations.py` — миграции
- `sqlite/codec.py` — `Fact <-> row/dict`
- `sqlite/repository.py` — CRUD и temporal queries
- `sqlite/snapshots.py` — snapshot API

**Особенно стоит убрать дублирование:**
- `_build_rows`
- `_fact_from_row`
- `save_snapshot`
- `load_snapshot`

**Эффект:**
- единая точка сериализации `Fact`
- проще поддерживать миграции
- меньше шансов сломать snapshot/storage совместимость
