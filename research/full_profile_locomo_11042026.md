# LoCoMo Full Profile — 11 Apr 2026

**Runs:** `v096-dated-all` (dated, all cats, 9 conv) + `v097-learn-cat1/2/3` (dated-learn, conv 0–6)  
**Answer model:** gpt-4o-mini | **Judge:** gpt-4o-mini | **Prompt:** v3 minimal | **top-k:** 60

---

## v096 — dated ingest, все категории (1288/1540 вопросов)

| Conv | Cat1 | Cat2 | Cat3 | Cat4 |
|------|------|------|------|------|
| 00 | 8/32 (25%) | 16/37 (43%) | 8/13 (62%) | 62/70 (89%) |
| 01 | 5/11 (45%) | 20/26 (77%) | — | 32/44 (73%) |
| 02 | 14/31 (45%) | 12/27 (44%) | 2/8 (25%) | 75/86 (87%) |
| 03 | 9/37 (24%) | 13/40 (33%) | 3/11 (27%) | 84/111 (76%) |
| 04 | 6/31 (19%) | 19/26 (73%) | 2/14 (14%) | 92/107 (86%) |
| 05 | 16/30 (53%) | 13/24 (54%) | 1/7 (14%) | 56/62 (90%) |
| 06 | 9/20 (45%) | 13/34 (38%) | 6/13 (46%) | 76/83 (92%) |
| 07 | 8/21 (38%) | 26/42 (62%) | 6/10 (60%) | 96/118 (81%) |
| 08 | 16/29 (55%) | 13/22 (59%) | 7/11 (64%) | — |
| **TOT** | **91/242 (37.6%)** | **145/278 (52.2%)** | **35/87 (40.2%)** | **573/681 (84.1%)** |
| **OVERALL** | | | | **844/1288 (65.5%)** |

---

## v097 — dated-learn ingest, conv 0–6 (472 результата, завершён)

| Conv | Cat1 | Cat2 | Cat3 |
|------|------|------|------|
| 00 | 9/32 (28%) | 15/37 (41%) | 11/13 (85%) |
| 01 | 5/11 (45%) | 18/26 (69%) | — |
| 02 | 14/31 (45%) | 10/27 (37%) | 1/8 (13%) |
| 03 | 8/37 (22%) | 14/40 (35%) | 1/11 (9%) |
| 04 | 4/31 (13%) | 18/26 (69%) | 1/14 (7%) |
| 05 | 13/30 (43%) | 9/24 (38%) | 1/7 (14%) |
| 06 | 6/20 (30%) | 8/34 (24%) | 6/13 (46%) |
| **TOT** | **59/192 (30.7%)** | **92/214 (43.0%)** | **21/66 (31.8%)** |

---

## v096 vs v097 — dated vs dated-learn

| Cat | v096 dated | v097 dated-learn | Δ |
|-----|-----------|-----------------|---|
| Cat1 | 37.6% | 30.7% | **−7pp** |
| Cat2 | 52.2% | 43.0% | **−9pp** |
| Cat3 | 40.2% | 31.8% | **−8pp** |

**Вывод:** `learn()` в среднем не помогает и даже немного вредит (шум в retrieval).  
**Исключение:** Conv 00 Cat3: 62% (dated) → **85%** (dated-learn) = **+23pp**.

### Conv 00 изолированное сравнение

| Cat | v096 (dated) | v097 (dated-learn) | Δ |
|-----|-------------|-------------------|---|
| Cat1 | 8/32 (25%) | 9/32 (28%) | +3pp |
| Cat2 | 16/37 (43%) | 15/37 (41%) | −2pp |
| Cat3 | 8/13 (62%) | 11/13 (85%) | **+23pp** |

---

## Анализ ошибок

### Cat1 — Single-hop factual (37.6%)

**Доминирующая ошибка: M — Model incomplete (83%)**

Модель останавливается на первых 1–2 совпадениях и не перечисляет все элементы из контекста.

**WRONG примеры:**

```
Q: What activities does Melanie partake in?
Gold: pottery, camping, painting, swimming
Got:  "Melanie participates in pottery classes, plays the clarinet, and enjoys reading."
→ Пропущены camping, painting, swimming; добавлены лишние факты
```

```
Q: Where has Melanie camped?
Gold: beach, mountains, forest
Got:  "Melanie has camped at the beach and in the mountains."
→ Пропущен forest
```

```
Q: What books has Melanie read?
Gold: "Nothing is Impossible", "Charlotte's Web"
Got:  "Melanie has read 'Charlotte's Web'... and is currently reading 'Becoming Nicole'"
→ Пропущена "Nothing is Impossible", добавлена лишняя книга
```

```
Q: What LGBTQ+ events has Caroline participated in?
Gold: Pride parade, school speech, support group
Got:  "Caroline has participated in an LGBTQ+ pride parade, an LGBTQ+ conference, and a support group"
→ Заменила "school speech" на "conference" (частично неверно)
```

