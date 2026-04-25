# LoCoMo learn-off partial results — conv 0–5

**Run:** `v095-learn-off-all`  
**Mode:** `dated` (no learn), ingest-mode=dated, top-k=60  
**Answer model:** gpt-4o-mini, **Judge:** gpt-4o-mini  
**Prompt:** v3 minimal  
**Status:** 6/10 conv completed (341 questions), stalled at conv 06 due to 401 error  
**Date:** 2026-04-11

---

## Итоговая таблица (conv 0–5)

| Conv | Cat1 correct/total | Cat1 % | Cat2 correct/total | Cat2 % |
|------|--------------------|--------|---------------------|--------|
| 00   | 7/32               | 21.9%  | 16/37               | 43.2%  |
| 01   | 5/11               | 45.5%  | 20/26               | **76.9%** |
| 02   | 14/31              | 45.2%  | 11/27               | 40.7%  |
| 03   | 9/37               | 24.3%  | 15/40               | 37.5%  |
| 04   | 9/31               | 29.0%  | 16/26               | 61.5%  |
| 05   | 14/23              | **60.9%** | 10/20            | 50.0%  |
| **TOTAL** | **58/165** | **35.2%** | **88/176** | **50.0%** |

---

## Анализ ошибок Cat1 (107 WRONG)

| Тип | Кол-во | % | Описание |
|-----|--------|---|----------|
| **M — Model incomplete** | 89 | 83.2% | Факты есть в контексте, модель не перечислила все |
| **R — Retrieval failure** | 18 | 16.8% | Нужный факт отсутствует в top-60 |

### Cat1 по conv

| Conv | Cat1 % | Wrong total | R | M |
|------|--------|-------------|---|---|
| 00   | 21.9%  | 25          | 2 | 23 |
| 01   | 45.5%  | 6           | 1 | 5  |
| 02   | 45.2%  | 17          | 3 | 14 |
| 03   | 24.3%  | 28          | 8 | 20 |
| 04   | 29.0%  | 22          | 3 | 19 |
| 05   | 60.9%  | 9           | 1 | 8  |

### Cat1 выводы

- **Dominant failure (83%):** модель видит факты в контексте, но не перечисляет все. Типичный pattern: вопрос "What activities does X do?" → модель даёт 2 из 4 активностей.
- **Retrieval (17%):** числа ("3", "2"), одиночные прилагательные, названия книг.
- **Conv 03** — высокий R (8) vs остальных. Вероятно, этот разговор имеет более сложную структуру хранения фактов.
- **Conv 05** — лучший cat1 (60.9%) при минимальном R. Меньше вопросов (23), вероятно более прямые вопросы.

---

## Анализ ошибок Cat2 (88 WRONG)

| Тип | Кол-во | % | Описание |
|-----|--------|---|----------|
| **off-by-1 date** | 39 | 44.3% | Событие "вчера" → модель читает session date вместо event date |
| **vague-gold** | 33 | 37.5% | Gold = "The week before X" — нет точной даты в контексте |
| **missing** | 16 | 18.2% | Дата вообще не попала в top-60 |

### Cat2 по conv

| Conv | Cat2 % | Wrong total | off-by-1 | vague-gold | missing |
|------|--------|-------------|----------|------------|---------|
| 00   | 43.2%  | 21          | 8  | 10 | 3 |
| 01   | 76.9%  | 6           | 6  | 0  | 0 |
| 02   | 40.7%  | 16          | 6  | 8  | 2 |
| 03   | 37.5%  | 25          | 9  | 12 | 4 |
| 04   | 61.5%  | 10          | 6  | 1  | 3 |
| 05   | 50.0%  | 10          | 4  | 2  | 4 |

### Cat2 примеры off-by-1

```
Q: "When did Caroline go to the LGBTQ support group?"
Gold: 7 May 2023
Got:  "Caroline went to the LGBTQ support group on 8 May, 2023."
Ctx:  "[8 May, 2023] Caroline: I went to a LGBTQ support group yesterday..."
```

```
Q: "When did Melanie sign up for a pottery class?"
Gold: 2 July 2023
Got:  "Melanie signed up for a pottery class on 3 July 2023."
Ctx:  "[3 July, 2023] ...signed up for pottery class yesterday..."
```

Паттерн стабильный: raw turn имеет session date, событие было "yesterday" → модель читает session date.

### Cat2 выводы

- **off-by-1 (44%)** — основная механика: `dated` ingest хранит сырые тёрны с датой сессии; событие "yesterday" → даёт дату на 1 день позже. Известный артефакт, не фиксится без изменения ingest-логики.
- **vague-gold (37%)** — gold answers в датасете типа "The week before 9 June 2023". Модель отвечает с точной датой — судья режет как WRONG. Это ограничение датасета, не модели.
- **missing (18%)** — дата не попала в top-60, ответ невозможен даже теоретически.
- **Conv 01 — лучший (76.9%)** — нет vague-gold вопросов в этом разговоре. Все 6 ошибок — off-by-1.
- **Conv 03 — худший (37.5%)** — много vague-gold (12 из 25 ошибок). Самый большой набор cat2 вопросов (40).

---

## Сравнение с предыдущими запусками (conv 0 только)

| Run | Mode | Cat1 | Cat2 |
|-----|------|------|------|
| v094-openai-1conv-4o | dated-learn (деградированный) + gpt-4o | 25% | 67.6% |
| v094-learn-fixed | dated-learn (старая сборка) | 34.4% | 51.4% |
| **v095-learn-off-all** | **dated only** | **21.9%** | **43.2%** |
| v095-learn-on-cat12 | dated-learn (новая сборка) | 31.3% | 54.1% |

### Дельта learn-on vs learn-off (conv 0)

- Cat1: 31.3% → 21.9% = **+9.4pp** от learn
- Cat2: 54.1% → 43.2% = **+10.9pp** от learn

---

## Структурные ограничения датасета

Часть "ошибок" — ограничения самого датасета:

1. **vague-gold (37% cat2 ошибок)** — gold ответ "The week before 9 June 2023", хотя в контексте только точная дата. Судья gpt-4o-mini режет точный ответ как WRONG.
2. **off-by-1 (44% cat2 ошибок)** — в LoCoMo10 события описаны как "yesterday/last week". Gold — настоящая дата события. В контексте — дата сессии (+1 день). Это структурная проблема ingest, не промпта.
3. **Cat1 M (83% cat1 ошибок)** — вопросы "What activities does X do?" требуют перечисления ВСЕХ активностей. Модель останавливается на первых 1-2 из контекста.

---

## Потенциальные фиксы

| Проблема | Тип | Возможный фикс | Impact |
|----------|-----|----------------|--------|
| off-by-1 | ingest | В `ingestLearn` хранить event date отдельно; в `ingestDated` не включать в recall для cat2 | ~+15pp cat2 |
| M (incomplete list) | model/prompt | Добавить в промпт "list ALL items, do not stop at first match" | ~+15pp cat1 |
| vague-gold | judge | Fuzzy match judge или проверять ±7 дней | ~+12pp cat2 |
| missing | retrieval | Увеличить top-k или улучшить embedding для числовых фактов | ~+5pp cat1/cat2 |
