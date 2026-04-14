export type MemoryType = "semantic" | "procedural" | "episodic";

export interface Fact {
  id: string;
  content: string;
  type: MemoryType;
  importance: number;
  retention_score: number;
  access_count: number;
  tags: string[];
  created_at: string;
  last_accessed: string;
}

export interface Stats {
  total_facts: number;
  by_type: Record<string, number>;
  avg_importance: number;
  avg_retention: number;
}

export interface KnowledgeBaseOptions {
  /** Agent namespace. Default: "default". */
  agentId?: string;
  /** Storage backend. Default: "yaml". */
  storage?: "yaml" | "sqlite";
  /** Base directory for YAML/SQLite storage. Use an absolute path. */
  dataDir?: string;
  /** Full path to SQLite database file. Overrides dataDir for sqlite. */
  dbPath?: string;
  /** Path to ai-knot-mcp binary. Default: "ai-knot-mcp". */
  command?: string;
  /** Extra environment variables passed to the ai-knot-mcp subprocess. */
  env?: Record<string, string>;
}

export interface AddOptions {
  type?: MemoryType;
  importance?: number;
  tags?: string[];
}

export interface LearnMessage {
  role: "user" | "assistant";
  content: string;
}

export interface LearnResult {
  stored: number;
  ids: string[];
}

export interface RecallOptions {
  topK?: number;
}

// ---- New-gen Track A types --------------------------------------------------

export interface IngestEpisodeOptions {
  /** Session identifier (groups turns into conversations). */
  sessionId: string;
  /** Unique turn identifier within the session. */
  turnId: string;
  /** Raw conversation text for this turn. */
  rawText: string;
  /** Speaker role. Default: "user". */
  speaker?: string;
  /** ISO datetime string (defaults to now). */
  observedAt?: string;
  /** Optional ISO date for session-level temporal anchor. */
  sessionDate?: string;
  /** Optional metadata. */
  sourceMeta?: Record<string, unknown>;
  /** Optional parent episode ID. */
  parentEpisodeId?: string;
  /** Extract AtomicClaims immediately. Default: true. */
  materialize?: boolean;
}

export interface IngestEpisodeResult {
  episode_id: string;
  session_id: string;
}

export interface AnswerItem {
  value: string;
  confidence: number;
  source_claim_ids: string[];
  source_episode_ids: string[];
}

export interface QueryOptions {
  /** Maximum bundles to retrieve. Default: 60. */
  topK?: number;
  /** "structured" or "narrative". Default: "structured". */
  render?: "structured" | "narrative";
}

export interface QueryAnswer {
  text: string;
  items: AnswerItem[];
  confidence: number;
  trace: Record<string, unknown>;
}

// ---- Internal JSON-RPC 2.0 types ----------------------------------------

export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id?: number;
  method: string;
  params?: unknown;
}

export interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: number;
  result?: {
    content?: Array<{ type: string; text: string }>;
    [key: string]: unknown;
  };
  error?: { code: number; message: string };
}