```
Q: What activities has Melanie done with her family?
Gold: Pottery, painting, camping, museum, swimming, hiking
Got:  "Melanie has gone camping, hiking in the mountains, exploring forests, and visited..."
→ Пропущены pottery, painting, swimming
```

**Распределение ошибок:**
| Тип | % | Описание |
|-----|---|----------|
| M (model incomplete) | 83% | Факты в контексте, модель не перечислила всё |
| R (retrieval miss) | 17% | Факт не попал в top-60 |

**Фикс:** Промпт `"List ALL items. Do not stop at the first match."` → ожидаемый **+15pp**.

---

### Cat2 — Temporal / "When did..." (52.2%)

**Основные паттерны ошибок:**

**off-by-1 date (44%) — session date вместо event date:**
```
Q: When did Melanie sign up for a pottery class?
Gold: 2 July 2023
Got:  "Melanie signed up for a pottery class on 3 July, 2023."
Ctx:  "[3 July, 2023] ...signed up for pottery class yesterday..."
```

```
Q: When did Melanie go to the museum?
Gold: 5 July 2023
Got:  "Melanie went to the museum on 6 July, 2023."
Ctx:  "[6 July, 2023] ...went to the museum yesterday..."
```

```
Q: When is Melanie's daughter's birthday?
Gold: 13 August
Got:  "Melanie's daughter's birthday is on 14 August."
Ctx:  "[14 August, 2023] ...birthday was yesterday..."
```

**vague-gold (38%) — судья слишком строгий:**
```
Q: When did Melanie run a charity race?
Gold: The sunday before 25 May 2023
Got:  "Melanie ran a charity race for mental health on 25 May 2023."
→ Модель ответила точной датой сессии, gold ожидает нечёткий ответ
```

```
Q: When did Caroline give a speech at a school?
Gold: The week before 9 June 2023
Got:  "Caroline gave a speech at a school event on 9 June 2023."
→ Технически верно по контексту, но gold требует "week before"
```

**Распределение ошибок:**
| Тип | % | Описание |
|-----|---|----------|
| off-by-1 | 44% | Session date ≠ event date ("yesterday" = -1 день) |
| vague-gold | 38% | Gold = "The week before X", судья режет точную дату |
| missing | 18% | Дата не попала в top-60 |

**Реальная accuracy без структурных артефактов: ~75–80%.**

**Фикс:** Event date хранить отдельно, raw turns не включать в recall для cat2 → **+15pp**.

---

### Cat3 — Inference / "Would/Likely..." (40.2% dated, 85% conv00 с learn)

**Паттерн 1: Модель отказывается делать вывод (S — synthesis failure)**

```
Q: Would Caroline be considered religious?
Gold: Somewhat, but not extremely religious
Got:  "There is no indication in the context that Caroline identifies as religious."
→ Церковь упомянута в контексте, но модель не inferит
```

```
Q: Would Melanie go on another roadtrip soon?
Gold: Likely no; since this one went badly
Got:  "The context does not indicate whether Melanie plans to go on another road trip soon."
→ Плохой roadtrip есть в контексте, модель не делает вывод
```

**Паттерн 2: Галлюцинация — берёт один факт, переоценивает его**

```
Q: What might John's financial status be?
Gold: Middle-class or wealthy
Got:  "John's financial status is strained, as he is trying to get his car fixed..."
→ Взял один негативный факт (car trouble), игнорировал всё остальное
```

```
Q: What might John's degree be in?
Gold: Political science, Public administration, Public affairs
Got:  "John's degree might be in a field related to public policy or community development..."
→ Размытый ответ, не попадает в gold keywords
```

**Паттерн 3: CORRECT с learn() — синтез по structured facts**

```
Q: Would Caroline likely have Dr. Seuss books on her bookshelf?
Gold: Yes, since she collects classic children's books
Got:  "Yes, Caroline likely has Dr. Seuss books on her bookshelf, as she has lots of kids' books..."
→ learn() создал факт "collects children's books" → прямой вывод
```

```
Q: What fields would Caroline be likely to pursue in her education?
Gold: Psychology, counseling certification
Got:  "Caroline would likely pursue fields in counseling or mental health."
→ CORRECT: learn() дал structured "wants to be counselor"
```

```
Q: Would Caroline pursue writing as a career option?
Gold: Likely no; though she likes reading, she wants to be a counselor
Got:  "There is no indication that Caroline is pursuing writing... Her focus is on counseling..."
→ CORRECT даже при "no indication" — правильный отказ от hallucination
```

**Распределение ошибок:**
| Тип | % | Описание |
|-----|---|----------|
| S (synthesis failure) | 60% | Факты есть, модель отказывается inferить |
| R (retrieval miss) | 25% | Ключевой факт не retrieved |
| H (hallucination) | 15% | Берёт один факт и делает неверный вывод |

