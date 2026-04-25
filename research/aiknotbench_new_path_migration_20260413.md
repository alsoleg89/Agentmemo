# aiknotbench: migration to the new query path

## Goal

Switch `aiknotbench` from the old benchmark path:

```ts
question -> adapter.recall() -> context -> answer model -> judge
```

to the new path:

```ts
question -> adapter.query() -> answer/evidence/trace -> judge
```

The key change is:

- old benchmark measures `kb.recall()`
- new benchmark must measure the new product query path (`raw_query` / `raw_query_with_trace`)

---

## Minimal required changes

### 1. `aiknotbench/src/aiknot.ts`

Replace the old adapter surface:

```ts
async recall(question: string): Promise<string> {
  return this.kb.recall(question, { topK: this.topK });
}
```

with the new adapter surface:

```ts
async query(question: string): Promise<{
  answer: string;
  evidence: string;
  trace?: unknown;
}> {
  const raw = await this.kb.raw_query_with_trace(question);
  return {
    answer: raw.answer,
    evidence: raw.items
      .map((x: { text: string }, i: number) => `[${i + 1}] ${x.text}`)
      .join("\n"),
    trace: raw.trace,
  };
}
```

If `raw_query_with_trace()` does not exist yet, use:

```ts
async query(question: string): Promise<{
  answer: string;
  evidence: string;
}> {
  const raw = await this.kb.raw_query(question);
  return {
    answer: raw.answer,
    evidence: raw.items
      .map((x: { text: string }, i: number) => `[${i + 1}] ${x.text}`)
      .join("\n"),
  };
}
```

---

### 2. `aiknotbench/src/runner.ts`

Replace the old benchmark call site:

```ts
const context = await adapter.recall(qa.question);
const { text: answer, usage: answerUsage } = await fns.answerFn(answerModel, context, qa.question);
const { verdict, usage: judgeUsage } = await fns.judgeFn(
  judgeModel,
  qa.question,
  answer,
  qa.answer
);
```

with:

```ts
const result = await adapter.query(qa.question);
const answer = result.answer;
const answerUsage = { promptTokens: 0, completionTokens: 0 };
const { verdict, usage: judgeUsage } = await fns.judgeFn(
  judgeModel,
  qa.question,
  answer,
  qa.answer
);
```

This is the actual switch from:

- benchmarking `retrieved context`

to:

- benchmarking the `new query path answer`

---

### 3. `aiknotbench/src/runner.ts` interface

Replace:

```ts
export interface AiknotAdapterLike {
  ingest(turns: string[], sessions?: import("./locomo.js").Session[]): Promise<void>;
  recall(question: string): Promise<string>;
  close(): Promise<void>;
}
```

with:

```ts
export interface AiknotAdapterLike {
  ingest(turns: string[], sessions?: import("./locomo.js").Session[]): Promise<void>;
  query(question: string): Promise<{
    answer: string;
    evidence: string;
    trace?: unknown;
  }>;
  close(): Promise<void>;
}
```

---

### 4. `aiknotbench/src/runner.ts` log entry

Keep `context` for backward compatibility, but fill it with evidence from the new query path.

Replace:

```ts
appendLog(runId, {
  ts: new Date().toISOString(),
  convIdx: conv.idx,
  qaIdx: qa.idx,
  category: qa.category,
  question: qa.question,
  goldAnswer: qa.answer,
  context,
  answer,
  verdict,
  answerUsage,
  judgeUsage,
});
```

with:

```ts
appendLog(runId, {
  ts: new Date().toISOString(),
  convIdx: conv.idx,
  qaIdx: qa.idx,
  category: qa.category,
  question: qa.question,
  goldAnswer: qa.answer,
  context: result.evidence,
  answer,
  verdict,
  answerUsage,
  judgeUsage,
  trace: result.trace,
});
```

Also extend `LogEntry`:

```ts
interface LogEntry {
  ts: string;
  convIdx: number;
  qaIdx: number;
  category: number;
  question: string;
  goldAnswer: string;
  context: string;
  answer: string;
  verdict: Verdict;
  answerUsage: Usage;
  judgeUsage: Usage;
  trace?: unknown;
}
```

---

## What does **not** need to change immediately

### `aiknotbench/src/evaluator.ts`

No required code changes for the migration itself.

Reason:

- `judgeAnswer()` is still used
- `answerQuestion()` simply stops being used in the new path

So for the migration:

- keep `judgeAnswer()`
- do not call `answerQuestion()` from `runner.ts`

---

## Smallest possible summary

If reduced to the essence, the migration is:

### Old

```ts
const context = await adapter.recall(qa.question);
const { text: answer } = await fns.answerFn(answerModel, context, qa.question);
```

### New

```ts
const result = await adapter.query(qa.question);
const answer = result.answer;
```

Everything else is just typing and logging around that switch.

---

## Definition of done

The migration is complete when:

1. `runner.ts` no longer calls `adapter.recall(...)`
2. `runner.ts` no longer calls `answerFn(...)` in the new path
3. `aiknot.ts` exposes `query(...)`
4. benchmark logs store `result.evidence` and optional `trace`
5. judge still compares `answer` vs `gold`

At that point `aiknotbench` is no longer measuring the old `recall()` surface. It is measuring the new query path.
