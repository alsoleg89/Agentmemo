# `ai_knot` newgen: целевая архитектура после последнего коммита

**Дата:** 2026-04-14  
**Scope:** только target architecture для `ai-knot` после последнего коммита, строго от baseline `dated ≈ 40/46/46/84` по `Cat1/Cat2/Cat3/Cat4`.  
**Не делаем:** не строим MVP-режимы, не делаем `dated-learn` core path, не меняем промпты как основной рычаг качества.  
**Что сохраняем:** совместимость с текущим `KnowledgeBase`, `recall()`, `snapshot()/restore()`, текущими benchmark run-ами и legacy storage.

---

## Контекст и baseline

Текущее состояние после последнего коммита уже показывает, что проблема не в «чистом retrieval».  
Стабильный ориентир для целевой архитектуры — `dated` baseline примерно:

- `Cat1 ≈ 40%`
- `Cat2 ≈ 46%`
- `Cat3 ≈ 46%`
- `Cat4 ≈ 84%`

Это важно по двум причинам:

1. `Cat1–Cat3` ещё далеко от цели `70%`, поэтому нужна не косметика, а смена ответа-ориентированного контура.
2. `Cat4` уже высок, значит архитектура не должна ломать narrative path и не должна переусложнять open-ended сценарии.

Текущий кодовый путь остаётся retrieval-centric:

- `KnowledgeBase._execute_recall()` в `src/ai_knot/knowledge.py:572` собирает кандидатов, ранжирует их и только потом отдаёт текстовый контекст.
- `recall_facts_with_trace()` в `src/ai_knot/knowledge.py:1161` даёт хороший trace для отладки retrieval, но ещё не trace для answer construction.
- `aiknotbench/src/aiknot.ts:51` в `dated` режиме сейчас строит 3-turn windows, то есть benchmark ingest всё ещё делает плоский текстовый суррогат, а не raw-эпизоды как первичную память.

Целевая архитектура должна сдвинуть центр тяжести:

`raw episodes -> atomic claims -> support bundles -> query contract -> deterministic operators -> answer`

---

## 1) Что и зачем меняем

### Что меняем концептуально

Мы заменяем модель «сначала собери top-k context, потом пусть LLM сам разберётся» на модель **contract-first answer engine**.

Три главные причины:

1. **`Cat1`** страдает от неполного перечисления и агрегации: проблема не в том, что факт не найден, а в том, что ответ не строится как set-операция.
2. **`Cat2`** страдает от смешения временных осей: `session date`, `event time`, `validity time`, `observed_at` должны быть явными и не конкурировать на уровне плоского контекста.
3. **`Cat3`** страдает от отсутствия bounded inference: система должна уметь не только искать факты, но и выбирать стратегию доказательного вывода (`yes/no/uncertain`, `ranked candidates`, `state reconstruction`).

### Что меняем в продукте

`ai-knot` становится не «обёрткой над поиском фактов», а **объяснимым memory engine**, который:

- хранит raw-источник как первичную истину,
- материализует атомарные claims,
- строит вспомогательные bundles для быстрого и компактного поиска,
- выбирает стратегию ответа по `QueryFrame` и `EvidenceProfile`,
- отдаёт либо структурированный ответ, либо narrative render без изменения промптов.

### Что не меняем

- Не вводим `inferential intent` по surface words.
- Не делаем benchmark-named runtime branches.
- Не кодируем `would/likely/might` как policy.
- Не превращаем `dated-learn` в core path.
- Не переписываем промпты как основной механизм улучшения.

### Current vs To-Be

**Сейчас:**

`dated sessions -> 3-turn windows / flat facts -> recall(top-k) -> prompt -> answer`

**Будет:**

`dated raw episodes -> atomic claims -> support bundles -> query contract -> operator -> answer + trace`

### Что это даёт для целевой метрики

При baseline `40/46/46/84` цель `70/70/70` по `Cat1–Cat3` выглядит реалистичной только если:

