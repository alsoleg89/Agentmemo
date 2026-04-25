# Aggregation Recall — Design Research

**Date:** 2026-04-11

---

## Problem Statement

Current `recall(query)` is ad-hoc retrieval: BM25 → top-60 by relevance → stop.
No way to say "give me ALL facts about X". Fact at position 61 is lost forever.

This is the root cause of Cat1 aggregation failures:
- "What activities does Melanie do?" → swimming at pos 7, pottery at pos 23, hiking at pos 41
- top-60 by BM25 includes all of them, but model still misses some (M-type failure)
- "give me everything agents said about Docker" → same problem, real-world use case

---

## Current Architecture Gap

### `add(content)` — raw ingestion
```python
Fact(content="Melanie went swimming with kids",
     entity="",     # EMPTY
     attribute="",  # EMPTY
     slot_key="",   # EMPTY
     tags=[])
```

### `learn(turns)` — LLM extraction (expensive)
```python
# LLM returns:
{"content": "Melanie likes swimming",
 "entity": "melanie",       # populated by LLM
 "attribute": "hobbies",    # populated by LLM
 "value": "swimming",
 "tags": ["hobbies", "activities"]}
# → Fact with slot_key = "melanie::hobbies"
```

**Gap:** `entity` fields are ONLY populated by `learn()`. In dated/add mode: `entity=""`.
Entity dictionary in `_build_entity_dictionary()` is empty in learn-OFF mode.

---

## API Design Options

### A — New method `recall_all(entity)`
```python
kb.recall_all("Melanie")
# → {"activities": [...], "family": [...], "events": [...]}
```
- User explicitly requests exhaustive mode
- Clean separation: different method = different return type (grouped dict)
- **Best for:** "give me everything about X" use cases

### B — Parameter on existing `recall()`
```python
kb.recall("What does Melanie do?", exhaustive=True)
```
- Same function, opt-in behavior
- Less clean: why would user know to pass `exhaustive=True`?

### C — Automatic (REJECTED)
```python
kb.recall("What does Melanie do?")
# system internally: detects "Melanie" → expands recall
```
- Implicit routing — system guesses intent
- Violates no-intent-routing constraint
- **REJECTED** for same reason as TEMPORAL intent detection

**Decision: Option A (`recall_all`) is correct.** Explicit first-class method.

---

## Entity Tagging Without LLM

For `recall_all` to work, facts must be indexed by entity at ingest time.
Options (no LLM):

| Approach | Quality | Cost | Works for |
|----------|---------|------|-----------|
| Speaker extraction | Excellent | Free | `[date] Melanie: ...` → entity="Melanie" |
| Heuristic NER (caps noun phrases) | Medium | Free | "Docker", "Kubernetes", names |
| spaCy NER | Good | ~50ms/doc | Any entity |
| LLM (existing learn()) | Excellent | Expensive | Everything |

For LoCoMo (dated mode, turns like "[8 May] Melanie: I love swimming"):
- **Speaker extraction is free and exact** — subject always before `:`
- Would give entity="Melanie" for free at `add_episodic()` / `ingestDated` time

For real-world use case (code agents talking about Docker):
- Heuristic NER: extract capitalized multi-char tokens
- Or spaCy if accuracy matters

---

## TurboQuant (Google, 2026) — Context

Google's KV cache compression: 6x memory reduction, 8x attention speedup, 3 bits/value,
training-free, zero accuracy loss. Presented at ICLR 2026.

Connection to ai-knot:
- Operates inside LLM inference (KV cache), not at retrieval layer
- If providers adopt it → longer contexts become cheaper
- Could change top-k sizing calculus (60 facts → 360 facts at same cost)
- Does NOT solve the retrieval/aggregation problem — still need right facts in context

---

## Existing Building Blocks in Code

- `Fact.entity`, `Fact.attribute`, `Fact.slot_key` — fields exist, empty in add() mode
- `_build_entity_dictionary()` — collects entity names from fact.entity + value_text
- `_build_entity_mention_index()` — entity → set[fact_ids] by substring match in content
- These currently used ONLY for multi-hop scoring in `_execute_recall()`
- `get_by_tag(tag)` — all facts with given tag (exists, but requires manual tags at add time)

---

## Lookup Index — Metric Validation

**Date:** 2026-04-11
**Run:** v095-learn-off-all (dated mode, 9 convs, 250 Cat1 questions)

### Failure Breakdown (actual recall context from log.jsonl)

| Type | Count | % of wrong | Lookup fixes? |
|------|-------|------------|---------------|
| R-missing (answer never stored in index) | 38 | 24% | no |
| **R-topk miss (in index, not in top-60)** | **36** | **23%** | **YES** |
| M-type (in top-60, model didn't enumerate) | 81 | 52% | no |

### Theoretical Max Improvement

```
Current:    95/250 = 38%
After fix: 131/250 = 52%  (+14.4pp)
```

### Per-Conv Breakdown

| Conv | Current | After | Delta |
|------|---------|-------|-------|
| 00 | 7/32 (22%) | 10/32 (31%) | +3 |
| 01 | 5/11 (45%) | 6/11 (55%) | +1 |
| 02 | 14/31 (45%) | 21/31 (68%) | +7 |
| 03 | 9/37 (24%) | 13/37 (35%) | +4 |
| 04 | 9/31 (29%) | 13/31 (42%) | +4 |
| 05 | 18/30 (60%) | 22/30 (73%) | +4 |
| 06 | 9/20 (45%) | 13/20 (65%) | +4 |
| 07 | 6/21 (29%) | 9/21 (43%) | +3 |
| 08 | 18/37 (49%) | 24/37 (65%) | +6 |

### Pattern

Aggregation questions ("What activities does Melanie do?"):
- pottery/camping/painting → in top-60 ✓
- swimming → at position 61+, missed ✗
- Lookup index: returns ALL facts with "melanie" token → swimming included

### M-Type Remaining Problem (81 questions, 52%)

Answer IS in top-60, model doesn't enumerate all items.
Separate problem, separate solution needed.
Lookup index alone cannot fix this.

---

## Architecture: Two Types of Index

```
BM25 index:   term → [(fact_id, weight), ...]  → ranked, cutoff (existing)
Lookup index: term → {fact_id, fact_id, ...}   → set, no cutoff (needed)
```

### Build Strategy

At `add(content)` time:
```python
for token in tokenize(content):
    if len(token) > 2:
        self._lookup_index[token].add(fact_id)
```

At retrieval for aggregation:
```python
query_tokens = tokenize(query)
candidate_ids = set()
for t in query_tokens:
    candidate_ids |= self._lookup_index.get(t, set())
# → all facts with any query token, no cutoff
# → rank within this set using BM25 for ordering
```

### Why This Is Generic

- Works for any text content, no entity fields required
- No LLM, no NER, no benchmark-specific patterns
- "give me all facts about Docker" → lookup["docker"] → all Docker facts
- Any user with overlapping content benefits

### Two Modes

**learn-OFF:** lookup index on raw content tokens → works immediately
**learn-ON:** same lookup index + additionally entity fields are available
              → can use entity_index for structured recall_all

### Next Problem After Lookup Index

M-type (81 questions): facts in context, model doesn't enumerate.
Options:
1. Entity-grouped format in recall output (group facts by entity before presenting)
2. Better prompt instructions ("list ALL items found")
3. Dedicated recall_all API that returns grouped/structured response
