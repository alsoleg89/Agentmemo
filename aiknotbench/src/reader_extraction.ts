import { generateText } from "ai";
import type { LanguageModelV1 } from "ai";

import { answerQuestion } from "./evaluator.js";
import type { AnswerResult } from "./evaluator.js";

function sanitize(s: string): string {
  // eslint-disable-next-line no-control-regex
  return s.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");
}

async function withRetry<T>(fn: () => Promise<T>, maxAttempts = 6): Promise<T> {
  let delay = 5000;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err) {
      const msg = String(err);
      const isRateLimit = msg.includes("Rate limit") || msg.includes("429");
      if (!isRateLimit || attempt === maxAttempts) throw err;
      const wait = delay + Math.random() * 1000;
      process.stderr.write(
        `  [rate limit] waiting ${(wait / 1000).toFixed(1)}s (attempt ${attempt}/${maxAttempts})\n`
      );
      await new Promise((r) => setTimeout(r, wait));
      delay = Math.min(delay * 2, 60000);
    }
  }
  throw new Error("unreachable");
}

const EXTRACT_SYSTEM =
  `Extract every fact from the memory context that could help answer the question. ` +
  `Output one fact per line. Be exhaustive — include all relevant details.`;

const COMPOSE_SYSTEM =
  `Compose a concise answer using only the provided facts. Answer directly without preamble.`;

/**
 * Deduplicate a list of candidate strings.
 * Strips common list prefixes (-, •, 1., etc.), case-folds, and removes
 * punctuation-only keys before comparing. First occurrence wins.
 */
export function dedupCandidates(items: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of items) {
    const item = raw.replace(/^(?:[-•*]\s+|\d+[.)]\s*)/, "").trim();
    if (!item) continue;
    const key = item.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (key.length > 0 && !seen.has(key)) {
      seen.add(key);
      result.push(item);
    }
  }
  return result;
}

/**
 * Three-stage extraction reader for list/profile/count questions.
 *
 * Stage A — extract all candidate facts from context (LLM).
 * Stage B — deduplicate candidates (deterministic case-fold).
 * Stage C — compose final answer from deduplicated facts (LLM).
 *
 * Falls back to the single-pass answerQuestion when Stage A returns nothing.
 */
export async function answerWithExtraction(
  model: LanguageModelV1,
  context: string,
  question: string
): Promise<AnswerResult> {
  // Stage A: extract candidate facts
  const { text: raw, usage: usageA } = await withRetry(() =>
    generateText({
      model,
      system: EXTRACT_SYSTEM,
      messages: [
        {
          role: "user",
          content: `Context:\n${sanitize(context)}\n\nQuestion: ${sanitize(question)}\n\nFacts:`,
        },
      ],
      maxTokens: 512,
      temperature: 0,
    })
  );

  // Stage B: deduplicate
  const candidates = dedupCandidates(raw.split("\n"));

  // Fallback when extraction yields nothing useful
  if (candidates.length === 0) {
    return answerQuestion(model, context, question);
  }

  // Stage C: compose from deduplicated facts
  const factsText = candidates.map((f, i) => `${i + 1}. ${f}`).join("\n");
  const { text, usage: usageC } = await withRetry(() =>
    generateText({
      model,
      system: COMPOSE_SYSTEM,
      messages: [
        {
          role: "user",
          content: `Facts:\n${factsText}\n\nQuestion: ${sanitize(question)}`,
        },
      ],
      maxTokens: 256,
      temperature: 0,
    })
  );

  return {
    text: text.trim(),
    usage: {
      promptTokens: usageA.promptTokens + usageC.promptTokens,
      completionTokens: usageA.completionTokens + usageC.completionTokens,
    },
  };
}