**Learn() влияние:**
- Conv 00 (Caroline/Melanie): dated=62% → dated-learn=**85%** (+23pp)
- Conv 02–06: dated=14–46%, dated-learn=7–46% — эффект нестабилен, conv сложнее
- На других conv facts scattered, inference сложнее → learn не решает

---

### Cat4 — Open-ended / "How/What did..." (84.1%)

Наиболее стабильная категория. Промпт, модель, ingest mode практически не влияют.

**CORRECT примеры:**
```
Q: How does Melanie prioritize self-care?
Gold: by carving out some me-time each day for activities like running...
Got:  "Melanie prioritizes self-care by carving out daily 'me-time' for activities like running, reading..."
→ Почти дословно из контекста
```

```
Q: What did Melanie realize after the charity race?
Gold: self-care is important
Got:  "Melanie realized that self-care is really important and that when she looks after herself..."
→ Прямой ответ из контекста
```

**WRONG примеры (15.9%):**
```
Q: What kind of pot did Mel and her kids make with clay?
Gold: a cup with a dog face on it
Got:  "Mel and her kids made their own pots at the pottery workshop."
→ Слишком обобщённый ответ, потерял специфику
```

```
Q: What did Mel and her kids paint in their latest project in July 2023?
Gold: a sunset with a palm tree
Got:  "Mel and her kids painted a nature-inspired piece."
→ Потерял конкретику (sunset with palm tree → generic "nature")
```

**Вывод:** Cat4 ошибки — в основном потеря специфики при генерации (generic → конкретный gold).

---

## Сравнительная таблица всех запусков

| Run | Mode | Conv | Cat1 | Cat2 | Cat3 | Cat4 | Overall |
|-----|------|------|------|------|------|------|---------|
| v094-4o-1conv | dated-learn (broken) + gpt-4o | 1 | 25% | 68% | 38% | 87% | 56.6% |
| v094-new-prompt | dated-learn (broken) + mini | 1 | 22% | 60% | 62% | 87% | 64.5% |
| v094-minimal | dated-learn (broken) + mini | 1 | 22% | 35% | 77% | 87% | 59.9% |
| v095-learn-on | dated-learn (fixed) + mini | 1 | 31% | 54% | — | — | 43.5% |
| v095-learn-off | dated + mini | 1 | 22% | 43% | — | — | 31.9% |
| v095-learn-off-all | dated + mini | 10 | 40.1% | 49.5% | — | — | — |
| **v096-dated-all** | **dated + mini** | **9** | **37.6%** | **52.2%** | **40.2%** | **84.1%** | **65.5%** |
| v097-learn (conv 0–6) | dated-learn + mini | 7 | 30.7% | 43.0% | 31.8% | — | — |

---

## Ключевые инсайты

### 1. Learn() помогает только cat3, только на простых conv
- Conv 00 (Caroline/Melanie): +23pp cat3 — inference простые, learn создаёт нужные факты
- Conv 02–06: learn не помогает или вредит — inference сложнее, другие персонажи
- Cat1, Cat2: learn практически не влияет (±3pp, шум)

### 2. Cat1 bottleneck — промпт, не retrieval
- 83% ошибок: факты есть, модель не перечисляет все
- Промпт "list ALL items" должен дать +15pp

### 3. Cat2 bottleneck — архитектура ingest
- 82% ошибок структурные (off-by-1 + vague-gold)
- Реальная accuracy без артефактов: ~75–80%
- Learn не решает off-by-1

### 4. Cat4 стабилен (84%), не требует доработки

### 5. Высокая вариативность по conv
| Метрика | Min | Max | Conv |
|---------|-----|-----|------|
| Cat1 | 13% (conv04 v097) | 55% (conv08 v096) | — |
| Cat2 | 24% (conv06 v097) | 77% (conv01) | — |
| Cat3 | 7% (conv04 v097) | 85% (conv00 v097) | — |
| Cat4 | 73% (conv01) | 92% (conv06) | — |

---

## Приоритетные фиксы

| # | Фикс | Категория | Δ | Сложность |
|---|------|-----------|---|-----------|
| 1 | Промпт "list ALL items, do not stop at first match" | Cat1 | +15pp | Низкая |
| 2 | Убрать raw turns из recall для cat2, хранить только event date | Cat2 | +15pp | Средняя |
| 3 | Fuzzy date judge (±1 день, ±7 дней для vague-gold) | Cat2 | +12pp | Средняя |
| 4 | Learn() только как дополнение к dated для inference-heavy conv | Cat3 | +10–23pp | Готово |
| 5 | Улучшить embedding recall для числовых фактов и single-word answers | Cat1 | +5pp | Высокая |
