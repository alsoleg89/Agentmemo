# LoCoMo Failure Analysis — Cat1, Cat2, Cat3

**Base run:** `v094-openai-1conv-4o` (conv 1, top-k 60, ingest-mode dated-learn, answer: gpt-4o, judge: gpt-4o-mini)  
**Date:** 2026-04-11

---

## Cat1 — Single-hop factual

**32 вопросов, 8 CORRECT (25%), 24 WRONG (75%)**

### Классификация провалов

| Тип | Кол-во | % | Описание |
|-----|--------|---|----------|
| **M — Model incomplete** | 11 | 46% | Факты в контексте, модель перечислила не все |
| **R — Retrieval failure** | 9 | 37% | Нужный факт не попал в top-60 |
| **J — Judge too strict** | 4 | 17% | Ответ по сути верный, судья срезал |

### Детальная таблица (WRONG)

| Вопрос | Gold | Проблема | Тип |
|--------|------|----------|-----|
| What is Caroline's relationship status? | Single | "single" не в контексте | R |
| What activities does Melanie partake in? | pottery, camping, painting, swimming | "swimming" не в контексте | R |
| Where has Melanie camped? | beach, mountains, forest | все слова в ctx, модель дала только 2 из 3 | M |
| What do Melanie's kids like? | dinosaurs, nature | "dinosaurs" не в контексте | R |
| What books has Melanie read? | "Nothing is Impossible", "Charlotte's Web" | "Nothing is Impossible" не в контексте | R |
| What does Melanie do to destress? | Running, pottery | оба слова в ctx, модель дала только running | M |
| What LGBTQ+ events has Caroline participated in? | Pride parade, school speech, support group | "speech" не в контексте | R |
| What events for children? | Mentoring program, school speech | "speech" не в контексте | R |
| What activities with family? | Pottery, painting, camping, museum, swimming, hiking | "swimming" не в контексте | R |
| How many times to the beach in 2023? | 2 | модель сказала "once or twice" — судья срезал | J |
| What kind of art does Caroline make? | abstract art | "abstract" в ctx, модель описала смысл, не слово | M |
| Who supports Caroline? | Her mentors, family, and friends | не перечислила всех | M |
| What types of pottery? | bowls, cup | сказала "pots and a cup", не "bowls" | M |
| What has Melanie painted? | Horse, sunset, sunrise | все в ctx, модель пропустила sunrise | M |
| What are Melanie's pets' names? | Oliver, Luna, Bailey | Bailey в ctx, модель пропустила | M |
| What symbols are important to Caroline? | Rainbow flag, transgender symbol | transgender symbol не упомянула | M |
| What instruments does Melanie play? | clarinet and violin | violin в ctx, модель дала только clarinet | M |
| Changes during transition? | Changes to her body, losing unsupportive friends | "losing unsupportive friends" не в ctx | R |
| What does Melanie do on hikes? | Roast marshmallows, tell stories | все в ctx, модель не нашла | M |
| Transgender-specific events? | Poetry reading, conference | вероятно семантически верно, судья срезал | J |
| What book from Caroline's suggestion? | "Becoming Nicole" | книга в ctx ("book Caroline recommended"), модель отказалась | M |
| How many children does Melanie have? | 3 | число "3" в ctx, модель отказалась | J |
| When did Melanie go on a hike after roadtrip? | 19 October 2023 | модель дала 20 October — на 1 день ошиблась | J |
| What items has Melanie bought? | Figurines, shoes | "shoes" не в контексте | R |

### Выводы Cat1

- **Главная проблема (46%)** — модель не перечисляет ВСЕ элементы при множественных ответах. Останавливается на первом/главном.
- **Retrieval (37%)** — часть фактов не индексируется должным образом. Особенно уязвимы: числа ("3"), заголовки книг, единичные прилагательные ("single").
- **Judge (17%)** — судья слишком строгий к приблизительным числам и парафразам.

---

## Cat3 — Inference / "Would likely..."

**13 вопросов, 5 CORRECT (38%), 8 WRONG (62%)**

### Классификация провалов

