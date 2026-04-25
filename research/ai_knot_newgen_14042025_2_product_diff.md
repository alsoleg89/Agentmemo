# ai-knot newgen 14042025 — продуктовый дифф после новой архитектуры

## Кратко

Новая архитектура ai-knot меняет сам класс продукта. Сейчас ai-knot выглядит как **retrieval-heavy memory system**: он хорошо хранит, ищет и частично ранжирует воспоминания/факты. После реализации целевой архитектуры он становится **answer-contracted memory engine**: системой, которая не просто находит контекст, а строит ответ по контракту, по типу вопроса, по типу evidence и по структуре памяти.

Это важный сдвиг:

- из “search your memory” → в “ask your memory a typed question”
- из “top-k facts” → в “evidence-aware answer plan”
- из “LLM sees context” → в “deterministic answer operators over evidence”
- из benchmark-oriented retrieval → в product-oriented memory reasoning

Ниже — глубокий разбор того, чем такой ai-knot отличается от конкурентов, какие новые user outcomes появятся, где мы commodity, где novel, и как это упаковать в продукт и go-to-market без overclaim.

---

## 1) Текущее позиционирование vs целевое

### Сейчас

Текущий ai-knot по сути продаёт и реализует следующее:

- гибридный retrieval over memory
- recall по raw / dated / learned evidence
- поддержку vector + BM25 + entity-hop + rerank
- traceable retrieval path

Это уже сильная база, но продуктово это всё ещё читается как:

> “Мы хорошо ищем память”

Для пользователя это полезно, но недостаточно дифференцировано. В реальном опыте он хочет не поиск ради поиска, а:

- “что сейчас правда?”
- “что здесь наиболее вероятно?”
- “когда именно это произошло?”
- “что нужно перечислить полностью?”
- “почему ты так считаешь?”

То есть пользователь покупает **ответ**, а не retrieval.

### Целевое позиционирование

После новой архитектуры ai-knot должен позиционироваться как:

> **Explainable memory substrate that produces typed, evidence-grounded answers over long-lived conversations and agent memory.**

Ключевые слова здесь:

- explainable
- evidence-grounded
- typed answers
- long-lived conversations
- agent memory

Это уже не просто memory search engine. Это memory system, которая умеет:

- различать тип вопроса;
- строить контракт ответа;
- выбирать стратегию ответа;
- возвращать trace;
- сохранять provenance;
- масштабироваться в multi-agent memory.

### Что меняется в восприятии продукта

До:

- “Удобный memory layer”
- “Ещё один retriever”
- “Поиск по чатам / фактам / эпизодам”

После:

- “Memory can answer like a system, not like a prompt”
- “Typed answers with trace”
- “State, time, list, inference — all first-class”
- “Shared memory for agents and teams”

Это уже другая категория.

---

## 2) Value proposition

### Основная ценность

Ценность новой архитектуры не в том, что она “находит больше текста”. Ценность в том, что она:

1. **снижает энтропию ответа** — меньше случайности, меньше prompt sensitivity;
2. **повышает полноту ответа** — особенно в list/aggregation вопросах;
3. **улучшает temporal correctness** — разделяет event time, observed time, validity time;
4. **делает inference bounded and auditable** — не “галлюцинирует reasoning”, а проверяет гипотезу по evidence;
5. **сохраняет explainability** — всегда можно показать, на чём построен ответ.

### Что получает пользователь

- меньше “я не уверен” там, где evidence есть;
- меньше неполных списков;
- меньше ошибок по датам и временным ссылкам;
- более честные ответы в uncertain cases;
- понятный trace “почему система ответила так”.

### Что получает продукт

- более высокий trust;
- более широкий класс задач;
- возможность продавать memory как capability, а не как инфраструктуру;
- лучшую историю для enterprise и agentic workflows;
- основу для future multi-agent memory и trust-aware memory.

### Формула value prop

**We don’t just retrieve memory. We contract, select, and verify the answer from memory.**

Это важно для позиционирования: продукт не обещает “всезнание”, он обещает **structured answer reliability**.

---

## 3) Конкурентный анализ

Ниже — анализ по локальным research docs:

- Mem0 — `/Users/alsoleg/Documents/github/ai-knot/research/competitors/01_mem0.md`
- Letta — `/Users/alsoleg/Documents/github/ai-knot/research/competitors/02_letta.md`
- Zep / Graphiti — `/Users/alsoleg/Documents/github/ai-knot/research/competitors/03_zep_graphiti.md`
- Cognee — `/Users/alsoleg/Documents/github/ai-knot/research/competitors/04_cognee.md`
- Supermemory — `/Users/alsoleg/Documents/github/ai-knot/research/competitors/05_supermemory.md`
- Hindsight — `/Users/alsoleg/Documents/github/ai-knot/research/competitors/06_hindsight.md`
- Comparison table — `/Users/alsoleg/Documents/github/ai-knot/research/competitors/00_comparison_table.md`

### 3.1 Mem0

**Сильная сторона**

- vector-first retrieval;
- graph enrichment for related entities;
- practical product packaging;
- хороший entry point для “memory for apps”.

**Слабое место**

- graph используется как side-channel enrichment, а не как полноценный answer planner;
- нет temporal reasoning как first-class answer contract;
- нет явного bounded inference;
- нет post-extraction consolidation как системного преимущества.

**Что у них commodity**

- vector similarity;
- graph enrichment;
- hybrid retrieval.

**Где ai-knot может быть лучше**

- answer contract вместо pure recall;
- typed answer operators;
- stronger time semantics;
- support bundles for set/aggregation queries.

### 3.2 Letta

**Сильная сторона**

- agentic self-search;
- LLM decides when and how to search;
- удобная agent story;
- сильная mental model для developers.

**Слабое место**

- intelligence lives in agent loop, not in memory substrate;
- retrieval itself не даёт сильной гарантии на полноту, time, inference;
- memory behavior зависит от agent behavior.

**Что у них commodity**

- memory search;
- hybrid search;
- developer ergonomics for agent loops.

**Где ai-knot может быть лучше**

- answers do not depend on agent improvisation;
- evidence-aware routing inside the memory layer;
- deterministic operators;
- better auditability for enterprise and product memory.

### 3.3 Zep / Graphiti

**Сильная сторона**

- best graph-retrieval completeness among mainstream competitors;
- BFS + BM25 + semantic + bi-temporal;
- strong for entity traversal and event coherence.

**Слабое место**

- graph-centric retrieval is still not the same as answer-contracted reasoning;
- binary-edge graph remains the core abstraction;
- no explicit answer contract / typed response planning.

**Что у них commodity**

- hybrid retrieval;
- temporal validity;
- entity traversal.

**Где ai-knot может быть лучше**

- post-extraction consolidation;
- coarse-to-fine support bundles;
- answer planning as first-class runtime;
- less dependence on graph traversal as the main product idea.

### 3.4 Cognee

**Сильная сторона**

- many retrieval modes;
- LLM-to-Cypher is flexible;
- can adapt to graph databases;
- memify introduces adaptive pruning/reweighting.

**Слабое место**

- too many modes can become a product complexity tax;
- graph query flexibility is not the same as answer quality;
- temporal semantics and answer contract are not the core story.

**What’s commodity**

- graph search;
- vector search;
- LLM-assisted query translation.

**Where ai-knot can win**

- fewer but stronger answer primitives;
- deterministic evidence operators;
- clearer product surface for trusted memory answers.

### 3.5 Supermemory

**Сильная сторона**

- polished product story;
- connector-first product;
- hybrid search with user/thread/time context;
- useful “memory graph” concept.

**Слабое место**

- technical details are opaque;
- hard to assess depth of temporal / inference semantics;
- differentiation depends on proprietary narrative.

**Что у них commodity**

- hybrid retrieval;
- connectors;
- user context.

**Где ai-knot может быть лучше**

- transparency and trace;
- typed answer contracts;
- evidence-level explainability;
- explicit architecture instead of black-box claims.

### 3.6 Hindsight

**Сильная сторона**

- strongest retrieval story among the group for temporal memory;
- four channels: semantic, BM25, entity traversal, temporal;
- spreading activation is genuinely distinctive;
- confidence-scored memories and distinct memory networks.

**Слабое место**

- still retrieval-centric;
- no fact consolidation;
- no hypergraph/n-ary grouping;
- no slot-based CAS;
- answer construction still not the product’s unique promise.

**Что у них commodity**

- hybrid search;
- temporal filtering;
- graph traversal.

**Где ai-knot может быть лучше**

