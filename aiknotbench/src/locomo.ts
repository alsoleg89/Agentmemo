import { createWriteStream, existsSync, readFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";

const LOCOMO_URL =
  "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json";

const DATA_DIR = resolve(
  fileURLToPath(import.meta.url),
  "..",
  "..",
  "data"
);

const DEFAULT_CACHE_PATH = resolve(DATA_DIR, "locomo10.json");

// ---- Public types -----------------------------------------------------------

export interface QAPair {
  idx: number;
  question: string;
  answer: string;
  category: number;
}

export interface Session {
  key: string;        // "session_1"
  date?: string;      // "8 May, 2023"
  turns: string[];    // speaker-prefixed turns within this session
  observedFacts?: string[]; // optional LoCoMo observation/caption/summary facts
  text: string;       // concatenated session text (date prefix + turns)
}

export interface Conversation {
  idx: number;
  turns: string[];    // flat (backward compat)
  sessions: Session[];
  qa: QAPair[];
}

export interface LoadOptions {
  locomoFile?: string;
  limit?: number;
}

// ---- Internal LoCoMo JSON schema -------------------------------------------

interface RawTurn {
  text?: string;
  speaker?: string;
  dia_id?: string;
  blip_caption?: string;
  query?: string;
}

interface RawQA {
  question?: string;
  answer?: string;
  category?: number;
  adversarial_answer?: string;
}

interface RawEventSummary {
  date?: string;
  [key: string]: unknown;
}

type RawObservationValue = Record<string, unknown>;

interface RawConversation {
  conversation?: Record<string, unknown>;
  event_summary?: Record<string, RawEventSummary>;
  observation?: Record<string, RawObservationValue>;
  session_summary?: Record<string, string>;
  qa?: RawQA[];
  [key: string]: unknown;
}

// ---- Dataset loading --------------------------------------------------------

export async function loadDataset(opts: LoadOptions = {}): Promise<Conversation[]> {
  const jsonPath = opts.locomoFile
    ?? process.env["LOCOMO_FILE"]
    ?? DEFAULT_CACHE_PATH;

  if (!existsSync(jsonPath)) {
    await downloadLocomo(DEFAULT_CACHE_PATH);
  }

  const raw: RawConversation[] = JSON.parse(
    readFileSync(jsonPath === DEFAULT_CACHE_PATH ? DEFAULT_CACHE_PATH : jsonPath, "utf-8")
  ) as RawConversation[];

  const slice = opts.limit !== undefined ? raw.slice(0, opts.limit) : raw;
  return slice.map((conv, idx) => normalizeConversation(conv, idx));
}

async function downloadLocomo(dest: string): Promise<void> {
  console.log(`Downloading LoCoMo10 dataset from GitHub…`);
  mkdirSync(dirname(dest), { recursive: true });

  const res = await fetch(LOCOMO_URL);
  if (!res.ok) {
    throw new Error(`Failed to download locomo10.json: HTTP ${res.status}`);
  }
  if (!res.body) throw new Error("Empty response body from locomo download");

  await pipeline(
    Readable.fromWeb(res.body as Parameters<typeof Readable.fromWeb>[0]),
    createWriteStream(dest)
  );
  console.log(`Cached to ${dest}`);
}

// ---- Schema normalisation ---------------------------------------------------

const SESSION_RE = /^session_(\d+)$/;

export function normalizeConversation(raw: RawConversation, idx: number): Conversation {
  const conv = (raw["conversation"] ?? raw) as Record<string, unknown>;
  const eventSummary = raw["event_summary"] ?? {};
  const observations = raw["observation"] ?? {};
  const sessionSummary = raw["session_summary"] ?? {};

  // Collect session_N keys, sort by N
  const numbered: Array<[number, string]> = [];
  for (const key of Object.keys(conv)) {
    const m = SESSION_RE.exec(key);
    if (m) numbered.push([parseInt(m[1]!, 10), key]);
  }
  numbered.sort((a, b) => a[0] - b[0]);

  const allTurns: string[] = [];
  const sessions: Session[] = [];

  for (const [num, key] of numbered) {
    const rawSession = conv[key];
    if (!Array.isArray(rawSession)) continue;

    const sessionTurns: string[] = [];
    const observedFacts: string[] = [];
    for (const turn of rawSession as RawTurn[]) {
      if (turn.text) {
        const speaker = turn.speaker ?? "speaker";
        const line = `${speaker}: ${turn.text}`;
        sessionTurns.push(line);
        allTurns.push(line);
      }

      const imageBits: string[] = [];
      if (turn.blip_caption) imageBits.push(`caption: ${turn.blip_caption}`);
      if (turn.query) imageBits.push(`image_query: ${turn.query}`);
      if (imageBits.length > 0) {
        const speaker = turn.speaker ?? "speaker";
        const diaId = turn.dia_id ? ` dia_id=${turn.dia_id}` : "";
        const text = turn.text ? ` related_turn="${speaker}: ${turn.text}"` : "";
        observedFacts.push(
          `[source=image_meta session=${key}${diaId}] ${speaker} shared image metadata: ${imageBits.join("; ")}.${text}`
        );
      }
    }

    if (sessionTurns.length === 0) continue;

    // Extract date from event_summary.events_session_N
    const evKey = `events_session_${num}`;
    const ev = (eventSummary as Record<string, RawEventSummary>)[evKey];
    const date = ev?.date;

    const obsKey = `session_${num}_observation`;
    const obs = observations[obsKey];
    if (obs && typeof obs === "object") {
      for (const [speaker, facts] of Object.entries(obs)) {
        if (!Array.isArray(facts)) continue;
        for (const fact of facts) {
          if (!Array.isArray(fact) || fact.length < 2) continue;
          const statement = String(fact[0] ?? "").trim();
          if (!statement) continue;
          const evidence = Array.isArray(fact[1])
            ? fact[1].join(",")
            : String(fact[1] ?? "");
          observedFacts.push(
            `[source=observation session=${key} evidence=${evidence}] ${speaker}: ${statement}`
          );
        }
      }
    }

    const summaryKey = `session_${num}_summary`;
    const summary = sessionSummary[summaryKey];
    if (summary && typeof summary === "string") {
      observedFacts.push(`[source=session_summary session=${key}] ${summary}`);
    }

    const datedObservedFacts = observedFacts.map((fact) =>
      date ? `[${date}] ${fact}` : fact
    );

    const textParts: string[] = [];
    if (date) textParts.push(`[${date}]`);
    textParts.push(sessionTurns.join("\n"));

    sessions.push({
      key,
      date,
      turns: sessionTurns,
      observedFacts: datedObservedFacts,
      text: textParts.join("\n"),
    });
  }

  const rawQA: RawQA[] = Array.isArray(raw["qa"]) ? (raw["qa"] as RawQA[]) : [];
  const qa: QAPair[] = rawQA
    .map((q, i): QAPair | null => {
      // Coerce to string — real LoCoMo answers can be numbers (years, counts, etc.)
      const question = q.question != null ? String(q.question).trim() : "";
      const category = q.category ?? 0;
      const raw_answer = category === 5
        ? (q.adversarial_answer ?? q.answer)
        : q.answer;
      const answer = raw_answer != null ? String(raw_answer).trim() : "";

      if (!question || !answer) return null;
      return { idx: i, question, answer, category };
    })
    .filter((q): q is QAPair => q !== null);

  return { idx, turns: allTurns, sessions, qa };
}

// ---- Filtering helpers (used by runner) ------------------------------------

export function filterQA(
  qa: QAPair[],
  types: number[] | undefined,
  sample: number | undefined
): QAPair[] {
  let filtered = types ? qa.filter((q) => types.includes(q.category)) : qa;
  if (sample !== undefined && filtered.length > sample) {
    filtered = filtered.slice(0, sample);
  }
  return filtered;
}