- `Cat1` получает set-aware answer path,
- `Cat2` получает first-class time model,
- `Cat3` получает bounded hypothesis / candidate ranking path,
- `Cat4` остаётся на narrative path и не теряет текущую силу.

---

## 2) Конкретные изменения по файлам / функциям / коду

Ниже — **целевая** карта изменений. Это не MVP-фаза; это конечный каркас.

### `src/ai_knot/knowledge.py`

**Текущая роль:** retrieval-centric public API (`recall`, `recall_facts`, `snapshot`, `restore`, `decay`).  
**Новая роль:** главный product API для `query()` поверх legacy compatibility.

Что добавить:

- `ingest_episode(...)`
  - принимает `RawEpisode`-уровень данных: `session_id`, `turn_id`, `speaker`, `observed_at`, `raw_text`, `source_meta`.
  - пишет raw как source of truth, без оконных суррогатов.
- `ingest_episodes(...)`
  - batch-ingest raw episodes.
- `query(...) -> QueryAnswer`
  - primary product API.
  - использует `QueryFrame`, `AnswerContract`, `EvidenceProfile`, `StrategyChooser`.
- `query_json(...) -> dict[str, Any]`
  - MCP / benchmark friendly structured payload.
- `rebuild_materialized(...)`
  - детерминированный rebuild claims/bundles из raw.
- `explain_query(...)`
  - debug helper, возвращает trace + chosen strategy.

Что оставить как legacy:

- `recall()` и `recall_facts()` остаются для обратной совместимости.
- `recall_facts_with_trace()` остаётся полезным retrieval trace, но не как final answer trace.
- `snapshot()/restore()` не удаляем, а расширяем на новые plane-ы.

Что важно не сделать:

- не расширять `_execute_recall()` в новый универсальный answer router;
- не смешивать legacy recall-trace и new query-trace в один неявный объект.

### `src/ai_knot/query_types.py` — новый файл

Вынести сюда query-specific типы, не раздувая `types.py`.

Минимальный набор:

- `RawEpisode`
- `AtomicClaim`
- `SupportBundle`
- `QueryFrame`
- `AnswerContract`
- `EvidenceProfile`
- `AnswerItem`
- `AnswerTrace`
- `QueryAnswer`

Почему отдельный файл:

- `src/ai_knot/types.py:1` уже несёт legacy memory model (`Fact`, `ConversationTurn`, `SnapshotDiff`, `Provenance`, `ConflictPolicy`).
- newgen-слой не должен превращать `Fact` в «god object».

### `src/ai_knot/query_contract.py` — новый файл

Отвечает за анализ вопроса и выбор контракта ответа.

Функции:

- `analyze_query(question: str) -> QueryFrame`
- `derive_answer_contract(frame: QueryFrame) -> AnswerContract`

`QueryFrame` должен описывать **геометрию вопроса**, а не benchmark label:

- `focus_entities`
- `target_kind` (`state | relation | location | identity | event | set | scalar | description`)
- `answer_space` (`bool | entity | set | scalar | description`)
- `temporal_scope` (`current | historical | interval`)
- `epistemic_mode` (`direct | reconstruct | ranked | hypothesis | narrative`)
- `locality` (`point | entity_scope | event_neighborhood | cross_entity`)
- `evidence_regime` (`single | aggregate | support_vs_contra`)

### `src/ai_knot/materialization.py` — новый файл

Отвечает за детерминированную материализацию атомарных claims из raw.

Функции:

- `materialize_episode(raw: RawEpisode) -> list[AtomicClaim]`
- `materialize_claims(raw_episodes: list[RawEpisode]) -> list[AtomicClaim]`
- `rebuild_claims_from_raw(...)`

Materializer должен извлекать generic claim-типы:

- `StateClaim`
- `RelationClaim`
- `EventClaim`
- `DescriptorClaim`
- `IntentClaim`
- `DurationClaim`
- `TransitionClaim`

Ключевая идея:

- claims должны быть **rebuildable**;
- claims не должны хранить ответ как готовую фразу;
- claims должны сохранять provenance на raw episode / turn / source span.

### `src/ai_knot/support_bundles.py` — новый файл

