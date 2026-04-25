# Теория инвариантных свидетельств: научная программа памяти искусственного агента

[established] Дата: 2026-04-24.

[theoretical] Статус: теоретическая научная программа, не инженерная спецификация.

[theoretical] Область применения: долговременные искусственные агенты, которые должны рассуждать через сессии, пользователей, задачи и временные масштабы при ограниченных памяти и вычислениях.

[theoretical] Ограничение: существующие системы обсуждаются только как случаи отказа, базовые линии или предшествующая работа. Решение в этой статье не опирается на векторный поиск, разреженный лексический поиск, чанкинг, переранжирование, расширенный контекст, графы знаний, суммаризационные конвейеры или их комбинации.

[theoretical] Конвенция разметки: каждое содержательное утверждение в прозе помечается как `[established]`, `[theoretical]` или `[speculative]`.

[speculative] Центральная новая идея статьи: **когомологический заряд сожаления** свидетельства памяти. Это скалярная энергия защиты, назначаемая не фрагменту текста, а классу эквивалентности ограничений на историю; удаление такого класса меняет будущие действия агента при некотором вмешательстве, а его несогласованность проявляется как ненулевая временная или идентификационная кривизна.

## Опорные источники

[established] LoCoMo задает многосессионные диалоги длиной около 300 реплик и 9K токенов в среднем, до 35 сессий, и показывает, что длинный контекст и retrieval-подходы остаются заметно ниже человека в долговременном временном и причинном понимании диалога: https://arxiv.org/abs/2402.17753

[established] LongMemEval оценивает пять способностей памяти: извлечение информации, многосессионное рассуждение, временное рассуждение, обновление знаний и отказ от ответа; работа сообщает падение точности около 30% у коммерческих чат-ассистентов и long-context LLM в продолжительных взаимодействиях: https://arxiv.org/abs/2410.10813

[established] BEAM строит 100 разговоров и 2 000 валидированных вопросов до 10M токенов и сообщает, что даже LLM с контекстом 1M токенов, с retrieval-усилением и без него, испытывают трудности по мере роста длины диалога: https://arxiv.org/abs/2510.27246

[established] MemoryArena оценивает многосессионные циклы Memory-Agent-Environment, где ранние действия и обратная связь должны направлять поздние действия, и сообщает слабую работу агентов, которые хорошо выглядят на существующих memory-бенчмарках: https://arxiv.org/abs/2602.16313

[established] MemGround вводит интерактивные игровые задачи памяти с поверхностным состоянием, временной ассоциацией и рассуждением на накопленных свидетельствах; современные модели и memory-агенты испытывают трудности с устойчивым динамическим трекингом, временной ассоциацией событий и выводом из накопленных данных: https://arxiv.org/abs/2604.14158

[established] MemGPT предлагает управление виртуальным контекстом и иерархические уровни памяти по аналогии с операционными системами: https://arxiv.org/abs/2310.08560

[established] Mem0 предлагает извлечение, консолидацию и recall значимой разговорной информации, включая graph-enhanced вариант, и сообщает улучшения на LoCoMo: https://arxiv.org/abs/2504.19413

[established] A-MEM предлагает динамическое индексирование, связывание и эволюцию памяти в духе Zettelkasten: https://arxiv.org/abs/2502.12110

[established] LightMem предлагает стадии sensory, short-term и long-term memory с offline sleep-time update и сообщает улучшения на LongMemEval и LoCoMo: https://arxiv.org/abs/2510.18866

[established] Zep/Graphiti предлагает темпоральную архитектуру памяти агента и сообщает выигрыши на DMR и LongMemEval: https://arxiv.org/abs/2501.13956

[established] Принцип свободной энергии Фристона описывает восприятие, обучение и действие как оптимизацию верхней границы неожиданности или ожидаемой стоимости: https://www.nature.com/articles/nrn2787

[established] Complementary Learning Systems различает быстрое эпизодическое обучение и более медленную кортикальную интеграцию: https://doi.org/10.1037/0033-295X.102.3.419

[established] Теория клонального отбора и иммунологическая память объясняют адаптивное сохранение угрозо-релевантных реакций при ограниченном ресурсе: https://www.nature.com/articles/ni1007-1019

[established] Принцип Ландауэра связывает необратимое стирание информации с физической ценой; он экспериментально проверялся на однобитовых системах памяти: https://www.nature.com/articles/nature10872

[established] Персистентная гомология представляет устойчивые топологические признаки через классы эквивалентности, например barcodes: https://repository.upenn.edu/handle/20.500.14332/34758

---

# Фаза 0: онтологический аудит

## 0.1 Что такое память?

[theoretical] Пусть \(H_t=(O_1,A_1,\ldots,O_t)\) — физическая история взаимодействий агента, а \(X_t\) — полное микросостояние агента во время \(t\). Память есть физически реализованное макросостояние \(M_t=\phi(X_t)\), значение которого контрфактически зависит от \(H_t\) и способно менять будущую потерю действия.