| Код | Тип | Кол-во | % |
|-----|-----|--------|---|
| **S — Synthesis failure** | Факты есть, модель не вывела | 5 | 63% |
| **R — Retrieval failure** | Факты не retrieved | 2 | 25% |
| **S+R** | Mixed | 1 | 12% |

*Нет ни одного H (hallucination), B (binary flip), J (judge)*

### Детальная таблица (WRONG)

| Вопрос | Gold | Факты в ctx? | Поведение модели | Код |
|--------|------|--------------|-----------------|-----|
| Would Caroline likely have Dr. Seuss books? | Yes, collects children's books | Нет — "collects children's books" не retrieved | REFUSED | R |
| Would Caroline pursue writing as a career? | Likely no; wants to be a counselor | Да — counselor, career, reading есть | REFUSED | S |
| Would Melanie be considered LGBTQ member? | Likely no, doesn't refer to herself | Да — lgbtq, melanie, trans есть | REFUSED | S |
| Would Caroline be considered religious? | Somewhat, not extremely | Частично — church есть | REFUSED | S |
| Would Melanie enjoy Vivaldi? | Yes; it's classical music | Да — classical, music, concert есть | REFUSED | S |
| Personality traits Melanie says about Caroline? | Thoughtful, authentic, driven | "driven" нет, остальное есть | Partial (дала "courage") | S+R |
| Would Melanie go on another roadtrip? | Likely no; went badly | Да — roadtrip, bad, accident есть | REFUSED | S |
| Would Caroline move back home? | No; adopting children | Нет — adoption не retrieved | REFUSED | R |

### Выводы Cat3

- **Главная проблема (63%)** — модель отказывается делать вывод даже когда факты есть. Причина: системный промпт `"If the context does not contain enough information to answer, say 'I don't have enough context'"`.
- **Pattern**: все 6 refused-случаев — вопросы типа "Would X likely..." которые требуют inference, а не прямой цитаты.
- **Fix**: убрать запрет на inference, разрешить `"Likely yes/no because..."`.

---

## Промпты (история экспериментов)

### v1 — Original (baseline)
```
You are a helpful assistant answering questions based on memory context.

Instructions:
- Extract the precise answer from the context. Quote names, dates, numbers, and places exactly as they appear.
- If the question asks "when", look for dates, times, or temporal references in the context.
- If the question asks about a person, look for statements made by or about that person.
- If multiple facts are relevant, synthesize them into a single coherent answer.
- If the context does not contain enough information to answer, say "I don't have enough context to answer this."
- Be concise — answer in 1-3 sentences.
```
**Результат (conv 1):** Cat1 ~25%, Cat3 ~38%

---

### v2 — Detailed instructions (run: v094-new-prompt-1conv)
```
You are a helpful assistant answering questions based on memory context.

Instructions:
- Extract answers exactly as they appear in context — quote names, dates, numbers, and places verbatim.
- If multiple items are relevant, list ALL of them — do not paraphrase, synthesize, or stop at the first match.
- If the question asks what someone "would", "likely", or "probably" do/think/feel:
  reason from available facts even if no direct answer exists, then answer with "Likely yes/no because..."
- Only say "I don't have enough context" if context has ZERO relevant facts.
- Be concise — a word, comma-separated list, or 1-2 sentences max.
```
**Адресует:** M (list ALL) + S (Likely yes/no)

---

### v3 — Minimal (run: v094-minimal-prompt-1conv)
```
Answer the question based on the memory context below. Answer concisely.

Context:
{context}

Question: {question}
```
**Гипотеза:** меньше инструкций → меньше "I don't have enough context" отказов, модель просто отвечает

---

## Реальная разметка категорий в данных

В датасете `locomo10.json` категории соответствуют:

| Cat | Тип | Примеры вопросов |
|-----|-----|-----------------|
| 1 | Single-hop factual | "What is Caroline's identity?" |
| 2 | **Temporal** ("When did...") | "When did Caroline go to the LGBTQ support group?" |
| 3 | Inference ("Would/Likely...") | "Would Caroline likely have Dr. Seuss books?" |
| 4 | Open-ended ("How/What did...") | "How does Melanie prioritize self-care?" |
| 5 | Adversarial (нет ответа) | исключаем из оценки |