Отвечает за coarse-to-fine retrieval поверх claims.

Bundles:

- `EntityTopicBundle`
- `StateTimelineBundle`
- `EventNeighborhoodBundle`
- `RelationSupportBundle`

Функции:

- `build_entity_topic_bundles(...)`
- `build_state_timeline_bundles(...)`
- `build_event_neighborhood_bundles(...)`
- `build_relation_support_bundles(...)`

Требование:

- bundle хранит `member_claim_ids`, а не дублирует raw text;
- bundle score рассчитывается из member claims, а не как независимая truth.

### `src/ai_knot/query_operators.py` — новый файл

Здесь живут deterministic answer operators.

Функции:

- `exact_state(...)`
- `set_collect(...)`
- `time_resolve(...)`
- `candidate_rank(...)`
- `bounded_hypothesis_test(...)`
- `narrative_cluster_render(...)`

### `src/ai_knot/query_runtime.py` — новый файл

Один orchestration слой, который связывает contract, bundles, claims и operator.

Функции:

- `retrieve_support(...)`
- `expand_support(...)`
- `build_evidence_profile(...)`
- `choose_strategy(...)`
- `execute_query(...)`

### `src/ai_knot/storage/base.py`

Добавить optional protocols для новых planes:

- `RawEpisodeStore`
- `ClaimStore`
- `BundleStore`
- `MaterializationStore`

Если хочется минимизировать поверхность, можно оставить это как internal storage contract в `KnowledgeBase`, но тогда SQLite/YAML реализации должны поддерживать одинаковый shape.

### `src/ai_knot/storage/sqlite_storage.py`

Добавить новые таблицы:

- `raw_episodes`
- `atomic_claims`
- `support_bundles`
- `bundle_members`
- `materialization_meta`

Также добавить индексы:

- по `agent_id`, `session_id`, `turn_id`
- по `entity`, `attribute`, `claim_type`
- по `bundle_type`, `topic`, `salience`
- по `source_episode_id`

`facts` таблицу не удалять — она остаётся legacy compatibility layer.

### `src/ai_knot/storage/yaml_storage.py`

Если YAML backend остаётся поддерживаемым, ему нужна зеркальная сериализация новых planes.

Практическое правило:

- YAML может быть медленнее SQLite,
- но должен сохранять корректность snapshot/restore/rebuild,
- и должен уметь round-trip для `RawEpisode`, `AtomicClaim`, `SupportBundle`.

### `src/ai_knot/forgetting.py`

Разделить:

- `truth validity`
- `salience`
- `archive policy`

`apply_decay()` в новом мире не должен «стирать истину».  
Он должен:

- снижать salience,
- влиять на retrieval priority,
- не удалять raw,
- не ломать valid windows.

### `src/ai_knot/_query_intent.py`

Оставить только retrieval-router для legacy `recall()` и pool retrieval.

Запрет:

- не использовать эту классификацию как answer policy;
- не добавлять сюда keyword-based inferential ветки;
- не кодировать `would/likely/might` как ядро решения.

### `src/ai_knot/mcp_server.py` и `src/ai_knot/_mcp_tools.py`

Добавить MCP tools:

- `query`
- `query_json`
- `rebuild_materialized`
- `stats_query`
- `explain_query` — опционально, для debug/ops

### `aiknotbench/src/aiknot.ts`

`dated` ingest сейчас строит sliding windows; это нужно заменить на ingest raw episodes.

Текущая логика:

- `ingestDated()` делает 3-turn window и передаёт его как строку.

Целевая логика:

- `ingestDated()` создаёт raw episode на каждый turn с `observed_at` / `session_date`;
- `dated-learn` остаётся только как сравнение/optional enrichment, не как core path;
- benchmark adapter должен уметь работать через `query()` вместо только `recall()`.

### `aiknotbench/src/runner.ts`

Добавить режимы:

- `legacy_recall`
- `target_query`

Идея:

- старый контур остаётся для regression сравнения;
- новый контур измеряет сам target answer engine;
- judge может получать либо `QueryAnswer.text`, либо structured answer render.

