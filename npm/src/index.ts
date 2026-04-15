import { McpClient } from "./client.js";
import type {
  AddOptions,
  Fact,
  IngestEpisodeOptions,
  IngestEpisodeResult,
  KnowledgeBaseOptions,
  LearnMessage,
  LearnResult,
  QueryAnswer,
  QueryOptions,
  RecallOptions,
  Stats,
} from "./types.js";

export type {
  AddOptions,
  Fact,
  IngestEpisodeOptions,
  IngestEpisodeResult,
  KnowledgeBaseOptions,
  LearnMessage,
  LearnResult,
  MemoryType,
  QueryAnswer,
  QueryOptions,
  RecallOptions,
  Stats,
} from "./types.js";

/**
 * TypeScript client for ai_knot. Spawns the ai-knot-mcp subprocess on
 * the first method call and communicates via JSON-RPC 2.0 over stdio.
 *
 * @example
 * ```typescript
 * import { KnowledgeBase } from 'ai-knot';
 *
 * const kb = new KnowledgeBase({ agentId: 'my-agent', storage: 'sqlite', dbPath: '/data/mem.db' });
 * await kb.add('User prefers TypeScript');
 * const ctx = await kb.recall('what language?');
 * console.log(ctx);
 * await kb.close();
 * ```
 */
export class KnowledgeBase {
  private readonly client: McpClient;

  constructor(options: KnowledgeBaseOptions = {}) {
    const env: Record<string, string> = { ...options.env };
    if (options.agentId !== undefined) env["AI_KNOT_AGENT_ID"] = options.agentId;
    if (options.storage !== undefined) env["AI_KNOT_STORAGE"] = options.storage;
    if (options.dataDir !== undefined) env["AI_KNOT_DATA_DIR"] = options.dataDir;
    if (options.dbPath !== undefined) env["AI_KNOT_DB_PATH"] = options.dbPath;
    this.client = new McpClient({ command: options.command, env });
  }

  /**
   * Add a fact to the knowledge base.
   * Returns the created Fact with its assigned ID.
   */
  async add(content: string, options: AddOptions = {}): Promise<Fact> {
    const args: Record<string, unknown> = { content };
    if (options.type !== undefined) args["type"] = options.type;
    if (options.importance !== undefined) args["importance"] = options.importance;
    // tags not yet exposed by mcp_server.py tool signature — pass through if present
    const text = await this.client.call("add", args);
    // Response: "Added fact [<id>]: <content>"
    const match = /\[([a-f0-9]{8})\]/.exec(text);
    const id = match?.[1] ?? "";
    const facts = await this.listFacts();
    const fact = facts.find((f) => f.id === id);
    if (fact !== undefined) return fact;
    // Fallback: construct a minimal Fact from the response text
    return {
      id,
      content,
      type: (options.type ?? "semantic") as Fact["type"],
      importance: options.importance ?? 0.8,
      retention_score: 1.0,
      access_count: 0,
      tags: options.tags ?? [],
      created_at: new Date().toISOString(),
      last_accessed: new Date().toISOString(),
    };
  }

  /**
   * Recall relevant facts for a query. Returns a formatted string ready to
   * inject into a prompt, or "No relevant facts found." if the KB is empty.
   */
  async recall(query: string, options: RecallOptions = {}): Promise<string> {
    const args: Record<string, unknown> = { query };
    if (options.topK !== undefined) args["top_k"] = options.topK;
    return this.client.call("recall", args);
  }

  /**
   * Extract and store knowledge from a conversation using an LLM.
   * Requires AI_KNOT_PROVIDER and AI_KNOT_API_KEY env vars (or provider
   * configured at KnowledgeBase construction via the `env` option).
   */
  async learn(messages: LearnMessage[]): Promise<LearnResult> {
    const text = await this.client.call("learn", { messages });
    return JSON.parse(text) as LearnResult;
  }

  /**
   * Remove a fact by its 8-character hex ID.
   */
  async forget(factId: string): Promise<void> {
    await this.client.call("forget", { fact_id: factId });
  }

  /**
   * List all stored facts as structured objects.
   */
  async listFacts(): Promise<Fact[]> {
    const text = await this.client.call("list_facts", {});
    if (text === "No facts stored.") return [];
    return JSON.parse(text) as Fact[];
  }

  /**
   * Return statistics about the knowledge base.
   */
  async stats(): Promise<Stats> {
    const text = await this.client.call("stats", {});
    return JSON.parse(text) as Stats;
  }

  /**
   * Save the current knowledge base state as a named snapshot.
   * Throws if the storage backend does not support snapshots.
   */
  async snapshot(name: string): Promise<void> {
    const text = await this.client.call("snapshot", { name });
    if (text.toLowerCase().includes("not supported")) {
      throw new Error(text);
    }
  }

  /**
   * Restore the knowledge base from a named snapshot.
   * Throws if the snapshot does not exist or backend does not support snapshots.
   */
  async restore(name: string): Promise<void> {
    const text = await this.client.call("restore", { name });
    if (text.toLowerCase().includes("not supported") || text.toLowerCase().includes("not found")) {
      throw new Error(text);
    }
  }

  /**
   * Ingest a single raw conversation turn into memory.
   *
   * Stores as RawEpisode and deterministically extracts AtomicClaims.
   * Does NOT call the LLM. Prefer this over ``add()`` for batch ingest
   * from raw conversation data.
   */
  async ingestEpisode(options: IngestEpisodeOptions): Promise<IngestEpisodeResult> {
    const args: Record<string, unknown> = {
      session_id: options.sessionId,
      turn_id: options.turnId,
      raw_text: options.rawText,
    };
    if (options.speaker !== undefined) args["speaker"] = options.speaker;
    if (options.observedAt !== undefined) args["observed_at"] = options.observedAt;
    if (options.sessionDate !== undefined) args["session_date"] = options.sessionDate;
    if (options.sourceMeta !== undefined) args["source_meta"] = options.sourceMeta;
    if (options.parentEpisodeId !== undefined) args["parent_episode_id"] = options.parentEpisodeId;
    if (options.materialize !== undefined) args["materialize"] = options.materialize;
    const text = await this.client.call("ingest_episode", args);
    return JSON.parse(text) as IngestEpisodeResult;
  }

  /**
   * Contract-first query over memory. Returns structured answer with trace.
   *
   * Uses the full pipeline: analyze_query → retrieve_bundles → expand_claims
   * → build_evidence_profile → choose_strategy → operator.
   *
   * The returned {@link QueryAnswer} includes:
   * - `text`: compact answer string (backward-compatible).
   * - `evidence_text`: formatted episode block (`[N] [YYYY-MM-DD] Speaker: …`)
   *   ready to inject into a downstream LLM prompt. Prefer this over `text`
   *   when grounded context matters.
   * - `items`: answer values with confidence and provenance.
   * - `trace`: full audit trail (strategy, evidence profile, latency).
   */
  async query(question: string, options: QueryOptions = {}): Promise<QueryAnswer> {
    const args: Record<string, unknown> = { question };
    if (options.topK !== undefined) args["top_k"] = options.topK;
    if (options.render !== undefined) args["render"] = options.render;
    const text = await this.client.call("query_json", args);
    return JSON.parse(text) as QueryAnswer;
  }

  /**
   * Gracefully shut down the ai-knot-mcp subprocess.
   * Call this when you are done using the KnowledgeBase.
   */
  async close(): Promise<void> {
    await this.client.close();
  }
}