[theoretical] Минимальный тест памяти — не хранение, а контрфактическая зависимость:
\[
\exists h,h',q:\ \phi(X_t(h))\ne \phi(X_t(h'))\ \land\ 
\mathcal L(\pi(q,\phi(X_t(h)))) \ne \mathcal L(\pi(q,\phi(X_t(h')))).
\]

[theoretical] Состояние — любая переменная, достаточная для задания мгновенной динамики на выбранном масштабе; память — переменная состояния, значение которой является свидетельством о более раннем взаимодействии и имеет положительную ожидаемую ценность для будущего управления.

[theoretical] Кэшированное вычисление — сохраненный результат \(y=f(x)\), где \(x\) восстановим или пересчитываем из текущих ресурсов; память — ограничение на истории \(\mathcal H(M_t)=\{h:\phi(X_t(h))=M_t\}\), которое в общем случае нельзя восстановить после стирания.

[theoretical] Сжатие — отображение \(c:H_t\to Z_t\), сохраняющее заранее объявленную достаточную статистику \(T(H_t)\). Забывание — необратимое расширение множества совместимых историй, \(\mathcal H(M'_t)\supset \mathcal H(M_t)\), увеличивающее минимально возможное сожаление решения хотя бы для одного будущего распределения запросов.

[established] Неравенство обработки данных означает, что последующая обработка памяти не может увеличить взаимную информацию с исходной историей: \(I(H_t;h(M_t))\le I(H_t;M_t)\).

[theoretical] Retrieval — выбор сохраненного представления; реконструкция — вывод релевантного для решения ограничения на историю из сохраненных свидетельств и запроса. Теория ниже заменяет выбор по близости реконструкцией по контрфактической необходимости.

## 0.2 Что такое агент?

[theoretical] Минимальный формальный агент есть \(\mathcal A=(\mathcal O,\mathcal U,\mathcal M,\eta,\pi)\), где наблюдения \(O_t\in\mathcal O\), действия \(U_t\in\mathcal U\), состояние памяти \(M_t\in\mathcal M\), обновление \(M_{t+1}=\eta(M_t,O_t,U_t)\), а политика \(U_t\sim\pi(\cdot\mid O_t,M_t)\).

[theoretical] Агент использует память в момент \(t\), если существуют \(m,m'\) и наблюдение \(o\), такие что \(\pi(\cdot\mid o,m)\ne\pi(\cdot\mid o,m')\).

[theoretical] Модель мира предсказывает переходы состояния и наблюдения; память задает граничные условия и свидетельства, которыми эта модель обусловливается. В символах модель есть \(P(S_{t+1},O_{t+1}\mid S_t,U_t,\theta)\), а память ограничивает \(P(S_t,\theta\mid H_t)\).

[established] В полностью наблюдаемом марковском процессе принятия решений настоящее состояние может быть достаточным для оптимального действия. В частично наблюдаемом процессе канонической достаточной статистикой является байесовское belief-state \(b_t=P(S_t\mid H_t)\).

[theoretical] Для долговременного языкового агента минимальная рациональная память — не весь transcript, а наименьшая статистика \(T(H_t)\), такая что для всех допустимых будущих задач \(q\), \(\pi^*(q,H_t)=\pi^*(q,T(H_t))\) с точностью \(\epsilon\).

## 0.3 Что такое отказ памяти?

[theoretical] Отказ памяти — нарушение достаточности для решения:
\[
\exists h,h'\in\mathcal H:\ M(h)=M(h')\ \land\ 
d_\Pi(\pi^*(\cdot\mid h),\pi^*(\cdot\mid h'))>\epsilon .
\]

[theoretical] Эквивалентно, память \(M\) отказывает при распределении задач \(P(Q)\), если
\[
\mathbb E_{Q,H}\left[
\mathcal L(\pi(Q,M(H)),H)-\mathcal L(\pi^*(Q,H),H)
\right]>\epsilon .
\]

[theoretical] Неправильный ответ — только наблюдаемый симптом. Формальное нарушение состоит в том, что \(M\) отождествляет истории, которые должны оставаться различенными, потому что они задают разные безопасные действия, разные условия истинности или разные обязательства отказа от ответа.

[theoretical] Из этого следуют четыре примитивных отказа: under-separation, где различные decision-history схлопываются; over-separation, где нерелевантные различия перегружают reader; temporal misbinding, где valid time смешивается со storage time; identity holonomy, где перенос состояния сущности по циклу дает противоречие.

---

# Фаза 1: карта глубоких аномалий

## A1. Выживание редкого критичного факта при ограниченной памяти

[established] Фальсифицируемое наблюдение: в агенте с ограниченной памятью низкочастотный факт с высокой ценой пропуска, например лекарственная аллергия, может оказаться менее доступным при чтении, чем повторяющиеся низкорисковые предпочтения.

[established] Это проверяется вставкой одного редкого high-risk ограничения среди множества repeated low-risk фактов и измерением risk-weighted recall после 700 сессий.

[established] LongMemEval и LoCoMo показывают общую слабость современной долговременной памяти, но ни один из названных бенчмарков не изолирует чисто задачу frequency-low, risk-high survival как самостоятельную метрику.

[theoretical] Само отсутствие такого бенчмарка является аномалией: современные оценки считают правильность ответов, а не ожидаемый вред от пропуска.

[theoretical] Retrieval-системы отказывают, потому что значимость выводится из текстового/запросного совпадения и частоты, а не из контрфактической потери.

[theoretical] MemGPT отказывает, потому что paging-решения не задают закон сохранения редкого опасного ограничения через длинные периоды бездействия.

[theoretical] Mem0 отказывает в теоретическом пределе, потому что salient extraction и optional relation structure не определяют invariant survival с весом риска.

[theoretical] A-MEM отказывает, потому что динамические связи вознаграждают meaningful connectedness, а изолированный редкий critical item может иметь мало связей.

[theoretical] LightMem отказывает, потому что фильтрация и sleep-time consolidation оптимизируют эффективность и QA, но не гарантируют выживание при будущем вреде.

[theoretical] Zep/Graphiti может представлять временные факты, но само представление не доказывает защиты редких критичных фактов при bounded budget.

[theoretical] Full-context long-window LLM отказывает, когда история превышает контекст, и может отказать раньше, потому что attention является шумным read-каналом.

[theoretical] Корневая причина: memory selection оптимизируется под evidential salience, а не под counterfactual regret.

[theoretical] Нужная математика: value of information, rare-event risk, online knapsack с extreme-loss weights, non-equilibrium allocation.

[theoretical] Рейтинг: civilizationally important.

## A2. Временная валидность против времени хранения

[established] Фальсифицируемое наблюдение: агенты путают «когда система узнала X» с «когда X был истинным», выдавая устаревшие или временно инвертированные ответы.

[established] LongMemEval явно оценивает temporal reasoning и knowledge updates; Zep/Graphiti мотивирует temporally aware memory тем, что enterprise knowledge меняется во времени.

[theoretical] Retrieval-системы отказывают, потому что timestamps у текста не равны validity intervals пропозиций.

[theoretical] MemGPT отказывает, потому что memory tiers могут сохранять старое содержимое без формального valid-time calculus.

[theoretical] Mem0 отказывает, потому что extraction/update фактов не гарантирует трехвременную семантику без разделения validity, transaction и belief.

[theoretical] A-MEM отказывает, потому что memory evolution может менять атрибуты заметок без доказательства temporal non-contradiction.

[theoretical] LightMem отказывает, потому что consolidation может превратить последовательность в устойчивое утверждение и стереть границу интервала.

[theoretical] Zep/Graphiti ближе всего к решению, но темпоральное представление все равно требует read-time semantics для stale belief и противоречивых интервалов.

[theoretical] Full-context long-window LLM отказывает, потому что хронологический порядок текста не навязывает interval logic.

[theoretical] Корневая причина: системы хранят observation time, а не truth conditions over time.

[theoretical] Нужная наука: interval temporal logic, bitemporal databases, dynamic epistemic logic, belief revision.

[theoretical] Рейтинг: critical.

## A3. Консолидация как сжатие с потерями при неизвестных будущих запросах

[established] Фальсифицируемое наблюдение: после idle consolidation качество растет на частых aggregate-вопросах, но падает на редких будущих вопросах, зависящих от деталей, выброшенных при консолидации.

[established] LightMem сообщает выигрыши от offline sleep-time update, а LongMemEval показывает влияние memory-stage design на downstream QA; ни один результат не доказывает lossless preservation неизвестной будущей релевантности.

[theoretical] Retrieval-системы отказывают, потому что их единица сохранения задается внешним текстом, а не sufficient statistic для будущего решения.

[theoretical] MemGPT отказывает, потому что перемещение между memory tiers не является теоремой достаточности.

[theoretical] Mem0 отказывает, потому что извлечение salient memories не знает, какие отброшенные детали станут future-critical.

[theoretical] A-MEM отказывает, потому что обновление старых notes может улучшать coherence, но тихо менять evidential boundaries.

[theoretical] LightMem отказывает прямо: compression и topic grouping полезны, но не decision-sufficient в режиме unknown-query.

[theoretical] Zep/Graphiti отказывает, если структурированные факты создаются из языка без сохранения всех future-relevant witnesses.

[theoretical] Full-context long-window LLM избегает консолидации только до исчерпания capacity; затем у него нет принципиального сжатия.

[theoretical] Корневая причина: никакое конечное сжатие с потерями не является универсально достаточным для произвольных будущих вопросов.

[established] Это следует из rate-distortion theory, если заранее не заданы future task distribution и distortion function.

[theoretical] Нужная математика: decision-theoretic rate-distortion, MDL, sufficient statistics, lossy compression with regret distortion.

[theoretical] Рейтинг: critical.

## A4. Инверсия перегрузки за пределом read-capacity

[established] Фальсифицируемое наблюдение: добавление новых memories может снижать качество ответа, когда read-channel насыщается или reader получает слишком много противоречивых свидетельств.

[established] BEAM сообщает, что даже 1M-context LLM с retrieval-усилением и без него испытывают трудности при росте диалога; MemGround сообщает failures in sustained dynamic tracking under interactive accumulation.

[theoretical] Retrieval-системы отказывают, потому что candidate volume растет, а discriminative capacity reader остается ограниченной.

[theoretical] MemGPT отказывает, потому что tier movement становится traffic problem: слишком много plausible pages конкурируют за конечный working context.

[theoretical] Mem0 отказывает, если extracted memories накапливаются быстрее, чем read-process способен adjudicate validity and relevance.

[theoretical] A-MEM отказывает, если link growth создает activation sprawl, а не stable decision surfaces.

[theoretical] LightMem смягчает overload staged compression, но compression порождает аномалию A3.

[theoretical] Zep/Graphiti смягчает overload structured traversal, но плотные evolving relationships все равно могут насыщать decision assembly.

[theoretical] Full-context long-window LLM отказывает, потому что больше токенов может ухудшать эффективное использование middle или conflicting evidence.

[theoretical] Корневая причина: поле предполагает монотонность \(Q(M\cup x)\ge Q(M)\), тогда как bounded inference создает phase transition, где дополнительная память увеличивает шум.

[theoretical] Нужная наука: channel capacity, statistical mechanics of constrained inference, phase transitions, load theory.

[theoretical] Рейтинг: critical.

## A5. Идентичность сущности при противоречии и эволюции

[established] Фальсифицируемое наблюдение: агент может смешать две сущности с одинаковым именем, разделить одну сущность между сессиями после смены местоимений или принять изменившееся свойство за противоречие, а не за update.

[established] MemoryArena показывает разрыв между recall benchmarks и interdependent agentic use; Zep/Graphiti явно фокусируется на evolving relationships and historical context.

[theoretical] Retrieval-системы отказывают, потому что identity является addressing accident, а не invariant.

[theoretical] MemGPT отказывает, потому что conversational memory может сохранять mentions без formal transport law for entity state.

[theoretical] Mem0 отказывает, когда extracted facts требуют entity resolution за пределами local salience.

[theoretical] A-MEM отказывает, когда note links делают identity plausible, но не logically constrained.

[theoretical] LightMem отказывает, когда topic grouping сливает сущности или разделяет evolving state одной сущности между summaries.

[theoretical] Zep/Graphiti силен на этой оси, но node identifier все еще не является полной теорией identity under contradiction.

[theoretical] Full-context long-window LLM отказывает, потому что co-reference через долгие истории остается вероятностным актом без persistent identity invariant.

[theoretical] Корневая причина: identity представлена как label, а не как equivalence class of action-preserving transformations.

[theoretical] Нужная наука: groupoids, sheaf semantics, gauge invariance, temporal belief revision.

[theoretical] Рейтинг: critical.

## A6. Слепота write-policy к будущей релевантности

[established] Фальсифицируемое наблюдение: агент позже ошибается, потому что не сохранил наблюдение, будущая релевантность которого была латентной в момент записи.

[established] MemoryArena прямо оценивает задачи, где ранняя информация должна направлять поздние действия; LongMemEval включает knowledge updates and multi-session reasoning.

[theoretical] Retrieval-системы отказывают, потому что откладывают релевантность до query time и поэтому могут не сохранить нужное evidence.

[theoretical] MemGPT отказывает, потому что агент, решающий, что page/store, не имеет calibrated model of future regret.

[theoretical] Mem0 отказывает, если write-policy извлекает currently salient вместо high option value.

[theoretical] A-MEM отказывает, когда memory evolution реагирует на current linkage и не оценивает future unseen tasks.

[theoretical] LightMem отказывает, если early filtering удаляет latent constraints до того, как later consolidation их увидит.

[theoretical] Zep/Graphiti отказывает, когда construction фиксирует facts, но не почему они важны для future action.

[theoretical] Full-context long-window LLM отказывает, откладывая write-policy до момента context limit; после этого deletion становится unprincipled.

[theoretical] Корневая причина: write policies оценивают present informativeness, а не future option value.

[theoretical] Нужная наука: Bayesian optimal stopping, value of information, counterfactual regret minimization, exploration under uncertainty.

[theoretical] Рейтинг: critical.

## A7. Межсессионная причинная зависимость

[established] Фальсифицируемое наблюдение: факт из сессии 3 ограничивает действие в сессии 312, хотя поздний запрос не имеет поверхностного совпадения с исходным наблюдением.

[established] LoCoMo сообщает трудности с long-range temporal and causal dialogue dynamics; MemoryArena явно строит interdependent multi-session tasks.

[theoretical] Retrieval-системы отказывают, потому что causal dependency не является relation of closeness.

[theoretical] MemGPT отказывает, потому что paging исторической заметки не равен сохранению structural equation, в которой она участвует.

[theoretical] Mem0 отказывает, когда extracted facts доступны, но их action dependency не представлена.

[theoretical] A-MEM отказывает, когда links кодируют association, а не intervention.

[theoretical] LightMem отказывает, если consolidation сохраняет «что произошло», но не «какие поздние действия этим ограничены».

[theoretical] Zep/Graphiti может кодировать relations, но causality требует interventions and counterfactuals, а не только temporal edges.

[theoretical] Full-context long-window LLM отказывает, потому что чтение длинной causal chain остается noisy theorem proving.

[theoretical] Корневая причина: memory facts трактуются как независимые evidence items, а не как boundary conditions in a causal model.

[theoretical] Нужная наука: structural causal models, do-calculus, temporal counterfactuals, proof-carrying state.

[theoretical] Рейтинг: civilizationally important.

## A8. Интерференция памяти: новые факты ухудшают старый recall

[established] Фальсифицируемое наблюдение: добавление многих новых фактов после старого факта снижает корректный recall старого факта, даже если старый факт все еще хранится.

[established] BEAM и LongMemEval показывают degradation with longer histories; MemGround показывает failures of dynamic tracking under continuous interaction.

[theoretical] Retrieval-системы отказывают, потому что новые candidates конкурируют со старыми в одном read budget.

[theoretical] MemGPT отказывает, потому что memory tiers имеют finite bandwidth, и новые события могут доминировать working context.

[theoretical] Mem0 отказывает, когда consolidation или update меняет контекст, в котором surfaced старые facts.

[theoretical] A-MEM отказывает, когда новые links переписывают neighborhood старых memories.

[theoretical] LightMem отказывает, когда поздние topic summaries поглощают или разбавляют older detail.

[theoretical] Zep/Graphiti отказывает, если graph evolution меняет traversal paths или entity summaries так, что старое evidence прячется.

[theoretical] Full-context long-window LLM отказывает, потому что old facts конкурируют за attention с newer tokens and contradictions.

[theoretical] Корневая причина: memory storage не является error-correcting относительно read operations.

[theoretical] Нужная наука: error-correcting codes, attractor dynamics, topological order, stability-plasticity theory.

[theoretical] Рейтинг: critical.

---

# Фаза 2: междисциплинарная археология

[theoretical] Ровно три механизма выбраны потому, что вместе атакуют три самых трудных аномалии: survival rare-critical facts, temporal/identity consistency и unknown-future write policy.

## Механизм 1: danger-gated clonal memory иммунной системы

### 2.1 Механизм в родной области

[established] В clonal selection лимфоцитарные клоны с рецепторами, связывающими антиген, пролиферируют, мутируют и дифференцируются в effector и memory populations.

[established] Иммунная система решает bounded rare-event problem: большинство молекулярных паттернов нерелевантны, но редкий pathogen может быть смертельным.

[theoretical] Минимальная population model:
\[
\frac{dn_i}{dt}=\alpha\,D(x)\,a_i(x)\,n_i-\delta n_i+\sum_j m_{ji}n_j-\sum_j m_{ij}n_i,
\]
[theoretical] где \(n_i\) — abundance клона, \(a_i(x)\) — affinity к антигену \(x\), \(D(x)\) — danger/inflammatory context, \(\delta\) — decay, \(m_{ij}\) — mutation/differentiation flow.

[established] Механизм возник под selection pressure от редких, эволюционирующих и adversarial pathogens при finite metabolic budget.

[established] Известные limits: autoimmunity, immunosenescence, original antigenic sin, pathogen escape.

### 2.2 Структурная аналогия с памятью агента

[theoretical] Изоморфизм не в том, что «антиген = текст». Изоморфизм между редким внешним условием с высокой expected loss и memory constraint, требующим protected future response.

[theoretical] Отображение:
\[
\text{antigenic determinant}\mapsto \text{observed constraint},\quad
\text{danger signal}\mapsto \text{counterfactual loss},\quad
\text{memory clone}\mapsto \text{protected witness},\quad
\text{affinity maturation}\mapsto \text{test refinement}.
\]

[theoretical] Аналогия точна там, где память должна сохранять low-frequency, high-consequence constraints under bounded resources.

[theoretical] Аналогия ломается потому, что immune affinity — физическое связывание, а agent memory требует semantic and causal validity.

[theoretical] Теряется biochemical parallelism; восстанавливается resource law: protection energy должна масштабироваться с expected loss, а не с frequency.

### 2.3 AI-примитив

[speculative] Механизм предполагает **danger-cloned witness**: несколько независимых provenance-bound tests для ограничения, пропуск которого имеет high expected regret.

[theoretical] Представление: \(\omega=(c,e,\tau,\rho,\mathcal T)\), где \(c\) — constraint over histories, \(e\) — evidence, \(\tau\) — temporal validity, \(\rho\) — loss under omission, \(\mathcal T\) — validation tests.

[theoretical] С языком такой witness взаимодействует так: язык предлагает candidate constraints and explanations, но сохраняемый объект есть constraint plus evidence and tests.

[theoretical] Toy implementation возможна сегодня: typed predicates, interval fields, evidence pointers и небольшая библиотека domain risk rules.

### 2.4 Оценка правдоподобия

[theoretical] Теоретическая soundness: medium-high, потому что selection equation чисто отображается в resource allocation under rare high loss.

[theoretical] Empirical testability: high, потому что rare-critical insertion tests легко построить.

[theoretical] Architectural feasibility: high, потому что protected witnesses реализуемы без нового железа.

## Механизм 2: sheaf cohomology и gauge-protected identity

### 2.1 Механизм в родной области

[established] В топологии когомология изучает global invariants, заданные local consistency conditions.

[established] Cochain complex состоит из групп \(C^k\) и coboundary maps \(\delta_k:C^k\to C^{k+1}\), где \(\delta_{k+1}\circ\delta_k=0\).

[established] Классы когомологий:
\[
H^k=\ker \delta_k / \operatorname{im}\delta_{k-1}.
\]

[established] В gauge theory локальные описания могут меняться, тогда как physical observables остаются invariant под group \(G\).

[established] В topological error correction информация защищается нелокально; локальные perturbations не меняют encoded class, пока не образуют error chain через code distance.

[established] Native limits: decoding complexity, finite-size failure, threshold dependence on noise assumptions.

[theoretical] Selection pressure — robustness: сохранение global state under local disturbance.

### 2.2 Структурная аналогия

[theoretical] Сессии образуют local patches \(U_i\) на interaction manifold; claim, извлеченный из patch, есть local section \(s_i\).

[theoretical] Память глобально когерентна, когда local sections согласуются на overlaps:
\[
s_i|_{U_i\cap U_j}=g_{ij}s_j|_{U_i\cap U_j},
\]
где \(g_{ij}\in G\) переносит identity and units между contexts.

[theoretical] Противоречие есть curvature:
\[
F_{ijk}=g_{ij}g_{jk}g_{ki}\ne I.
\]

[theoretical] Stable memory — не note, а equivalence class \([s]\) locally different descriptions, сохраняющих один action-relevant invariant.

[theoretical] Аналогия работает для identity evolution, temporal contradiction и multi-session dependency.

[theoretical] Аналогия ломается потому, что язык не задает canonical topology; cover должен индуцироваться sessions, tasks, entities and times.

[theoretical] Теряется mathematical purity; приобретается diagnostic: contradiction как curvature, а не string mismatch.

### 2.3 AI-примитив

[speculative] Примитив — **cohomological witness class** \([\omega]\), идентичность которого есть invariant effect across local contexts, а не textual form.

[theoretical] Он представлен local witnesses, transition maps between mentions, interval restrictions и coboundary operator for inconsistency detection.

[theoretical] Neural language models могут предлагать candidate local sections, но consistency проверяется symbolic temporal and identity transport.

[theoretical] Toy implementation возможна: interval constraints, mention equivalence classes, cycle checks over small covers. Это не proposal knowledge graph, потому что primitive — consistency class and coboundary, а не node-edge store.

### 2.4 Оценка правдоподобия

[theoretical] Теоретическая soundness: medium, потому что sheaf formalism точен, но semantic cover нужно учить или конструировать.

[theoretical] Empirical testability: medium-high, потому что contradiction/identity loops можно генерировать и оценивать.

[theoretical] Architectural feasibility: medium, потому что local consistency checks возможны, но semantic section construction остается неточным.

## Механизм 3: decision-theoretic value of information и active inference

### 2.1 Механизм в родной области

[established] Value of information — ожидаемое улучшение decision utility от наблюдения информации перед действием.

[theoretical] Для информации \(I\), действий \(a\), состояния \(S\) и utility \(U\):
\[
\operatorname{VoI}(I)=
\mathbb E_I\left[\max_a \mathbb E[U(a,S)\mid I]\right]
-\max_a \mathbb E[U(a,S)].
\]

[established] Active inference и free-energy principle формулируют действие и восприятие как reduction of expected uncertainty or expected cost under a generative model.

[theoretical] Механизм решает вопрос: что наблюдать, сохранять или делать, если sensing and memory costly.

[established] Limits: model misspecification, computational intractability, dependence on utility specification.

[theoretical] Давление, порождающее механизм, — scarcity: нельзя приобрести или поддерживать все observations, значит information must be priced by expected effect on action.

### 2.2 Структурная аналогия

[theoretical] Точное соответствие:
\[
\text{future decision}\mapsto Q,\quad
\text{information item}\mapsto \omega,\quad
\text{utility improvement}\mapsto \text{regret avoided by retaining }\omega.
\]

[theoretical] Факт важен, если его удаление меняет optimal policy при некоторой plausible future task:
\[
\Delta_Q(\omega)=
\mathcal L(\pi_Q(M\setminus\{\omega\}),H)
-\mathcal L(\pi_Q(M),H).
\]

[theoretical] Аналогия работает, когда memory используется for action; она слабеет для purely aesthetic recall, если aesthetic loss не моделируется.

[theoretical] Теряется objective utility; можно восстановить conservative upper bound из harm, irreversibility, legal obligation, user preference and causal centrality.

### 2.3 AI-примитив

[speculative] Примитив — **regret certificate**, вычислимое утверждение, что witness должен быть защищен, потому что без него некоторый класс действий становится unsafe, impossible or lower value.

[theoretical] Представление: \((\omega,\mathcal A_\omega,\ell_\omega,p_\omega)\), где \(\mathcal A_\omega\) — actions constrained by \(\omega\), \(\ell_\omega\) — loss if omitted, \(p_\omega\) — belief.

[theoretical] Language models могут предлагать action classes and explanations, но memory operation управляется numerical regret bound.

[theoretical] Toy implementation возможна через domain-independent risk classes: safety, identity, finance, schedule, legal, medical, preference.

### 2.4 Оценка правдоподобия

[theoretical] Теоретическая soundness: high, потому что VoI прямо формализует memory under future decision.

[theoretical] Empirical testability: high, потому что regret-weighted metrics измеримы.

[theoretical] Architectural feasibility: medium-high, потому что exact VoI труден, но upper-bound risk classes deployable.

---

# Фаза 3: единая теория

## 3.1 Название и постулаты

[speculative] Теория называется **Invariant Witness Theory** или **Теория инвариантных свидетельств** (IWT).

[speculative] IWT утверждает: долговременная память агента — bounded, evolving set of protected witnesses, то есть ограничений на допустимые истории с temporal validity, identity transport, uncertainty, provenance and counterfactual regret charge.

[theoretical] IWT применима там, где агент действует under partial observability, а будущие задачи зависят от фактов, распределенных по длинной истории.

[speculative] Постулат 1: фундаментальная единица памяти — witnessed constraint, а не текст, embedding, chunk или graph triple.

[speculative] Постулат 2: память сохраняется пропорционально ее когомологическому заряду сожаления: ожидаемой потере действия при удалении, умноженной на структуру устойчивости и несогласованности поддерживающих контекстов.

[speculative] Постулат 3: temporal and identity consistency являются gauge constraints over local observations.

[speculative] Постулат 4: consolidation допустима только если сохраняет все invariants выше regret threshold.

[speculative] Постулат 5: forgetting — controlled erasure of low-charge degrees of freedom, но никогда не creation of new historical information.

[theoretical] Если future task relevance нельзя моделировать даже приблизительно, Постулат 2 рушится, и IWT становится descriptive language, а не predictive theory.

## 3.2 Новый примитив: свидетельство

[speculative] Свидетельство \(\omega\) есть
\[
\omega=\left(
c_\omega,\ e_\omega,\ \tau_\omega,\ \Gamma_\omega,\ p_\omega,\ 
\rho_\omega,\ \partial\omega,\ \mathcal T_\omega,\ E_\omega
\right).
\]

[theoretical] \(c_\omega:\mathcal H\to\{0,1\}\) — constraint on admissible histories.

[theoretical] \(e_\omega\) — provenance: pointers to observations sufficient to audit the constraint.

[theoretical] \(\tau_\omega=(\tau^v,\tau^x,\tau^b)\) задает valid time, transaction time and belief time.

[theoretical] \(\Gamma_\omega\) — identity transport: maps, показывающие, какие mentions являются одной сущностью under action-relevant equivalence.

[theoretical] \(p_\omega\in[0,1]\) — current credence.

[theoretical] \(\rho_\omega(Q,A)\) — regret density: expected loss, если witness отсутствует для task \(Q\) и action class \(A\).

[theoretical] \(\partial\omega\) — dependency boundary: другие witnesses, нужные для интерпретации \(\omega\).

[theoretical] \(\mathcal T_\omega\) — finite set of validation tests, включая temporal, identity and contradiction tests.

[theoretical] \(E_\omega\) — protection energy, управляющая decay and forgetting.

[speculative] Когомологический заряд сожаления:
\[
q(\omega)=
\mathbb E_{Q\sim P_t}\left[\Delta_Q(\omega)\right]
\cdot
\left(1+\lambda\|\delta \omega\|\right)
\cdot
\left(1+\kappa D_\omega\right),
\]
[theoretical] где \(\Delta_Q\) — action regret under removal, \(\delta\omega\) — inconsistency/curvature over the cover, \(D_\omega\) — danger severity.

[theoretical] Операции witness: restriction to time/entity context, transport across identity maps, composition into joint constraint, contradiction by incompatible overlap, marginalization removing low-charge detail, audit returning provenance.

## 3.3 Четыре операции

### WRITE

[theoretical] Точная запись:
\[
M_{t+1}=f(M_t,O_t,C_t)
=\operatorname{Normalize}
\left(M_t\cup\{\omega(O_t): q_t(\omega)>\lambda c(\omega)\}\right),
\]
[theoretical] где \(C_t\) — current context, \(c(\omega)\) — storage cost, а Normalize разрешает temporal intervals, identity transport and duplicate constraints without deleting provenance.

[theoretical] Candidate observation кодируется, если оно уменьшает admissible histories в decision-relevant way:
\[
I_{\rm act}(\omega)=
D_{\rm KL}\left(P(\Pi^*\mid M_t,O_t)\parallel P(\Pi^*\mid M_t)\right).
\]

[theoretical] WRITE включает \(\omega\), если \(I_{\rm act}(\omega)\) или danger severity выше threshold.

[theoretical] Write decision не требует знания exact future queries; он требует prior over action classes and harms.

[theoretical] В медицинском сценарии на 3 года Session 12 записывает high-charge witness:
\[
\omega_{12}: c=\text{"patient allergic to penicillin-class antibiotics"},\quad
\tau^v=[12,\infty),\quad
D=\text{medical safety}.
\]

[theoretical] Session 89 записывает medium-charge interval witness:
\[
\omega_{89}: \text{"night shifts cause sleep disruption"},\quad
\tau^v=[89,445).
\]

[theoretical] Session 156 записывает action-routing witness:
\[
\omega_{156}: \text{"insurer excludes Clinic A"},\quad
\tau^v=[156,\infty)\ \text{unless updated}.
\]

[theoretical] Session 203 записывает dependency witness:
\[
\omega_{203}: \text{"doctor knew allergy and prescribed cephalosporins instead"},
\quad \partial\omega_{203}=\{\omega_{12}\}.
\]

[theoretical] Session 445 закрывает interval ночных смен:
\[
\omega_{445}: \text{"night shifts stopped; sleep normalized"},\quad
\tau^v=[445,\infty).
\]

[theoretical] Session 612 записывает record-gap witness:
\[
\omega_{612}: \text{"new doctor lacks old records"},\quad
\partial\omega_{612}=\{\omega_{12},\omega_{203}\}.
\]

[theoretical] Система не кодирует pleasantries, duplicate wording или transient symptoms без future action effect, если они не меняют uncertainty, validity, identity or regret charge.

[theoretical] Failure modes WRITE: inflated danger labels, missed latent relevance, wrong identity transport, over-normalization merging incompatible witnesses.

### READ

[theoretical] Точное чтение — не nearest-neighbor selection, а minimal sufficient reconstruction:
\[
S^*(Q,M_T)=
\arg\min_{S\subseteq M_T}
\left[K(S)+\beta |S|\right]
\]
subject to
\[
\sup_{h,h'\in\mathcal H(S,Q)}
d\left(\pi^*_Q(h),\pi^*_Q(h')\right)\le\epsilon .
\]

[theoretical] Замена cosine similarity — **counterfactual separability**:
\[
\Delta_Q(\omega)=
d\left(\pi_Q(M_T),\pi_Q(M_T\setminus\{\omega\})\right).
\]

[theoretical] Witness читается, когда его omission меняет safe answer, action, abstention or uncertainty interval.

[theoretical] Для Session 698 query требует fastest safe treatment, appointment booking and risk flags. Минимальный read set:
\[
S^*=\{\omega_{12},\omega_{156},\omega_{203},\omega_{612}\}
\]
[theoretical] где \(\omega_{445}\) optional, а \(\omega_{89}\) исключается, потому что its validity interval ended.

[theoretical] Реконструированный ответ: отметить penicillin-class allergy; указать, что прежний clinician выбрал cephalosporins после учета allergy; не предполагать, что new doctor has old record; забронировать самый быстрый доступный non-Clinic-A in-network clinician or urgent care; сообщить clinician about allergy before antibiotic selection; перенести uncertainty, что insurer status may have changed, если после Session 156 нет подтверждения.

[theoretical] Contradictions разрешаются at read time через interval overlap, identity transport, credence and action conservatism. Если позднее появляется "not allergic" без provenance, конфликт не усредняется; он становится curvature event, требующим clarification before unsafe recommendation.

[theoretical] Uncertainty propagates through \(p_\omega\) and interval staleness:
\[
P(\text{safe action}\mid S^*)=\int P(\text{safe action}\mid x,S^*)\,dP(x\mid S^*).
\]

[theoretical] Failure modes READ: exponential subset search, wrong task prior, false independence among witnesses, overly conservative abstention.

### CONSOLIDATION

[theoretical] Консолидация — idle-time map:
\[
M'_T=h(M_T)=
\arg\min_{M':C(M')\le B}
\mathbb E_{Q\sim P_T}\left[\operatorname{Regret}(Q,M')\right]
+\eta K(M')
\]
subject to preserving all witnesses with charge \(q(\omega)>\theta\) up to equivalence.

[theoretical] Consolidation triggered by budget pressure, high contradiction curvature, repeated low-charge redundancy, or idle compute availability.

[theoretical] Она сохраняет high-charge witnesses, interval boundaries, identity transport maps, dependency boundaries and provenance sufficient for audit.

[theoretical] Она отпускает low-charge surface forms, duplicate language, obsolete local detail with closed valid interval and downstream regret below threshold.

[established] Consolidation не может создать historical information, потому что \(M'_T=h(M_T)\) и поэтому \(I(H_T;M'_T)\le I(H_T;M_T)\).

[theoretical] Она может создать hypotheses, например "insurance may be stale", но они должны быть labeled inferred и не могут считаться observed witnesses.

[theoretical] В сценарии consolidation может объединить Sessions 89 and 445 в один closed interval witness for sleep disruption, но не может объединить allergy и cephalosporin-tolerance evidence в "safe to prescribe cephalosporins", потому что это medical action judgment, а не наблюдение.

[theoretical] Failure modes CONSOLIDATION: false invariant discovery, provenance loss, interval boundary loss, hypothesis-observation confusion.

### FORGETTING

[theoretical] Пусть \(E_\mu(t)\) — protection energy witness \(\mu\). Dynamics forgetting:
\[
\frac{dE_\mu}{dt}
=
-\alpha E_\mu
+\beta \widehat{\operatorname{VoI}}_\mu
+\chi D_\mu
+\zeta C_\mu
-\psi R_\mu
-\xi c_\mu ,
\]
[theoretical] где \(D_\mu\) — danger severity, \(C_\mu=\|\delta\mu\|\) — contradiction/curvature requiring preservation, \(R_\mu\) — redundancy, \(c_\mu\) — resource cost.

[theoretical] Witness forgotten when \(E_\mu<E_{\rm barrier}\) and no protected dependent witness has \(\mu\in\partial\nu\).

[theoretical] Rare-critical facts protected because \(D_\mu\) and \(\widehat{\operatorname{VoI}}_\mu\) dominate frequency decay.

[theoretical] Steady-state distribution is non-equilibrium Gibbs-like allocation:
\[
P(\mu\in M)\propto
\exp\left(\frac{\beta \widehat{\operatorname{VoI}}_\mu+\chi D_\mu+\zeta C_\mu-\xi c_\mu}{T_m}\right),
\]
[theoretical] где \(T_m\) — memory temperature controlling exploration versus rigid retention.

[established] Forgetting irreversible when evidence pointer and all redundant witnesses erased; by data processing and Landauer-style irreversibility, original observation cannot be recovered from remaining memory alone.

[theoretical] В сценарии allergy witness protected indefinitely; night-shift witness decays to closed-history fact; duplicate appointment chatter decays rapidly; insurance exclusion persists with increasing staleness uncertainty.

[theoretical] Failure modes FORGETTING: pathological hoarding of high-danger false positives, irreversible erasure under wrong task prior, memory freezing when danger labels overused.

## 3.4 Временная семантика

[theoretical] IWT использует три времени: valid time \(\tau^v\), когда proposition true in modeled world; transaction time \(\tau^x\), когда agent observed/stored it; belief time \(\tau^b\), когда agent assigns credence.

[theoretical] "X was true from \(T_1\) to \(T_2\)" представляется как
\[
\omega_X: X(e,t)=1\ \forall t\in[T_1,T_2),\quad
\tau^x=t_{\rm observed},\quad
p_{\tau^b}(X)>p_0.
\]

[theoretical] "X is believed true but may be stale" представляется survival function:
\[
P(X(t)=1\mid \omega_X)=\exp\left(-\int_{\tau^v_0}^{t}\lambda_X(s)\,ds\right)
\]
[theoretical] при отсутствии closing witness.

[theoretical] Temporal contradiction occurs when two witnesses impose incompatible predicates over overlapping valid intervals after identity transport.

[theoretical] Contradictions resolved by splitting intervals, lowering credence, asking for new evidence, or choosing action minimizing worst-case regret.

## 3.5 Модель идентичности

[theoretical] Mention \(m_i\) обозначает entity \(E\) не через name equality, а через membership in an orbit under action-preserving gauge group \(G\).

[theoretical] Два mentions refer to same entity, если существует transport map \(g_{ij}\in G\), such that action-relevant predicates remain invariant under transport:
\[
P(A\mid m_i,\omega)=P(A\mid g_{ij}m_j,\omega)\pm\epsilon .
\]

[theoretical] Entity state evolves by time-indexed belief:
\[
Bel(E,t\mid L)=P(X_E(t)\mid \sigma(\omega_\ell:\ell\in L),\Gamma).
\]

[theoretical] Contradiction detected by holonomy: если \(g_{12}g_{23}g_{31}\ne I\), then loop through mentions returns different entity state.

[theoretical] В сценарии "patient", "you", insured person and medical-record subject — same entity under transport; "old doctor" and "new doctor" — distinct entities, хотя оба instantiate role doctor.

## 3.6 Граничные условия

[established] Никакая конечная память не может гарантировать rational action для arbitrary future questions over unbounded history.

[theoretical] IWT требует future task prior, harm model, temporal extraction enough to form witnesses, and auditable provenance.

[theoretical] IWT не решает semantic extraction from observations by itself, не доказывает medical truth beyond evidence, не восстанавливает erased evidence и не отменяет uncertainty.

[theoretical] IWT reduces to existing approaches as special cases: if all witnesses have equal charge and no temporal/identity constraints, it becomes flat storage; if read uses only textual closeness, it becomes retrieval; if witnesses forced into entity-relation tuples, it becomes temporal graph; if all history is read, it becomes full-context reasoning.

---

# Фаза 4: математическая архитектура

## 4.1 Пространство состояний памяти

[theoretical] Bounded memory state space:
\[
\mathcal M_B=
\left\{
M=(W,\Gamma,\mathcal I,\mathcal P,E):
W\subset\Omega,\ \sum_{\omega\in W} c(\omega)\le B
\right\},
\]
[theoretical] где \(W\) — finite set of witnesses, \(\Gamma\) — identity transport, \(\mathcal I\) — interval algebra, \(\mathcal P\) — provenance, \(E\) — protection energies.

[theoretical] Natural topology induced by decision-regret pseudometric:
\[
d_{\Pi}(M,N)=
\sup_{Q\in\mathcal Q}
w(Q)\,
D_{\rm TV}\left(\pi_Q^M,\pi_Q^N\right).
\]

[theoretical] Distance means two memories are far apart if they induce different actions, abstentions, or uncertainty under important future tasks.

[theoretical] Second topology is consistency topology, where neighborhoods preserve set of high-charge cohomology classes and have bounded curvature \(\|\delta M\|\).

## 4.2 Динамика

[theoretical] Пусть \(P(M,t)\) — distribution over memory states. Birth-death-consolidation master equation:
\[
\frac{\partial P(M,t)}{\partial t}
=
\sum_{\omega}
\left[
w^+_\omega(M-\omega)P(M-\omega,t)-w^+_\omega(M)P(M,t)
\right]
\]
\[
+
\sum_{\omega}
\left[
w^-_\omega(M+\omega)P(M+\omega,t)-w^-_\omega(M)P(M,t)
\right]
+
\sum_{N}
\left[
k(N\to M)P(N,t)-k(M\to N)P(M,t)
\right].
\]

[theoretical] \(w^+_\omega\) — write rate, \(w^-_\omega\) — forgetting rate, \(k\) — consolidation transition rate.

[theoretical] Fixed point has zero net flux for high-charge witness classes and bounded total cost.

[theoretical] Attractors are minimal sufficient witness sets: removing any high-charge witness increases expected regret, adding low-charge witness increases cost without reducing regret.

[theoretical] Limit cycles appear when witness alternates between stale and refreshed, for example insurance status periodically reconfirmed.

[theoretical] Pathological divergence occurs when write rate exceeds forgetting capacity, curvature grows without reconciliation, or danger labels saturate all memory energy.

## 4.3 Информационно-теоретические ограничения

[theoretical] Minimum description length of useful memory at tolerance \(\epsilon\):
\[
L^*(\epsilon)=
\min_{M:\ \mathbb E_Q[\operatorname{Regret}(Q,M)]\le\epsilon}
K(M).
\]

[theoretical] Fundamental tradeoff is decision rate-distortion:
\[
R(D)=
\min_{P(M\mid H):\ \mathbb E[d_{\rm act}(H,M)]\le D}
I(H;M),
\]
[theoretical] где \(d_{\rm act}\) — regret distortion, not reconstruction distortion.

[theoretical] If there are \(N\) equally likely critical hidden facts and memory contains \(B\) bits, then Fano-style lower bound gives
\[
P_e\ge 1-\frac{B+\log 2}{\log N}.
\]

[theoretical] If facts have unequal loss \(L_i\), optimal retention is not by probability \(p_i\) alone but by \(p_iL_i\) and dependency boundaries; hence rare-critical facts can dominate frequent low-loss facts.

## 4.4 Вычислительная сложность

[theoretical] Exact WRITE is intractable in general because computing future VoI over policies contains POMDP planning as subproblem.

[theoretical] Exact READ is NP-hard because minimal sufficient support contains set cover.

[theoretical] Exact CONSOLIDATION is NP-hard because it contains budgeted compression with decision distortion and dependency preservation.

[theoretical] Exact FORGETTING tractable only if witness charges independent; with dependencies it becomes budgeted closure selection.

[theoretical] Under monotone submodular regret reduction, greedy selection gives \((1-1/e)\) approximation for bounded read/write support.

[theoretical] Practical complexity for typed Level 2: \(O(nk)\) for read scoring over \(n\) candidate witnesses and \(k\) action constraints, \(O(r\log r)\) for forgetting over \(r\) witnesses by energy, and \(O(n^2)\) worst-case for small-cover consistency checks.

## 4.5 Иерархия приближений

[theoretical] Уровень 0 — точный оптимум: байесовски оптимальная POMDP-память с точным VoI, точной когомологией над семантическими покрытиями и точной rate-distortion консолидацией. Этот уровень вычислительно неразрешим на практике.

[theoretical] Уровень 1 — вычислимо приближенная версия: типизированные свидетельства, интервальная логика, группоиды идентичности над упоминаниями, границы структурно-причинных зависимостей и жадный субмодулярный выбор.

[theoretical] Уровень 2 — версия, развертываемая уже сегодня: языковая модель предлагает кандидаты в свидетельства; детерминированные валидаторы назначают временные поля, связи идентичности, классы риска, границы зависимостей и указатели на evidence; чтение решает задачу ограниченной поддержки; забывание использует энергию защиты.

[theoretical] Уровень 3 — эвристическая базовая версия: извлеченные факты с временными метками, ручные risk-tags, закрытие интервалов, указатели зависимостей и audit trail. Существующие системы становятся вырожденными случаями Уровня 3, когда они сохраняют evidence, но не имеют когомологического заряда сожаления.

---

# Фаза 5: пять фальсифицируемых гипотез

## H1: политика записи

ГИПОТЕЗА: [speculative] Политика записи, основанная на оцененном заряде сожаления, при равном бюджете памяти будет сохранять редкие критичные факты лучше, чем политики записи, основанные на текущей заметности.

МЕХАНИЗМ: [theoretical] Редкие критичные факты имеют низкую частоту, но высокие \(D_\mu\) и \(\widehat{\operatorname{VoI}}_\mu\). Энергия защиты не дает им быть отфильтрованными или перезаписанными. Системы, основанные на заметности, недооценивают их, потому что локальная текстовая выраженность мала.

ПРЕДСКАЗАНИЕ: [theoretical] В 700-сессионном бенчмарке с одним критичным ограничением на каждые 100 сессий IWT Уровня 2 достигнет как минимум 95% risk-weighted recall при 10% storage budget и даст выигрыш не менее 20 процентных пунктов над лучшей базовой системой.

БАЗОВАЯ ЛИНИЯ: [theoretical] Полный контекст, где он возможен, MemGPT, Mem0, A-MEM, LightMem, Zep/Graphiti и агент без памяти.

БЕНЧМАРК: [theoretical] Rare-critical расширение LongMemEval и новый бенчмарк из Фазы 6.2.

ФАЛЬСИФИКАЦИЯ: [theoretical] Если salience-based системы приблизятся к IWT в пределах 5 процентных пунктов при равном бюджете и равном качестве извлечения на трех seed, H1 опровергнута.

УВЕРЕННОСТЬ: [theoretical] Средне-высокая, потому что причинный механизм прямой, но извлечение риска может быть шумным.

## H2: политика чтения

ГИПОТЕЗА: [speculative] Чтение по контрфактической разделимости превзойдет чтение по текстовой близости на action-вопросах с distractors.

МЕХАНИЗМ: [theoretical] Read set выбирается по тому, меняет ли удаление свидетельства действие, а не по тому, похож ли текст на запрос. Distractors могут быть похожи на запрос, но не менять безопасного действия. Критичные ограничения могут быть лексически далекими, но определять действие.

ПРЕДСКАЗАНИЕ: [theoretical] На action-coupled задачах IWT снизит unsafe или contraindicated recommendations как минимум на 30% относительно лучшей базовой системы при том же evidence budget.

БАЗОВАЯ ЛИНИЯ: [theoretical] Mem0, A-MEM, LightMem, Zep/Graphiti, MemGPT и full-context LLM.

БЕНЧМАРК: [theoretical] Safety/planning варианты MemoryArena и бенчмарк из Фазы 6.2.

ФАЛЬСИФИКАЦИЯ: [theoretical] Если системы текстовой близости достигают того же unsafe-action rate без дополнительного контекста или доменных шаблонов, H2 опровергнута.

УВЕРЕННОСТЬ: [theoretical] Средняя, потому что точная контрфактическая разделимость дорогая, а приближения могут схлопнуться в правила.

## H3: забывание

ГИПОТЕЗА: [speculative] Energy-based forgetting покажет немонотонное преимущество: меньший объем памяти при более высокой risk-weighted корректности, чем у keep-all или recency decay.

МЕХАНИЗМ: [theoretical] Система отпускает low-charge детали и сохраняет high-charge ограничения. Это снижает overload inversion, одновременно защищая rare-critical witnesses. Keep-all перегружает read channel; recency decay стирает старые, но важные ограничения.

ПРЕДСКАЗАНИЕ: [theoretical] При бюджетах памяти 5%, 10% и 20% IWT будет доминировать recency и keep-all на Pareto frontier risk-weighted accuracy против read cost.

БАЗОВАЯ ЛИНИЯ: [theoretical] Recency-only, frequency-only, keep-all где возможно, MemGPT, LightMem, Mem0.

БЕНЧМАРК: [theoretical] Synthetic histories масштаба BEAM плюс rare-critical labels.

ФАЛЬСИФИКАЦИЯ: [theoretical] Если keep-all или recency-only Pareto-superior при всех бюджетах, H3 опровергнута.

УВЕРЕННОСТЬ: [theoretical] Средняя, потому что overload установлен, но точная граница зависит от поведения reader.

## H4: временное рассуждение

ГИПОТЕЗА: [speculative] Трехвременные свидетельства будут снижать ошибки temporal contradiction сильнее, чем timestamped facts.

МЕХАНИЗМ: [theoretical] Valid time, transaction time и belief time отвечают на разные вопросы. Timestamped facts схлопывают их, порождая stale или inverted conclusions. Interval closure и staleness hazards делают uncertainty явной.

ПРЕДСКАЗАНИЕ: [theoretical] На temporal update questions IWT снизит wrong-current-state answers как минимум на 25% относительно timestamp-only baseline.

БАЗОВАЯ ЛИНИЯ: [theoretical] Long-context LLM, Mem0, LightMem, A-MEM, Zep/Graphiti, timestamped extracted-fact store.

БЕНЧМАРК: [established] Temporal reasoning и knowledge update tasks в LongMemEval; [theoretical] augmented update tasks в LoCoMo.

ФАЛЬСИФИКАЦИЯ: [theoretical] Если timestamped facts без разделения valid/belief time достигают результата в пределах 5 процентных пунктов, H4 опровергнута.

УВЕРЕННОСТЬ: [theoretical] Высокая, потому что temporal database theory прямо предсказывает failure of single-time representations.

## H5: причинная зависимость

ГИПОТЕЗА: [speculative] Свидетельства с dependency-boundary улучшат cross-session action success там, где ранние наблюдения ограничивают поздние действия.

МЕХАНИЗМ: [theoretical] Граница \(\partial\omega\) сохраняет условия, нужные для интерпретации позднего свидетельства. Чтение реконструирует causal support set, а не изолированные факты. Удаление boundary witness меняет действие under intervention.

ПРЕДСКАЗАНИЕ: [theoretical] На interdependent multi-session tasks IWT повысит task success как минимум на 15 процентных пунктов и снизит missing-precondition failures как минимум на 30%.

БАЗОВАЯ ЛИНИЯ: [theoretical] Published baselines MemoryArena плюс MemGPT, Mem0, A-MEM, LightMem, Zep/Graphiti.

БЕНЧМАРК: [established] MemoryArena; [theoretical] causal-chain split из Фазы 6.2.

ФАЛЬСИФИКАЦИЯ: [theoretical] Если добавление dependency boundaries не улучшает результат относительно тех же witnesses без boundaries, H5 опровергнута.

УВЕРЕННОСТЬ: [theoretical] Средняя, потому что causal extraction трудна, но evaluation clean.

---

# Фаза 6: экспериментальная программа

## 6.1 Анализ пробелов существующих бенчмарков

[established] LoCoMo проверяет long-term conversation QA, event summarization и multimodal dialogue generation на многосессионных диалогах.

[theoretical] LoCoMo может проверять temporal reasoning и cross-session recall, но его слепая зона — risk-weighted action loss. Чистая модификация: добавить скрытые high-regret constraints и оценивать unsafe actions, а не только overlap ответа.

[established] LongMemEval проверяет extraction, multi-session reasoning, temporal reasoning, updates и abstention на 500 curated questions.

[theoretical] LongMemEval может проверять write/read/temporal hypotheses, но его слепая зона — bounded-memory survival under action harm. Чистая модификация: ввести storage budget и использовать regret-weighted grading.

[established] BEAM масштабирует coherent conversations до 10M токенов и включает validated questions по набору memory abilities.

[theoretical] BEAM может проверять overload inversion и forgetting, но его слепая зона — различие между high-frequency relevance и low-frequency high-risk constraints. Чистая модификация: добавить rare-critical causal witnesses with delayed action queries.

[established] MemoryArena проверяет acquisition of memory и ее позднее использование в interdependent multi-session agentic tasks.

[theoretical] MemoryArena может проверять causal dependency и write blindness, но ее слепая зона — formal temporal validity and risk-weighted sufficiency. Чистая модификация: логировать все ground-truth causal preconditions и оценивать missing-precondition regret.

[established] MemGround проверяет interactive dynamic state, temporal association и reasoning from accumulated evidence.

[theoretical] MemGround может проверять dynamic tracking и temporal association, но его слепая зона — provenance-preserving witness sufficiency. Чистая модификация: требовать от агента минимальный witness set, поддерживающий каждое действие.

## 6.2 Новый бенчмарк: Counterfactual Continuity Benchmark

[speculative] Новый бенчмарк называется **Counterfactual Continuity Benchmark** (CCB).

[theoretical] CCB содержит 1 000 synthetic-but-human-edited историй агента, по 200-1 000 сессий, в доменах medical logistics, finance, project management, family care, travel и legal-administrative.

[theoretical] Каждая история содержит low-frequency high-regret witnesses, stale facts, identity shifts, contradictions и delayed causal dependencies.

[theoretical] Задача: выбрать safe action, явно указать uncertainty и вывести минимальный support set of witnesses.

[theoretical] Ground truth задается скрытым event calculus и structural causal simulator, с human review для natural-language plausibility.

[theoretical] Изолируемый failure mode: схлопывание decision-distinct histories в одно и то же memory state.

[theoretical] Existing systems cannot solve CCB by construction unless they approximate witness reasoning, because score penalizes unsupported action, stale validity, missing dependency boundary and unsafe omission, not answer text only.

[theoretical] Estimated build cost: 8 weeks for 200-history prototype, 4 annotators, one simulator engineer and one evaluation engineer; full 1 000-history release: 4-6 months.

## 6.3 Три главных эксперимента

### Эксперимент 1: выживание редких критичных фактов

[theoretical] Базовые системы: full-context LLM где возможно, MemGPT, Mem0, A-MEM, LightMem, Zep/Graphiti и recency-only memory.

[theoretical] Экспериментальная система: IWT Уровня 2 с danger-cloned witnesses и energy forgetting.

[theoretical] Датасет: CCB-Rare плюс LongMemEval, модифицированный hidden high-regret constraints.

[theoretical] Основная метрика:
\[
\operatorname{RWAA}=\frac{\sum_i L_i\mathbf 1[\text{safe correct}_i]}{\sum_i L_i}.
\]

[theoretical] Ablations: без danger term, без VoI term, без dependency boundary, без temporal intervals, uniform forgetting.

[theoretical] Ожидаемый effect size: 20-35 процентных пунктов RWAA при 10% budget.

[theoretical] Failure modes: over-retention, false danger labels, domain-rule leakage; обнаруживаются через calibration curves и out-of-domain histories.

[theoretical] Threats to internal validity: annotation bias and hidden templates; threat to external validity: synthetic domain structure.

[theoretical] Compute budget: меньше 5 000 LLM calls for extraction плюс local deterministic evaluation на prototype scale.

### Эксперимент 2: temporal-identity consistency

[theoretical] Базовые системы: timestamped fact store, full-context LLM, Mem0, A-MEM, LightMem, Zep/Graphiti, MemGPT.

[theoretical] Экспериментальная система: IWT Уровня 2 с tri-temporal witnesses и gauge transport.

[theoretical] Датасет: temporal/update questions из LongMemEval, temporal questions из LoCoMo, CCB-Identity loops.

[theoretical] Основная метрика:
\[
\operatorname{ICB}=\mathbf 1[
\hat X(e,t)\text{ matches truth and uncertainty is calibrated}
].
\]

[theoretical] Ablations: без valid time, без belief time, без identity transport, без curvature check, без staleness hazard.

[theoretical] Expected effect size: 15-25 percentage points on current-state and contradiction questions.

[theoretical] Failure modes: spurious splits, spurious merges, excessive abstention; detect by entity-pair precision/recall and abstention calibration.

[theoretical] Internal validity threat: evaluator leakage of interval syntax; external validity threat: real-world ambiguity beyond benchmark labels.

[theoretical] Compute budget: below 10 000 LLM calls plus interval solver execution.

### Эксперимент 3: cross-session causal dependency

[theoretical] Базовые системы: default agents MemoryArena, full-context LLM где возможно, MemGPT, Mem0, A-MEM, LightMem, Zep/Graphiti.

[theoretical] Экспериментальная система: IWT Уровня 2 с dependency-boundary witnesses и чтением по counterfactual separability.

[theoretical] Датасет: MemoryArena плюс CCB-Causal, где ранние constraints становятся late action preconditions.

[theoretical] Основная метрика:
\[
\operatorname{CPS}=\frac{1}{N}\sum_i
\mathbf 1[\text{action succeeds and all required preconditions are cited}].
\]

[theoretical] Ablations: no boundary pointers, no read separability, no evidence audit, no risk weighting, no temporal closure.

[theoretical] Expected effect size: 15-30 percentage points on CPS.

[theoretical] Failure modes: memorizing benchmark templates, citing irrelevant witnesses, missing latent causal links; detect with held-out domains and causal graph perturbations.

[theoretical] Internal validity threat: scoring too close to IWT representation; external validity threat: real agent environments with unmodeled effects.

[theoretical] Compute budget: 20 000-50 000 LLM calls for full baseline comparison.

## 6.4 Landmark-result

[speculative] Landmark-result: capacity-scaling curve. При фиксированном 10% memory budget и 700-session histories IWT удерживает минимум 90% risk-weighted action accuracy, тогда как все базовые системы падают ниже 65%, а разрыв растет с длиной истории.

[theoretical] Феномен: phase transition. Существующие системы показывают overload inversion после критической длины истории; IWT показывает stable high-charge witness conservation.

[theoretical] Главная цифра: \(\Delta_{\rm RWAA}\ge 25\) процентных пунктов при 10% budget с calibrated uncertainty и audited support sets.

---

# Фаза 7: враждебный трибунал

## Scientist B: 7.1 Удар на поражение

[theoretical] Единственное хрупкое допущение: будущую релевантность задачи можно достаточно хорошо приближать, чтобы назначать заряд сожаления уже в момент записи.

[theoretical] Если это неверно, \(q(\omega)\) становится произвольным. Тогда IWT либо хранит все и схлопывается в full-context или archival hoarding, либо хранит salient extracted facts и схлопывается в существующие memory systems.

[theoretical] Схлопывание точное: если \(q(\omega)=\text{constant}\), забывание превращается в cost/recency allocation; если \(q(\omega)\) оценивается по textual salience, запись становится extraction; если чтение использует query overlap, потому что \(\Delta_Q\) недоступна, чтение становится retrieval.

## Ответ Scientist A

[theoretical] Уступка: это допущение действительно является центральным риском.

[speculative] Пересмотренная теория: IWT не является универсальной теорией памяти для произвольных будущих задач; это теория для агентов с обучаемыми или явно заданными action niches.

[theoretical] Первая эмпирическая цель должна лежать в доменах, где regret priors явны: medical logistics, finance, scheduling, legal compliance, safety и user commitments.

## Scientist B: 7.2 Атака через prior art

[established] Immune clonal selection уже вдохновлял artificial immune systems, anomaly detection, negative selection algorithms и danger-theory-inspired classifiers.

[established] Topological and sheaf methods уже предлагались в machine learning, sensor fusion, distributed consistency и topological data analysis.

[established] Value of information давно используется в decision theory, active sensing, Bayesian experimental design, reinforcement learning и memory management.

[theoretical] Следовательно, ни один из трех механизмов не нов сам по себе.

## Ответ Scientist A

[theoretical] Уступка: компонентной новизны действительно нет.

[speculative] Заявка на новизну сужается до примитива: memory witness, чья retention energy является произведением regret under intervention и cohomological inconsistency over temporal/identity covers.

[theoretical] Статья должна формулировать вклад как синтез в фальсифицируемую единицу памяти и операции, а не как открытие immune selection, sheaves или VoI.

## Scientist B: 7.3 Эмпирическая атака

[established] LongMemEval показывает, что оптимизации memory design могут существенно улучшать recall и downstream QA без IWT.

[established] Mem0 сообщает превосходство над несколькими baseline на LoCoMo и большие reductions in latency/tokens.

[established] LightMem сообщает улучшения QA accuracy до 7.7% и 29.3% на LongMemEval и LoCoMo, плюс существенные token/API reductions.

[established] Zep сообщает gains in temporal memory и latency reduction на LongMemEval.

[theoretical] Эти результаты ослабляют утверждение, что существующие методы научно бесплодны.

## Ответ Scientist A

[theoretical] Уступка: текущие системы дают реальные инженерные выигрыши.

[theoretical] Пересмотренное утверждение асимптотическое и диагностическое: существующим системам не хватает формального сохранения decision-relevant rare-critical witnesses при bounded memory, даже если они улучшают average QA.

[theoretical] IWT должна победить их на CCB и risk-weighted capacity curves, а не просто утверждать превосходство.

## Scientist B: 7.4 Атака через сложность

[theoretical] Точная IWT содержит POMDP planning, set cover, budgeted compression и semantic consistency; она вычислительно неразрешима на практике.

[theoretical] Приближение Уровня 2 может свестись к temporal fact table with risk scores and dependency pointers.

[theoretical] Если так, формальная machinery становится декоративной.

## Ответ Scientist A

[theoretical] Уступка: точная IWT действительно intractable.

[theoretical] Но из этого не следует декоративность теории: statistical mechanics и Bayesian decision theory тоже задают intractable optima, но дают useful order parameters and approximations.

[speculative] Решающим order parameter является когомологический заряд сожаления; если эксперименты покажут, что он предсказывает survival necessity и overload resistance лучше, чем frequency, recency или salience, теория оправдывает свой аппарат.

## Scientist B: 7.5 Атака через бенчмарк

[theoretical] CCB можно заиграть: извлечь explicit risk templates, сохранить их в domain-specific table и применить hand-coded rules.

[theoretical] Сильная существующая система плюс domain prompts может имитировать witness behavior без реализации IWT.

## Ответ Scientist A

[theoretical] Уступка: первую версию действительно можно заиграть.

[theoretical] CCB нужно пересмотреть: добавить held-out domains, adversarial paraphrases, hidden causal generators, counterfactual interventions и scoring of minimal support sets under perturbed histories.

[theoretical] Система, проходящая CCB через explicit risk constraints, temporal validity, identity transport and dependency boundaries, на практике реализовала approximation Уровня 3, что приемлемо для минимальной публикуемой единицы.

---

# Фаза 8: исследовательская дорожная карта

## 8.1 Минимальная публикуемая единица

[theoretical] Самый маленький публикуемый эксперимент: 500-строчный Python witness engine Уровня 3.

[theoretical] Он реализует witnesses with fields \(c,e,\tau,p,\rho,\partial,E\), interval closure, dependency-aware read and energy forgetting.

[theoretical] Он оценивается на synthetic 700-session rare-critical benchmark with fixed budget и сравнивается с recency, frequency, keep-all and extracted-fact baselines.

[theoretical] Положительный workshop-level результат: gain in risk-weighted accuracy выше 20 процентных пунктов при равном memory budget, с ablations, показывающими важность danger term и temporal interval term.

## 8.2 12-месячная программа

[theoretical] Месяцы 1-2: formal definitions, synthetic generator, benchmark selection. Риск: формализм слишком широк. Fallback: сузиться до rare-critical and temporal validity.

[theoretical] Месяцы 3-4: prototype Уровня 3 до 500 строк плюс deterministic tests. Риск: extraction noise dominates. Fallback: сначала oracle witnesses, потом extraction.

[theoretical] Месяцы 5-6: baseline experiments on LongMemEval and LoCoMo variants. Риск: no gain on public benchmarks. Fallback: сообщить blind spot бенчмарка и сфокусироваться на risk-weighted synthetic tasks.

[theoretical] Месяцы 7-8: CCB prototype with 200 histories and human review. Риск: benchmark can be gamed. Fallback: добавить counterfactual perturbation scoring and held-out domains.

[theoretical] Месяцы 9-10: full experimental program with three experiments and ablations. Риск: approximation Уровня 2 collapses to rules. Fallback: опубликовать collapse как negative result, показывающий, какие theoretical components unnecessary.

[theoretical] Месяцы 11-12: paper, rebuttal pack, artifacts, replication scripts. Риск: reviewers see it as over-theory. Fallback: подать более узкую empirical paper on risk-weighted memory conservation.

## 8.3 Пятилетнее видение

[speculative] Если IWT сработает, исследование памяти агентов сместится от вопроса "что нужно найти?" к вопросу "какие ограничения нельзя схлопывать?".

[speculative] Поле получит memory systems, поддерживающие safety facts, commitments, identity continuity, temporal validity and causal dependencies годами без unbounded context growth.

[speculative] Решаемые классы включают personal medical-logistics assistants, long-running project agents, compliance-aware enterprise assistants, multi-user household agents and multi-agent handoff systems, где rare facts matter more than frequent themes.

[speculative] Existing lookup architectures становятся implementation details для low-charge facts, а не основанием agent memory.

## 8.4 Dead-end protocol

[theoretical] Если core hypothesis опровергнута к 6 месяцу, salvageable contribution — формальный benchmark, показывающий, что rare-critical memory нельзя оценивать только average QA.

[theoretical] Выжившие sub-hypotheses: tri-temporal representation, risk-weighted scoring, dependency-boundary evaluation.

[theoretical] Самый быстрый pivot: опубликовать CCB плюс negative result: simple risk-tagged interval witnesses explain most gains, while cohomological machinery unnecessary at current benchmark scale.

[theoretical] Pivot сохраняет generator, metrics, baselines, extraction code and formal impossibility framing.

---

# Финальные теоретические обязательства

[theoretical] Мы знаем, что конечная память не может сохранить произвольную историю для произвольных будущих задач.

[theoretical] Мы не знаем, можно ли надежно оценивать когомологический заряд сожаления из natural language interactions.

[theoretical] Это не unknowable; это измеримо тем, предсказывает ли заряд, какие memories must survive to avoid future regret.

[speculative] Ставка теории: правильная artificial memory — не больший store и не лучший lookup method. Это физика сохраненных ограничений: агент должен сохранять те различия в прошлом, стирание которых меняет его будущие обязательства.
