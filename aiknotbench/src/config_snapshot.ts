/**
 * Canonical settings management for reproducible bench runs.
 *
 * Provides helpers to load the pinned canonical.json, hash it for
 * stable identity, resolve the effective run config from CLI + env,
 * diff against canonical, and enforce strict-or-warn drift policy.
 */
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CanonicalConfig {
  schema_version: number;
  models: {
    answer: string;
    answer_temperature: number;
    answer_max_tokens: number;
    judge: string;
    judge_temperature: number;
    judge_max_tokens: number;
    embed_model: string;
    embed_url: string;
  };
  retrieval: {
    top_k: number;
    profile: string;
    ingest_mode: string;
    ddsa_enabled: boolean;
    llm_recall: boolean;
    rrf_weights: number[];
  };
  dataset: {
    path: string;
    sha256: string;
    convs_default: number[];
  };
  prompts: {
    answer_system_sha256: string;
    answer_user_template_sha256: string;
    judge_system_sha256: string;
  };
  env_allowlist: string[];
}

export interface ResolvedRunConfig {
  answer_model: string;
  judge_model: string;
  top_k: number;
  profile: string;
  ingest_mode: string;
  ddsa_enabled: boolean;
  llm_recall: boolean;
  embed_model: string;
  embed_url: string;
  dataset_path: string;
  convs: number[];
  allow_drift: boolean;
}

// ---------------------------------------------------------------------------
// Load + hash canonical
// ---------------------------------------------------------------------------

const CANONICAL_PATH = resolve(
  new URL(".", import.meta.url).pathname,
  "../config/canonical.json"
);

export function loadCanonical(): CanonicalConfig {
  if (!existsSync(CANONICAL_PATH)) {
    throw new Error(`canonical.json not found at ${CANONICAL_PATH}`);
  }
  return JSON.parse(readFileSync(CANONICAL_PATH, "utf-8")) as CanonicalConfig;
}

export function hashCanonical(): string {
  const bytes = readFileSync(CANONICAL_PATH);
  return createHash("sha256").update(bytes).digest("hex");
}

// ---------------------------------------------------------------------------
// Resolve effective run config from CLI args + env
// ---------------------------------------------------------------------------

export interface RunArgs {
  answerModel?: string;
  judgeModel?: string;
  topK?: number;
  ingestMode?: string;
  convs?: number[];
  allowDrift?: boolean;
}

export function resolveRunConfig(
  args: RunArgs,
  env: NodeJS.ProcessEnv
): ResolvedRunConfig {
  const canonical = loadCanonical();
  return {
    answer_model:
      args.answerModel ??
      env["DEFAULT_ANSWER_MODEL"] ??
      canonical.models.answer,
    judge_model:
      args.judgeModel ??
      env["DEFAULT_JUDGE_MODEL"] ??
      canonical.models.judge,
    top_k: args.topK ?? canonical.retrieval.top_k,
    profile:
      env["AIKNOT_QUERY_PROFILE"] ?? canonical.retrieval.profile,
    ingest_mode: args.ingestMode ?? canonical.retrieval.ingest_mode,
    ddsa_enabled:
      (env["AIKNOT_DDSA_ENABLED"] ?? "false") === "true",
    llm_recall: (env["AI_KNOT_LLM_RECALL"] ?? "false") === "true",
    embed_model:
      env["AI_KNOT_EMBED_MODEL"] ?? canonical.models.embed_model,
    embed_url:
      env["AI_KNOT_EMBED_URL"] ?? canonical.models.embed_url,
    dataset_path: canonical.dataset.path,
    convs: args.convs ?? canonical.dataset.convs_default,
    allow_drift: args.allowDrift ?? false,
  };
}

// ---------------------------------------------------------------------------
// Diff against canonical
// ---------------------------------------------------------------------------

type Primitive = string | number | boolean;

export function diffAgainstCanonical(
  resolved: ResolvedRunConfig
): string[] {
  const canonical = loadCanonical();
  const deviations: string[] = [];

  function check(key: string, actual: Primitive, expected: Primitive): void {
    if (String(actual) !== String(expected)) {
      deviations.push(`${key}: expected=${String(expected)} actual=${String(actual)}`);
    }
  }

  check("models.answer", resolved.answer_model, canonical.models.answer);
  check("models.judge", resolved.judge_model, canonical.models.judge);
  check("retrieval.top_k", resolved.top_k, canonical.retrieval.top_k);
  check("retrieval.profile", resolved.profile, canonical.retrieval.profile);
  check("retrieval.ingest_mode", resolved.ingest_mode, canonical.retrieval.ingest_mode);
  check("retrieval.ddsa_enabled", resolved.ddsa_enabled, canonical.retrieval.ddsa_enabled);
  check("retrieval.llm_recall", resolved.llm_recall, canonical.retrieval.llm_recall);
  check("models.embed_model", resolved.embed_model, canonical.models.embed_model);

  return deviations;
}

// ---------------------------------------------------------------------------
// Enforce: throw on drift unless --allow-drift passed
// ---------------------------------------------------------------------------

export function requireNoDrift(
  deviations: string[],
  allowDrift: boolean
): void {
  if (deviations.length === 0) return;
  const msg = [
    `Config deviates from canonical.json (${deviations.length} knob(s)):`,
    ...deviations.map((d) => `  - ${d}`),
    "",
    "Pass --allow-drift to proceed anyway (results will NOT be comparable to baseline).",
  ].join("\n");
  if (!allowDrift) {
    throw new Error(msg);
  }
  process.stderr.write(`[WARN] ${msg}\n`);
}
