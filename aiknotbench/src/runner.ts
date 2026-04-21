import { execSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { LanguageModelV1 } from "ai";

import { AiknotAdapter } from "./aiknot.js";
import type { IngestMode } from "./aiknot.js";
import {
  diffAgainstCanonical,
  hashCanonical,
  loadCanonical,
  requireNoDrift,
  resolveRunConfig,
} from "./config_snapshot.js";
import type { ResolvedRunConfig } from "./config_snapshot.js";
import { answerQuestion, judgeAnswer } from "./evaluator.js";
import type { Verdict, Usage } from "./evaluator.js";
import { filterQA, loadDataset } from "./locomo.js";
import type { LoadOptions } from "./locomo.js";

// ---- Paths ------------------------------------------------------------------

const RUNS_DIR = resolve(
  fileURLToPath(import.meta.url),
  "..",
  "..",
  "data",
  "runs"
);

function runDir(runId: string): string {
  return resolve(RUNS_DIR, runId);
}

function checkpointPath(runId: string): string {
  return resolve(runDir(runId), "checkpoint.json");
}

function reportPath(runId: string): string {
  return resolve(runDir(runId), "report.json");
}

function logPath(runId: string): string {
  return resolve(runDir(runId), "log.jsonl");
}

function dbPath(runId: string): string {
  return resolve(runDir(runId), "knot.db");
}

function runConfigPath(runId: string): string {
  return resolve(runDir(runId), "run_config.json");
}

// ---- Git + dataset helpers --------------------------------------------------

interface GitInfo {
  sha: string;
  dirty: boolean;
}

function getGitInfo(repoPath: string): GitInfo {
  try {
    const sha = execSync("git rev-parse HEAD", { cwd: repoPath, stdio: ["ignore", "pipe", "ignore"] })
      .toString().trim();
    const dirty = execSync("git status --porcelain", { cwd: repoPath, stdio: ["ignore", "pipe", "ignore"] })
      .toString().trim().length > 0;
    return { sha, dirty };
  } catch {
    return { sha: "unknown", dirty: false };
  }
}

function hashFileContents(filePath: string): string {
  try {
    const bytes = readFileSync(filePath);
    return createHash("sha256").update(bytes).digest("hex");
  } catch {
    return "unknown";
  }
}

// ---- RunConfig (written once, immutable per run) ----------------------------

interface RunConfig {
  runId: string;
  startedAt: string;
  git: {
    aiKnotSha: string;
    aiKnotDirty: boolean;
    aiknotbenchSha: string;
    aiknotbenchDirty: boolean;
  };
  config: {
    canonicalSha: string;
    deviations: string[];
    resolved: ResolvedRunConfig;
  };
  dataset: {
    path: string;
    sha256: string;
    convs: number[];
  };
}

function writeRunConfig(runId: string, rc: RunConfig): void {
  writeFileSync(runConfigPath(runId), JSON.stringify(rc, null, 2));
}

function loadRunConfig(runId: string): RunConfig | null {
  const p = runConfigPath(runId);
  if (!existsSync(p)) return null;
  return JSON.parse(readFileSync(p, "utf-8")) as RunConfig;
}

// ---- Checkpoint schema ------------------------------------------------------

interface CheckpointResult {
  convIdx: number;
  qaIdx: number;
  category: number;
  verdict: Verdict;
}

interface Checkpoint {
  runId: string;
  /** @deprecated moved to run_config.json */
  judgeModel?: string;
  /** @deprecated moved to run_config.json */
  answerModel?: string;
  startedAt: string;
  updatedAt: string;
  ingested: number[];
  results: CheckpointResult[];
  /** @deprecated moved to run_config.json */
  ingestMode?: IngestMode;
}

function loadCheckpoint(runId: string): Checkpoint | null {
  const p = checkpointPath(runId);
  if (!existsSync(p)) return null;
  return JSON.parse(readFileSync(p, "utf-8")) as Checkpoint;
}

function saveCheckpoint(cp: Checkpoint): void {
  cp.updatedAt = new Date().toISOString();
  writeFileSync(checkpointPath(cp.runId), JSON.stringify(cp, null, 2));
}

// ---- Report schema ----------------------------------------------------------

interface TypeStat {
  total: number;
  correct: number;
  accuracy: number;
}

export interface Report {
  runId: string;
  judgeModel: string;
  answerModel: string;
  finishedAt: string;
  summary: TypeStat;           // cat1–4 only (excludes adversarial cat5)
  adversarial?: TypeStat;      // cat5 separate (inverse-signal)
  byType: Record<string, TypeStat>;
  categories1to4: TypeStat;
  git?: {
    aiKnotSha: string;
    aiKnotDirty: boolean;
    aiknotbenchSha: string;
    aiknotbenchDirty: boolean;
  };
  config?: {
    canonicalSha: string;
    deviations: string[];
    resolved: ResolvedRunConfig;
  };
  dataset?: {
    path: string;
    sha256: string;
    convs: number[];
  };
  timings?: {
    wallClockSec: number;
    tokensIn: number;
    tokensOut: number;
  };
}

export function computeReport(
  runId: string,
  judgeModel: string,
  answerModel: string,
  results: CheckpointResult[],
  extras?: {
    runConfig?: RunConfig | null;
    timings?: Report["timings"];
  }
): Report {
  const all = results;
  // Cat5 is adversarial ("Not mentioned" gold) — separate from primary summary
  const primary = all.filter((r) => r.category !== 5);
  const cat5 = all.filter((r) => r.category === 5);
  const correct = primary.filter((r) => r.verdict === "CORRECT").length;
  const summary: TypeStat = {
    total: primary.length,
    correct,
    accuracy: primary.length > 0 ? correct / primary.length : 0,
  };
  const adversarial: TypeStat | undefined = cat5.length > 0
    ? {
        total: cat5.length,
        correct: cat5.filter((r) => r.verdict === "CORRECT").length,
        accuracy: cat5.filter((r) => r.verdict === "CORRECT").length / cat5.length,
      }
    : undefined;

  const byType: Record<string, TypeStat> = {};
  for (const r of all) {
    const key = String(r.category);
    if (!byType[key]) byType[key] = { total: 0, correct: 0, accuracy: 0 };
    byType[key]!.total++;
    if (r.verdict === "CORRECT") byType[key]!.correct++;
  }
  for (const stat of Object.values(byType)) {
    stat.accuracy = stat.total > 0 ? stat.correct / stat.total : 0;
  }

  const cat14 = all.filter((r) => r.category >= 1 && r.category <= 4);
  const cat14correct = cat14.filter((r) => r.verdict === "CORRECT").length;
  const categories1to4: TypeStat = {
    total: cat14.length,
    correct: cat14correct,
    accuracy: cat14.length > 0 ? cat14correct / cat14.length : 0,
  };

  const rc = extras?.runConfig;
  return {
    runId,
    judgeModel,
    answerModel,
    finishedAt: new Date().toISOString(),
    summary,
    ...(adversarial !== undefined ? { adversarial } : {}),
    byType,
    categories1to4,
    ...(rc ? { git: rc.git, config: rc.config, dataset: rc.dataset } : {}),
    ...(extras?.timings ? { timings: extras.timings } : {}),
  };
}

// ---- Injectable evaluator (for testing) -------------------------------------

export interface EvaluatorFns {
  answerFn: (
    model: LanguageModelV1,
    context: string,
    question: string
  ) => Promise<{ text: string; usage: Usage }>;
  judgeFn: (
    model: LanguageModelV1,
    question: string,
    answer: string,
    gold: string
  ) => Promise<{ verdict: Verdict; usage: Usage }>;
  adapterFactory: (
    runDbPath: string,
    convIdx: number,
    command: string,
    env: Record<string, string>,
    topK: number,
    ingestMode: IngestMode
  ) => AiknotAdapterLike;
}

export interface AiknotAdapterLike {
  ingest(turns: string[], sessions?: import("./locomo.js").Session[], speakerA?: string): Promise<void>;
  recall(question: string): Promise<string>;
  close(): Promise<void>;
}

const defaultEvaluatorFns = (
  judgeModel: LanguageModelV1,
  answerModel: LanguageModelV1,
  command: string
): EvaluatorFns => ({
  answerFn: (_, ctx, q) => answerQuestion(answerModel, ctx, q),
  judgeFn: (_, question, answer, gold) =>
    judgeAnswer(judgeModel, question, answer, gold),
  adapterFactory: (dbPath, convIdx, _cmd, env, topK, ingestMode) =>
    new AiknotAdapter(dbPath, convIdx, command, env, topK, ingestMode),
});

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
  evidenceContainsGold: boolean;
  answerUsage: Usage;
  judgeUsage: Usage;
}