- answer-contract layer;
- reconstruction over raw episodes;
- typed operators for list/time/inference answers;
- support bundles and consolidation.

### 3.7 memvid

**Сильная сторона**

- session-level storage is simple and effective;
- full session context helps aggregation;
- deterministic retrieval path;
- strong practical lesson: coarse granularity can beat over-fragmentation.

**Слабое место**

- no explicit inference architecture;
- no temporal reasoning layer as product differentiator;
- no answer contract;
- little emphasis on explainable state reconstruction.

**Что у них commodity**

- hybrid retrieval;
- session storage;
- deterministic search.

**Где ai-knot может быть лучше**

- typed answer planning;
- structured claims;
- traceable answer generation;
- multi-agent memory and trust.

### 3.8 Итог конкурентного поля

Рынок уже насыщен:

- vector + BM25;
- graph lookup;
- temporal filtering;
- agentic tool use.

Поэтому ai-knot не должен продаваться как:

- “ещё один graph memory”;
- “ещё один vector memory”;
- “ещё один agentic search loop”.

Наша ставка — на **answer-contracted memory reasoning**.

---

## 4) Где мы commodity, где novel

Это один из самых важных разделов. Чтобы не overclaim, надо честно разделить:

### Commodity

Это то, что уже стало стандартом рынка:

- vector retrieval;
- BM25 / lexical retrieval;
- hybrid fusion;
- entity extraction;
- graph traversal;
- temporal filtering;
- connector ingestion;
- LLM-assisted rendering.

На этом нельзя строить основное позиционирование. Это необходимо, но не уникально.

### Novel

Вот где у ai-knot может быть настоящее отличие:

#### 1. Query contract as a product primitive

Не “intent class”, а:

- `answer_space`
- `truth_mode`
- `time_axis`
- `locality`
- `evidence_regime`

Это не benchmark label. Это contract for memory answers.

#### 2. Support bundles as coarse-to-fine retrieval units

Не answer-shaped helper facts, а rebuildable evidence bundles:

- entity topic bundle;
- state timeline bundle;
- event neighborhood bundle;
- relation support bundle.

#### 3. Deterministic answer operators

Короткий набор операторов:

- exact_state;
- set_collect;
- time_resolve;
- candidate_rank;
- bounded_hypothesis_test;
- narrative_cluster_render.

Это делает answer behavior predictable.

#### 4. Evidence-aware strategy chooser

Роутинг не по словам вопроса, а по структуре вопроса плюс profile найденных evidence.

#### 5. Trace as product surface

Не только debugging trace, а customer-visible explainability.

### Как это сформулировать без overclaim

Правильная формула:

> We are novel in how we contract, organize, and verify answers over memory.

Неправильная формула:

> We have the best graph/vector search.

Потому что это commodity-гонка.

---

## 5) Product use cases и user stories

Ниже — не benchmark examples, а продуктовые истории.

### 5.1 Personal memory assistant

**Сценарий**

Пользователь спрашивает:

- “Что я обещал Коле на прошлой неделе?”
- “Когда я в последний раз говорил, что хочу сменить работу?”
- “Какие книги я уже рекомендовал?”

**Что даёт новая архитектура**

- answer_space=entity/set/scalar автоматически;
- time_axis выбирается осознанно;
- memory answers становятся воспроизводимыми;
- пользователь видит trace.

**Новый outcome**

- меньше потери контекста;
- меньше “не помню” при наличии evidence;
- более точные временные ответы.

### 5.2 Team / work memory

**Сценарий**

Менеджер спрашивает:

- “Что мы решили по клиенту X?”
- “Какие риски уже поднимались в прошлых созвонах?”
- “Что было согласовано, но ещё не сделано?”

**Что даёт новая архитектура**

- state reconstruction;
- support bundles по проекту/клиенту;
- separation of current state vs historical event;
- explanation of why a decision was surfaced.

**Новый outcome**

- меньше повторных обсуждений;
- меньше потери решений;
- проще аудит и handoff.

### 5.3 Support / customer success memory

**Сценарий**

Support agent спрашивает:

- “Какие проблемы уже были у этого клиента?”
- “Были ли у него ранее возвраты?”
- “Что обещали в прошлом тикете?”

**Что даёт новая архитектура**

- precise list answers;
- temporal answer correctness;
- contradiction-aware support traces;
- reduced agent guesswork.