### `tests/*`

Добавить новый набор тестов под query runtime, materialization, bundles, decay и restore.

---

## 3) API, кодовые сниппеты и псевдокод операторов

### Новый public API

```python
answer = kb.query(
    "What activities does Melanie do with her family?",
    top_k=60,
)

print(answer.text)
print(answer.confidence)
print(answer.trace.strategy)
```

### Типы ответа

```python
@dataclass(slots=True)
class QueryAnswer:
    text: str
    items: list[AnswerItem]
    confidence: float
    trace: AnswerTrace
```

```python
@dataclass(slots=True)
class QueryFrame:
    focus_entities: list[str]
    target_kind: str
    answer_space: str
    temporal_scope: str
    epistemic_mode: str
    locality: str
    evidence_regime: str
```

```python
@dataclass(slots=True)
class AnswerContract:
    answer_space: str
    truth_mode: str
    time_axis: str
    locality: str
    evidence_regime: str
```

### Query runtime

```python
def query(self, question: str, *, top_k: int = 60, now: datetime | None = None) -> QueryAnswer:
    frame = analyze_query(question)
    contract = derive_answer_contract(frame)

    bundles = retrieve_support(self._agent_id, question, frame, contract, now=now)
    claims = expand_support(bundles, contract)
    profile = build_evidence_profile(claims, bundles, contract)

    strategy = choose_strategy(frame, contract, profile)
    result = execute_query(strategy, claims, bundles, contract, profile)

    return result
```

### `set_collect` псевдокод

```python
def set_collect(claims, contract):
    items = []
    seen = set()
    for claim in claims:
        if claim.kind not in {"StateClaim", "EventClaim", "RelationClaim"}:
            continue
        key = (claim.subject, claim.relation, claim.value_text)
        if key in seen:
            continue
        seen.add(key)
        items.append(claim)
    return items
```

Что важно:

- разные значения под одним и тем же `slot_key` не должны схлопываться, если вопрос — list/set;
- дедупликация должна быть семантической, а не только lexical.

### `time_resolve` псевдокод

```python
def time_resolve(claims, contract):
    if contract.time_axis == "event":
        primary_axis = "event_time"
    elif contract.time_axis == "current":
        primary_axis = "validity_window"
    else:
        primary_axis = "event_time_then_validity"

    ordered = sort_claims_by_axis(claims, primary_axis)
    return select_best_temporal_view(ordered)
```

Ключевая идея:

- `session_date` не должен выигрывать у `event_time` просто потому, что он был lexical-heavy;
- `observed_at` и `validity` должны оставаться отдельными осями.

### `candidate_rank` псевдокод

```python
def candidate_rank(claims, contract):
    scored = []
    for claim in claims:
        score = (
            explicitness_bonus(claim)
            + support_bonus(claim)
            + proximity_bonus(claim, contract.focus_entities)
            - contradiction_penalty(claim)
        )
        scored.append((claim, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)
```

### `bounded_hypothesis_test` псевдокод

```python
def bounded_hypothesis_test(claims, contract):
    support = sum(weight(c) for c in claims if c.polarity == "support")
    contra = sum(weight(c) for c in claims if c.polarity == "contra")
    ambiguity = estimate_ambiguity(claims)

    score = support - contra - ambiguity
    if abs(score) < contract.uncertainty_threshold:
        return AnswerItem(value="uncertain", confidence=0.5)
    return AnswerItem(value="yes" if score > 0 else "no", confidence=sigmoid(abs(score)))
```

### `narrative_cluster_render`

Нарративный путь остаётся совместимым с текущим prompt-стеком:

- structured answer решается детерминированно;
- narrative rendering может использовать существующий промпт без изменений;
- промпт не должен быть единственным местом reasoning.

---

## 4) Тестирование

Тестирование должно проверять не только correctness ответа, но и **выбор стратегии**, **trace**, **restore/rebuild** и **анти-overfit поведение**.

### 4.1 Unit tests

#### `tests/test_query_contract.py`

Проверяет, что вопрос переводится в правильный `QueryFrame` и `AnswerContract`.