function appendLog(runId: string, entry: LogEntry): void {
  appendFileSync(logPath(runId), JSON.stringify(entry) + "\n", "utf-8");
}

// ---- RunOptions -------------------------------------------------------------

export interface RunOptions extends LoadOptions {
  runId: string;
  judgeModel: LanguageModelV1;
  answerModel: LanguageModelV1;
  judgeModelName: string;
  answerModelName: string;
  aiKnotCommand: string;
  aiKnotEnv?: Record<string, string>;
  topK?: number;
  maxTurns?: number;
  ingestMode?: IngestMode;
  types?: number[];
  convs?: number[];
  sample?: number;
  force?: boolean;
  allowDrift?: boolean;
  _evaluatorOverride?: Partial<EvaluatorFns>;
}

// ---- Main run logic ---------------------------------------------------------

export async function runBenchmark(opts: RunOptions): Promise<Report> {
  const {
    runId,
    judgeModel,
    answerModel,
    judgeModelName,
    answerModelName,
    aiKnotCommand,
    aiKnotEnv = {},
    topK = 5,
    maxTurns,
    ingestMode = "dated",
    types,
    convs,
    sample,
    force,
    allowDrift = false,
    _evaluatorOverride,
  } = opts;

  const dir = runDir(runId);

  if (force && existsSync(dir)) {
    rmSync(dir, { recursive: true, force: true });
  }

  mkdirSync(dir, { recursive: true });

  // Write run_config.json once on first start (never mutated on resume)
  const BENCH_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const AI_KNOT_ROOT = resolve(BENCH_ROOT, "..");
  if (!existsSync(runConfigPath(runId))) {
    const resolved = resolveRunConfig(
      { answerModel: answerModelName, judgeModel: judgeModelName, topK, ingestMode, convs, allowDrift },
      process.env as NodeJS.ProcessEnv
    );
    const deviations = diffAgainstCanonical(resolved);
    requireNoDrift(deviations, allowDrift);
    const canonical = loadCanonical();
    const aiKnotGit = getGitInfo(AI_KNOT_ROOT);
    const benchGit = getGitInfo(BENCH_ROOT);
    const rc: RunConfig = {
      runId,
      startedAt: new Date().toISOString(),
      git: {
        aiKnotSha: aiKnotGit.sha,
        aiKnotDirty: aiKnotGit.dirty,
        aiknotbenchSha: benchGit.sha,
        aiknotbenchDirty: benchGit.dirty,
      },
      config: {
        canonicalSha: hashCanonical(),
        deviations,
        resolved,
      },
      dataset: {
        path: canonical.dataset.path,
        sha256: hashFileContents(resolve(BENCH_ROOT, canonical.dataset.path)),
        convs: convs ?? canonical.dataset.convs_default,
      },
    };
    writeRunConfig(runId, rc);
  }

  // Load or create checkpoint
  let cp = loadCheckpoint(runId);
  if (!cp) {
    cp = {
      runId,
      startedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ingested: [],
      results: [],
    };
    saveCheckpoint(cp);
  }

  let dataset = await loadDataset({
    locomoFile: opts.locomoFile,
    limit: opts.limit,
  });
  if (convs && convs.length > 0) {
    const convSet = new Set(convs);
    dataset = dataset.filter((c) => convSet.has(c.idx));
  }

  const fns: EvaluatorFns = {
    ...defaultEvaluatorFns(judgeModel, answerModel, aiKnotCommand),
    ..._evaluatorOverride,
  };

  // Compute total work for progress display
  let totalWork = 0;
  for (const conv of dataset) {
    totalWork += filterQA(conv.qa, types, sample).length;
  }

  // Timing accumulators
  const wallStart = Date.now();
  let tokensIn = 0;
  let tokensOut = 0;

  const pad = String(dataset.length).length;
  console.log(
    `\nrun: ${runId}  convs: ${dataset.length}  ` +
    `judge: ${judgeModelName}  model: ${answerModelName}\n`
  );

  for (const conv of dataset) {
    const convLabel = String(conv.idx + 1).padStart(pad, "0");
    const filteredQA = filterQA(conv.qa, types, sample);
    const pending = filteredQA.filter(
      (qa) =>
        !cp!.results.some(
          (r) => r.convIdx === conv.idx && r.qaIdx === qa.idx
        )
    );

    if (pending.length === 0) {
      console.log(
        `  conv ${convLabel}/${dataset.length} — already complete, skipping`
      );
      continue;
    }

    const adapter = fns.adapterFactory(dbPath(runId), conv.idx, aiKnotCommand, aiKnotEnv, topK, ingestMode);

    try {
      if (!cp!.ingested.includes(conv.idx)) {
        process.stdout.write(
          `  conv ${convLabel}/${dataset.length} — ingesting ${conv.turns.length} turns… `
        );
        const turns = maxTurns !== undefined ? conv.turns.slice(0, maxTurns) : conv.turns;
        let sessions = conv.sessions;
        if (maxTurns !== undefined) {
          let remaining = maxTurns;
          sessions = [];
          for (const s of conv.sessions) {
            if (remaining <= 0) break;
            if (s.turns.length <= remaining) {
              sessions.push(s);
              remaining -= s.turns.length;
            } else {
              sessions.push({ ...s, turns: s.turns.slice(0, remaining) });
              remaining = 0;
            }
          }
        }
        await adapter.ingest(turns, sessions, conv.speakerA);
        cp!.ingested.push(conv.idx);
        saveCheckpoint(cp!);
        process.stdout.write("done\n");
      }

      for (const qa of pending) {
        const context = await adapter.recall(qa.question);
        const { text: answer, usage: answerUsage } = await fns.answerFn(answerModel, context, qa.question);
        const { verdict, usage: judgeUsage } = await fns.judgeFn(
          judgeModel,
          qa.question,
          answer,
          qa.answer
        );
        tokensIn += answerUsage.promptTokens + judgeUsage.promptTokens;
        tokensOut += answerUsage.completionTokens + judgeUsage.completionTokens;

        cp!.results.push({
          convIdx: conv.idx,
          qaIdx: qa.idx,
          category: qa.category,
          verdict,
        });
        saveCheckpoint(cp!);

        const goldLower = qa.answer.toLowerCase();
        const evidenceContainsGold = context.toLowerCase().includes(goldLower);

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
          evidenceContainsGold,
          answerUsage,
          judgeUsage,
        });

        const done = cp!.results.length;
        const icon = verdict === "CORRECT" ? "✓" : "✗";
        const q = qa.question.length > 55
          ? qa.question.slice(0, 55) + "…"
          : qa.question;
        console.log(
          `  [conv ${convLabel} qa ${String(done).padStart(String(totalWork).length)}/${totalWork}] ` +
          `${icon} ${verdict} (cat ${qa.category}) "${q}"`
        );
      }
    } finally {
      await adapter.close();
    }
  }

  // Write report
  const report = computeReport(
    runId,
    judgeModelName,
    answerModelName,
    cp.results,
    {
      runConfig: loadRunConfig(runId),
      timings: { wallClockSec: (Date.now() - wallStart) / 1000, tokensIn, tokensOut },
    }
  );
  writeFileSync(reportPath(runId), JSON.stringify(report, null, 2));

  // Print summary
  const acc = (report.categories1to4.accuracy * 100).toFixed(1);
  const acc14 = `${report.categories1to4.correct}/${report.categories1to4.total}`;
  console.log(`\n${"─".repeat(52)}`);
  console.log(
    `  cat 1–4 accuracy : ${acc}%  (${acc14})`
  );
  console.log(
    `  overall accuracy : ${(report.summary.accuracy * 100).toFixed(1)}%  ` +
    `(${report.summary.correct}/${report.summary.total})`
  );
  for (const [cat, stat] of Object.entries(report.byType).sort()) {
    const catNames: Record<string, string> = {
      "1": "single-hop",
      "2": "temporal",
      "3": "inference",
      "4": "open-domain",
      "5": "adversarial",
    };
    const label = catNames[cat] ?? `cat${cat}`;
    console.log(
      `  cat ${cat} (${label.padEnd(10)}) : ` +
      `${(stat.accuracy * 100).toFixed(1)}%  (${stat.correct}/${stat.total})`
    );
  }
  console.log(`${"─".repeat(52)}`);
  console.log(`  report: data/runs/${runId}/report.json\n`);

  return report;
}

// ---- List runs --------------------------------------------------------------

export interface RunSummary {
  runId: string;
  startedAt: string;
  finishedAt: string | null;
  total: number;
  accuracy: string | null;
}

export function listRuns(opts: { limit?: number } = {}): RunSummary[] {
  if (!existsSync(RUNS_DIR)) return [];

  const dirs = readdirSync(RUNS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  const summaries: RunSummary[] = [];

  for (const runId of dirs) {
    const cp = loadCheckpoint(runId);
    const rp = reportPath(runId);
    const report = existsSync(rp)
      ? (JSON.parse(readFileSync(rp, "utf-8")) as Report)
      : null;

    summaries.push({
      runId,
      startedAt: cp?.startedAt ?? "unknown",
      finishedAt: report?.finishedAt ?? null,
      total: cp?.results.length ?? 0,
      accuracy:
        report
          ? `${(report.categories1to4.accuracy * 100).toFixed(1)}%`
          : null,
    });
  }

  // Sort newest first
  summaries.sort((a, b) => b.startedAt.localeCompare(a.startedAt));

  return opts.limit !== undefined ? summaries.slice(0, opts.limit) : summaries;
}