Cat2 в датасете — это **чисто temporal** (все 37 вопросов conv 1 начинаются с "When did").  
Cat3 — inference/commonsense (соответствует Cat4 в оригинальной статье).

---

## Сравнительная таблица всех запусков (conv 1)

### По категориям

| Run | Answer model | Prompt | Cat1 | Cat2 | Cat3 | Cat4 | Overall |
|-----|-------------|--------|------|------|------|------|---------|
| v094-openai-1conv-4o | gpt-4o | v1 original | 25% (8/32) | 67.6% (25/37) | 38.5% (5/13) | 87.1% (61/70) | 56.6% |
| v094-new-prompt-1conv | gpt-4o-mini | v2 detailed | 21.9% (7/32) | 59.5% (22/37) | 61.5% (8/13) | 87.1% (61/70) | 64.5% |
| v094-minimal-prompt-1conv | gpt-4o-mini | v3 minimal | 21.9% (7/32) | 35.1% (13/37) | 76.9% (10/13) | 87.1% (61/70) | 59.9% |
| v094-4o-cat12-1conv | gpt-4o | v3 minimal | 37.5% (12/32) | 59.5% (22/37) | — | — | 49.3% |

### Ключевые наблюдения

- **Cat4 (87%)** — стабилен при любом промпте и модели. Открытые описательные вопросы хорошо решаются.
- **Cat3 (inference)** — сильно зависит от промпта: v1=38% → v3=77%. Минимальный промпт лучший: модель просто инферит без запрета.
- **Cat2 (temporal)** — сильно зависит от модели: gpt-4o=60-68%, gpt-4o-mini без инструкций=35%. Mini теряется на "When did" без явного указания искать даты.
- **Cat1 (factual)** — промпт почти не влияет. gpt-4o даёт +15pp vs mini (37.5% vs 22%). Главная проблема в retrieval и неполном перечислении.

### Лучшие конфигурации по категории

| Cat | Лучший результат | Run |
|-----|-----------------|-----|
| Cat1 | 37.5% | gpt-4o + v3 minimal |
| Cat2 | 67.6% | gpt-4o + v1 original |
| Cat3 | 76.9% | gpt-4o-mini + v3 minimal |
| Cat4 | 87.1% | любой |

---

## Влияние learn() — изоляционный эксперимент (conv 1, mini, minimal prompt)

### Результаты

| Run | learn() | Ingest mode | Cat1 | Cat2 | Overall |
|-----|---------|-------------|------|------|---------|
| v094-minimal-prompt | broken (деградированный) | dated-learn | 21.9% (7/32) | 35.1% (13/37) | 39.1% |
| v094-learn-fixed (старая сборка) | ✓ | dated-learn | 34.4% (11/32) | 51.4% (19/37) | 43.5% |
| v095-learn-off | ✗ | dated | 18.8% (6/32) | 43.2% (16/37) | 31.9% |
| **v095-learn-on** | ✓ | dated-learn | **31.3% (10/32)** | **54.1% (20/37)** | **43.5%** |
| v094-4o-cat12 | broken | dated-learn | 37.5% (12/32) | 59.5% (22/37) | 49.3% |

### Ключевые выводы

- **learn() даёт +12.5pp cat1, +10.9pp cat2** vs dated-only (чистый delta)
- **Деградированный learn** (старый баг — хранил последнее user-сообщение) был хуже dated-only на cat2: добавлял шумовые факты → засорял retrieval
- **gpt-4o vs mini** (при broken learn): +15.6pp cat1, +16.3pp cat2 — модель отвечает сильно лучше на одних и тех же retrieval-данных
- **Off-by-1 на cat2** (~6 вопросов, ~16pp): raw dated turns с session-датой побеждают structured facts с event-датой при recall. Известный артефакт dated-learn, не фиксим

### Механика off-by-1 (cat2)

`dated-learn` делает двойной ingest:
1. `ingestDated` → raw turn `[8 May] Caroline: went to support group`
2. `ingestLearn` → structured fact `Caroline attended support group on 7 May`

При recall raw turn доминирует → модель читает session date `8 May` вместо event date `7 May`.