Примеры:

- `"What activities does Melanie partake in?"` -> `answer_space=set`, `evidence_regime=aggregate`
- `"When did Melanie sign up for pottery?"` -> `time_axis=event`
- `"Would Caroline likely pursue writing?"` -> `truth_mode=hypothesis`

#### `tests/test_materialization.py`

Проверяет детерминированную материализацию claims из raw.

Примеры:

- raw turn с датой и событием -> `EventClaim`
- raw turn с устойчивым свойством -> `StateClaim`
- повторный rebuild из тех же raw episodes даёт тот же набор claims

#### `tests/test_support_bundles.py`

Проверяет bundle grouping и стабильность membership.

Примеры:

- scattered family-activity claims попадают в один `EntityTopicBundle`
- chronologically related facts формируют `StateTimelineBundle`
- adjacent turn-ы и их claim-ы связываются в `EventNeighborhoodBundle`

#### `tests/test_query_operators.py`

Проверяет операторы по отдельности.

Примеры:

- `set_collect()` возвращает все элементы, а не первый совпавший;
- `time_resolve()` предпочитает `event_time` над `session_date`;
- `candidate_rank()` отдаёт explicit evidence выше weak semantic neighbors;
- `bounded_hypothesis_test()` возвращает `uncertain`, если support и contra близки.

#### `tests/test_query_runtime.py`

Проверяет end-to-end routing.

Примеры:

- одинаковый surface query маршрутизируется по-разному при разном evidence profile;
- trace содержит `frame`, `contract`, `bundle_ids`, `claim_ids`, `strategy`, `operator`.

#### `tests/test_query_trace.py`

Проверяет полноту и стабильность trace.

Trace должен включать:

- `question`
- `frame`
- `contract`
- `retrieved_bundle_ids`
- `expanded_claim_ids`
- `evidence_profile`
- `strategy`
- `operator`
- `decision`
- `confidence`

#### `tests/test_query_decay.py`

Проверяет, что decay меняет salience, а не truth.

Примеры:

- procedural claims не теряют pinned-статус;
- inactive event claims не исчезают из raw;
- bundle score пересчитывается из member claims.

#### `tests/test_query_restore.py`

Проверяет, что restore/rebuild восстанавливает все planes.

Примеры:

- snapshot restore возвращает raw + claims + bundles в согласованное состояние;
- rebuild после очистки materialized tables воспроизводит идентичный результат.

### 4.2 Integration tests

#### `tests/test_query_end_to_end.py`

Покрывает четыре основных сценария:

1. **Cat1 aggregation**
   - запрос вида: `"What activities does Melanie do with her family?"`
   - ожидаем: полный set, без остановки на первых 1–2 совпадениях
2. **Cat2 temporal**
   - запрос вида: `"When did Melanie sign up for a pottery class?"`
   - ожидаем: `event_time`, не `session_date`
3. **Cat3 hypothesis**
   - запрос вида: `"Would Caroline be considered religious?"`
   - ожидаем: `yes/no/uncertain` с trace support-vs-contra
4. **Cat4 narrative / local detail**
   - запрос вида: `"What kind of pot did they make with clay?"`
   - ожидаем: local evidence neighborhood, не случайный nearby fact

### 4.3 Trace-first regression tests

Нужно отдельное тестирование trace bucket-ов, чтобы видеть, где именно теряется качество:

- `frame_error`
- `materialization_miss`
- `bundle_miss`
- `strategy_error`
- `operator_error`
- `render_gap`

Это прямой наследник текущего retrieval trace, но с новой семантикой.

### 4.4 Acceptance criteria по тестам

- Все `QueryFrame`-тесты проходят без знания benchmark categories внутри runtime.
- Все operator-тесты проходят на synthetic product queries.
- Trace покрывает выбор стратегии.
- `restore()` и `rebuild_materialized()` взаимно совместимы.
- Legacy `recall()` не ломается.

---

## 5) Требования по эффективности

### Память

Цель — не дублировать raw text в каждом слое.

Правила:

- `RawEpisode` хранит полный исходник.
- `AtomicClaim` хранит минимальный нормализованный слот + provenance.
- `SupportBundle` хранит только `member_claim_ids`, scores и компактные индексы.
- Не писать raw turn body в bundle tables.

Практический бюджет:

- materialized planes должны быть pointer-heavy, а не text-heavy;
- bundle tables должны быть заметно компактнее raw plane;
- rebuild должен быть возможен без дополнительной внешней памяти сверх индекса.

### Токены

Главная экономия — не пихать топ-60 текстовых кусков в prompt.

Ожидаемый эффект:

- structured queries для `Cat1–Cat3` уходят в короткий answer package;
- prompt context уменьшается до минимального render-only слоя;
- narrative fallback использует уже собранные claim summaries, а не длинный raw dump.

Практический бюджет:

- structured path должен обходиться **без** LLM на query time;
- для narrative fallback LLM получает только релевантный evidence neighborhood, а не полный retrieval dump;
- токенов на structured ответы должно быть существенно меньше, чем в текущем `recall(top_k=60)` пути.

### Скорость

Цель — сместить работу из query-time в ingest/rebuild-time.

Практика:

- query-time:
  - `frame` + `contract`
  - lookup по bundles / claims
  - operator execution
- ingest/rebuild-time:
  - materialization
  - bundle building
  - index refresh

Пороговые ожидания:

- structured query path должен быть сопоставим с текущим recall path или быстрее;
- rebuild может быть тяжелее, но он offline / async;
- Cat1/Cat2/Cat3 не должны требовать LLM call, если contract уже определён и evidence достаточно.

### Структурная эффективность

Правило хорошего дизайна:

- один raw episode -> несколько claims -> несколько bundle refs,
- а не один raw episode -> много дублированных windows.

Если вдруг storage footprint начинает расти быстрее качества — это признак, что bundle layer повторяет raw text вместо compact provenance.

---

## 6) Инфраструктурная обвязка

### Storage

Текущий storage уже умеет `facts` и `snapshots` в `src/ai_knot/storage/sqlite_storage.py:1`.

Новая архитектура требует:

- versioned schema migration;
- raw + claims + bundles как отдельные таблицы;
- совместимость с legacy `facts`.

### Snapshot / Restore

Нужно различать два режима:

1. **Fast restore**
   - восстанавливаем raw + materialized snapshot как единый consistent state;
2. **Rebuild restore**
   - восстанавливаем только raw;
   - затем вызываем `rebuild_materialized()`.

Требование:

- `restore()` должен гарантировать консистентность всех planes;
- `rebuild_materialized()` должен быть детерминированным и идемпотентным.

### Rebuild

`rebuild_materialized()` должен уметь:

- rebuild all planes for an agent;
- rebuild from raw only;
- rebuild scope-частично, если повреждён только один bundle type.

Рекомендуемая meta-таблица:

- `schema_version`
- `materialization_version`
- `source_revision`
- `bundle_revision`
- `last_rebuild_at`
- `rebuild_status`

### MCP

`src/ai_knot/mcp_server.py:179` и `src/ai_knot/_mcp_tools.py:173` должны получить новые инструменты:

- `query`
- `query_json`
- `rebuild_materialized`
- `stats_query`
- `explain_query`

Что важно:

- `query_json` должен возвращать trace-friendly структурированный ответ;
- `query` может возвращать человекочитаемый текст + краткий summary;
- legacy `recall` и `learn` не удаляются сразу.

### Benchmark adapter

`aiknotbench/src/aiknot.ts:51` и `aiknotbench/src/runner.ts:167` должны уметь работать в двух режимах:

- `legacy_recall`
- `target_query`

Практически:

- `dated` ingest больше не должен быть 3-turn window суррогатом;
- `dated` должен писать raw episodes;
- `runner.ts` должен уметь сравнивать старый и новый путь без изменения dataset/judge.

### Observability

Новые метрики, которые должны быть доступны в trace / logs:

- coverage по bundles;
- число expanded claims;
- выбранный strategy / operator;
- number of support vs contra claims;
- query latency;
- rebuild latency;
- token budget;
- `restore()` consistency check.

### Compatibility rule

`pool.py` и shared-memory semantics не должны ломаться.

Требование:

- новые claims обязаны сохранять `slot_key`, `claim_key`, `valid_from`, `valid_until`, `version`;
- shared pool CAS по-прежнему должен понимать стабильные structured claims;
- newgen не должен требовать переписывания всего multi-agent слоя в первой же итерации.

---

## 7) Как должен работать decay

### Главный принцип

**Decay меняет salience, а не truth.**

Это критично:

- истина не должна исчезать только потому, что факт давно не открывали;
- retrieval priority может падать;
- validity / provenance / history должны оставаться восстановимыми.

### По слоям

#### `RawEpisode`

- не decay’ится как truth record;
- может архивироваться;
- не должен удаляться только по времени;
- допускается cold storage, но не потеря.

#### `AtomicClaim`

- truth validity живёт отдельно от salience;
- `state_claim` обычно живёт дольше;
- `event_claim` может терять salience быстрее;
- `descriptor_claim` / `intent_claim` часто требуют более агрессивного decay, если нет подтверждения.

#### `SupportBundle`

- bundle score вычисляется из member claims;
- если member claim salience падает, bundle score тоже падает;
- bundle не имеет отдельной truth, только retrieval relevance.

#### `Procedural claims`

- должны быть pinned или почти pinned;
- decay допускается только как weak salience change, но не как забывание.

### Как это должно выглядеть в коде

`src/ai_knot/forgetting.py:128` должен быть переосмыслен так:

- `calculate_retention()` остаётся compatibility-слоем,
- но новый слой вводит отдельно:
  - `calculate_salience(...)`
  - `calculate_truth_validity(...)`
  - `archive_policy(...)`

Переходный принцип:

- legacy `Fact.retention_score` можно продолжить обновлять для обратной совместимости;
- newgen query path должен опираться на `salience`, `validity`, `bundle_score`;
- retrieval priority не должна смешиваться с truth status.

### Практическая политика decay

1. **Не удалять raw** автоматическим decay.
2. **Не удалять claims** без явной archive policy.
3. **Bundle-ы** пересчитывать, а не “верить” старому score.
4. **Pinned claims** не забывать.
5. **Validity** не трогать decay-ем.

### Что это даёт продукту

- пользователи не теряют историю;
- система меньше галлюцинирует из-за «забытого» evidence;
- можно объяснить, почему что-то стало менее релевантным, не утверждая, что оно стало ложным.

---

## 8) Restrictions / guardrails: как не скатиться в LoCoMo-overfit

### Жёсткие ограничения

1. **Никаких runtime branch-ей по `Cat1/Cat2/Cat3/Cat4`.**
   - Эти ярлыки существуют только в evaluation layer.
2. **Никаких keyword policies по `would/likely/might/when`.**
   - Surface words — только weak signal внутри `QueryFrame`, не policy.
3. **Никаких answer-shaped helper labels.**
   - Запрещены конструкции вроде `ally_or_not`, `future_role`, `persona_trait` как runtime primitive.
4. **Никаких benchmark-specific truth classes.**
   - Truth должен следовать из evidence, а не из формата gold answer.
5. **Никаких prompt hacks как главного улучшения.**
   - Промпт можно оставить для narrative render, но не для reasoning core.
6. **Никакой потери provenance.**
   - Каждый claim должен быть rebuildable до raw episode / turn / span.

### Проверка на overfit

Каждый новый тип, индекс или оператор должен проходить тест:

**Можно ли назвать минимум 3 продуктовых кейса вне LoCoMo, где это нужно?**

Если нельзя — это, скорее всего, LoCoMo-shaped overfit.

### Что считается product capability

Product capability — это слой, который полезен вне benchmark:

- current state query,
- timeline query,
- list / set answer,
- bounded hypothesis answer,
- explainable evidence trace.

### Что считается overfit

Overfit — это слой, который:

- знает benchmark category,
- знает gold format,
- знает surface keywords,
- живёт только для одного dataset family.

### Guardrails по реализации

- `src/ai_knot/_query_intent.py` остаётся retrieval-only.
- `src/ai_knot/types.py` не превращается в свалку query-типов.
- `dated-learn` не становится production default.
- `query()` должен работать полезно даже без LLM на query time.
- `trace` должен объяснять решение через evidence chain, а не через category label.

### Как распознать плохой дифф

Плохой дифф выглядит так:

- «если query содержит `would`, включить inferential branch»;
- «если query начинается с `when`, сделать special temporal hack»;
- «если в question есть activity-list semantics, вернуть заранее зашитый answer shape».

Это надо отвергать, даже если короткий benchmark gain выглядит соблазнительно.

---

## Open Questions

1. `RawEpisode` лучше хранить как turn-level объект или как session-level envelope с turn children?
2. `SupportBundle` строим eagerly на ingest или lazily при первом query?
3. `query()` должен возвращать строго версионированный JSON schema сразу или достаточно text + trace для старта?
4. `restore()` восстанавливает только raw или всегда raw + materialized planes?
5. Где лучше держать `trace`: в `KnowledgeBase` или отдельном `QueryTrace` модуле?
6. Нужен ли в первом релизе отдельный `explain_query()` MCP tool, или хватит `query_json()`?
7. Какой минимум `dated-learn` допустим как future uplift, не затрагивая core path?

---

## Review — Архитектор

**Вердикт:** план сильный и системный.

- Самое правильное решение — не наращивать ещё один retrieval branch, а выделить новый answer runtime.
- Хорошо, что `recall()` сохраняется как legacy path, а `query()` становится новым product API.
- Правильный structural split: `raw -> claims -> bundles -> contract -> operator`.
- Особенно сильная часть — явное разделение truth, salience и render path.

**Что архитектор бы держал под контролем:**

- не раздувать `AtomicClaim` в десятки специальных подтипов;
- не превращать `SupportBundle` в скрытый answer cache;
- не смешивать schema evolution legacy `facts` и new planes без versioned migration;
- не допустить, чтобы `query_runtime.py` превратился в god module.

**Архитектурный вывод:**  
если держать operator core маленьким, это выглядит как хорошая target architecture, а не как набор разрозненных улучшений.

---

## Review — Критик

**Вердикт:** план правильный, но риск complexity inflation высокий.

- Самый большой риск — слишком много новых сущностей одновременно: raw episodes, claims, bundles, contracts, profiles, operators, traces, rebuild jobs.
- Второй риск — optimistic assumption, что materialization будет достаточно чистой для `Cat3`.
- Третий риск — benchmark adapter migration может оказаться сложнее, чем кажется, потому что нынешний runner заточен под `recall() -> context -> answerFn`.

**Что критик бы потребовал:**

- жёстко определить минимальный final operator set и запретить его расползание;
- ввести migration invariant: любой answer должен быть rebuildable из raw;
- заранее описать rollback plan, если `query()` path временно уступает `recall()` на части сценариев;
- явно померить storage growth и rebuild latency, а не считать их “приемлемыми по умолчанию”.

**Критический вывод:**  
цель достижима, но только если команда удержит дисциплину и не даст architecture drift съесть выигрыш.

---

## Review — Пользователь продукта

**Вердикт:** это выглядит полезно именно потому, что меняется результат, а не только внутренняя схема.

Что пользователь реально почувствует:

- списки станут полнее;
- временные ответы станут надёжнее;
- inference перестанет быть “магией prompt-а”;
- появится понятный trace, почему ответ именно такой;
- память станет меньше похожа на поиск по заметкам и больше — на надёжный слой знаний.

Что пользователь не должен заметить:

- сложности новых planes;
- rebuild jobs;
- storage migrations;
- внутренние distinctions между `raw`, `claim`, `bundle`.

**Пользовательский вывод:**  
если это сделано хорошо, продуктово это ощущается как переход от “иногда находит полезный контекст” к “обычно даёт правильный тип ответа”.