**Новый outcome**

- быстрее first response;
- меньше повторных вопросов клиенту;
- выше consistency между агентами.

### 5.4 Agent memory

**Сценарий**

LLM-agent работает долго и должен помнить:

- текущие цели;
- выполненные шаги;
- observed constraints;
- prior failures;
- trustable claims from other tools/agents.

**Что даёт новая архитектура**

- raw episodes remain auditable;
- claims are typed;
- beliefs / evidence can be separated;
- uncertainty becomes first-class.

**Новый outcome**

- agent can reason over memory without re-searching everything;
- easier recovery after interruptions;
- better tool-calling discipline.

### 5.5 Multi-person / shared memory

**Сценарий**

Команда или несколько агентов делят один memory substrate.

**Что даёт новая архитектура**

- provenance-aware claims;
- trust-aware support;
- decay by salience, not by deleting truth;
- conflict trace.

**Новый outcome**

- shared memory becomes collaborative, not chaotic;
- can answer “who said what and why do we trust it?”

---

## 6) Почему это не LoCoMo overfit

Это важный риск, и его нужно проговорить честно.

### Что было бы overfit

Если бы мы сделали:

- branch по `Cat1/Cat2/Cat3`;
- keyword policy `would/likely/when`;
- helper labels под gold answers;
- temporal hacks только под “When did”;
- prompt tweaks only to score on one benchmark.

Это была бы подгонка.

### Почему новая архитектура не overfit по замыслу

Потому что она строится вокруг общих memory задач:

- list completeness;
- temporal correctness;
- state reconstruction;
- bounded inference;
- provenance and trace.

Это не LoCoMo-specific; это общие продуктовые проблемы.

### Проверка на продуктовость

Если убрать слово “LoCoMo”, слои всё ещё имеют смысл?

- `RawEpisode` — да;
- `AtomicClaim` — да;
- `SupportBundle` — да;
- `QueryFrame` — да;
- `AnswerContract` — да;
- `time_resolve` — да;
- `candidate_rank` — да;
- `bounded_hypothesis_test` — да.

То есть архитектура остаётся полезной вне benchmark.

### Что держит систему от overfit

- no category-specific runtime branches;
- no answer-shaped helper ontology;
- no keyword router as final policy;
- no prompt tricks as core solution;
- trace based on evidence, not on benchmark heuristics.

### Внутренний критерий

Любая новая сущность проходит тест:

> Назови 3 реальных product queries вне LoCoMo, где она нужна.

Если не получается — это подозрительно.

---

## 7) Go-to-market и product differentiation

### Как это продавать

Нельзя продавать ai-knot как:

- “мы лучше ищем память”;
- “мы тоже умеем graph memory”;
- “мы тоже hybrid retrieval”.

Это commodity.

Надо продавать так:

> **ai-knot turns memory into typed, explainable answers.**

Или:

> **Ask memory a question. Get an answer contract, evidence, and trace.**

### Кому это особенно важно

#### Enterprise / team memory

Им важно:

- provenance;
- consistency;
- auditability;
- time correctness;
- explainable reasoning.

#### Agents / orchestration

Им важно:

- state tracking;
- bounded inference;
- recovery after interruption;
- trust-aware shared memory.

#### Support / CRM / ops

Им важно:

- complete lists;
- current state;
- action history;
- decision trace.

### Какой дифференциатор продавать

#### Дифференциатор 1: Typed answers

Не просто retrieval, а тип ответа:

- list;
- temporal;
- exact state;
- hypothesis;
- narrative.

#### Дифференциатор 2: Evidence-aware routing

Система выбирает стратегию ответа по evidence, а не по surface-form keywords.

#### Дифференциатор 3: Explainability by design

Ответ сопровождается trace и provenance.

#### Дифференциатор 4: Shared memory trust

Мультиагентный и командный режимы работают с trust/decay/conflict.

### Что можно обещать в GTM

Можно обещать:

- faster, more reliable memory answers;
- fewer missing items in lists;
- better time accuracy;
- explanation of “why”.

Нельзя обещать:

- perfect truth;
- zero hallucinations always;
- superior performance on every benchmark;
- graph memory as universal answer to everything.

---

## 8) Риски позиционирования и what not to claim

Это обязательный блок, чтобы не испортить отличный продуктовый story.

### Риск 1: Слишком сильное claim “мы лучшие на памяти”

Почему плохо:

- рынок быстро сравнит с Mem0, Zep, Hindsight, Letta;
- это приведёт к commodity battle;
- победить по всем осям сразу почти невозможно.

Что говорить вместо этого:

- “Мы лучше в answer contract and evidence trace”
- “Мы лучше в typed memory reasoning”

### Риск 2: Позиционировать как graph DB

Почему плохо:

- graph memory — уже знакомая, crowded категория;
- теряется наш answer-planning дифференциал.

Что говорить вместо этого:

- graph traversal is one retrieval ingredient, not the product.

### Риск 3: Позиционировать как benchmark solver

Почему плохо:

- подгонка под LoCoMo убивает доверие;
- benchmark improvements не всегда переводятся в product value.

Что говорить вместо этого:

- “We solve common memory tasks; benchmarks are one validation signal.”

### Риск 4: Перебор с novelty

Почему плохо:

- если слишком много новых сущностей, система станет дорогой в разработке и сложной в объяснении.

Что делать:

- держать core small:
  - raw episodes;
  - claims;
  - bundles;
  - query contract;
  - operators;
  - trace.

### Риск 5: Обещать, что inference всегда точен

Почему плохо:

- bounded hypothesis testing всё равно может быть uncertain;
- product должен честно уметь говорить “uncertain”.

Что говорить:

- “The system can bound uncertainty and show evidence.”

### What not to claim

- not “fully autonomous reasoning”;
- not “solves all memory problems”;
- not “perfect graph intelligence”;
- not “benchmark-general superhuman memory”;
- not “zero-risk answer generation”.

---

## 9) Итоговая формулировка дифференциатора

После реализации новой архитектуры ai-knot должен звучать так:

> **ai-knot is a raw-first, evidence-aware memory engine that contracts typed answers over long-lived conversational and agent memory, with traceable reasoning and product-grade temporal correctness.**

Если ещё короче:

> **Not just memory search — memory answers.**

Это и есть правильный продуктовый дифф.

---

## 10) Ревью архитектора

**Вердикт:** позиционирование сильное и соответствует архитектуре.

- Хорошо, что дифф строится не вокруг “ещё одного graph/vector memory”, а вокруг answer contract и evidence trace.
- Сильная часть документа — отделение commodity-слоя от настоящей новизны.
- Правильно, что differentiation завязан на capability surface, а не на benchmark numbers.

**Что архитектор бы уточнил:**

- где именно заканчивается retrieval platform и начинается answer platform;
- какую часть narrative path мы сознательно оставляем LLM-dependent;
- какой минимальный набор product APIs будет виден наружу в первой полноценной версии.

**Архитектурный вывод:**  
документ хорошо стыкуется с target design и не обещает архитектурно невозможного.

---

## 11) Ревью критика

**Вердикт:** сильный product narrative, но есть риск over-positioning.

- Если слишком активно продавать “новую категорию”, рынок может услышать только marketing abstraction.
- Есть риск, что пользователь скажет: “окей, а в реальном продукте это просто retrieval + rerank + prompt”.
- Есть риск недооценить, насколько сложно донести answer contract без хорошего developer UX.

**Что критик бы потребовал:**

- очень конкретные demo flows;
- чёткие отрицательные claims: чем продукт НЕ является;
- отдельную таблицу “feature -> user-visible outcome”, чтобы narrative не зависал в абстракциях;
- дисциплину против слов вроде “fully autonomous reasoning”.

**Критический вывод:**  
позиционирование сильное, но его надо доказывать живыми кейсами и наблюдаемым product behavior.

---

## 12) Ревью как пользователь продукта

**Вердикт:** ценность понятна, если её показать на типовых вопросах.

Как это должно прозвучать для пользователя:

- “дай мне полный список, а не несколько случайных пунктов”;
- “скажи точную дату события, а не дату разговора о событии”;
- “если ты делаешь вывод, покажи, на чём он основан”;
- “если не уверен — скажи uncertain, а не придумывай”.

Что особенно цепляет:

- объяснимость;
- полнота;
- надёжность во времени;
- пригодность для shared/team memory.

**Пользовательский вывод:**  
этот дифф имеет смысл, потому что обещает не “больше памяти”, а “более надёжные ответы из памяти”.
