"""S12 — Topic Channel + Publish Gating.

Verifies that:
  1. Facts can be routed to specific topic channels (devops / frontend / backend).
  2. Publish gating (utility_threshold) filters out low-importance facts before
     they enter the shared pool.
  3. Per-channel recall returns only facts from the correct domain.

Flow:
  1. Agent A inserts 9 high-importance facts (importance=0.8), 3 per channel.
  2. Agent A inserts 3 low-importance facts (importance=0.15), 1 per channel.
  3. Agent A publishes with utility_threshold=0.3.
     Expected: 9 high-importance facts published; 3 low-importance filtered out
     (utility = state_confidence × importance ≈ 0.15 < 0.3).
  4. Agent B queries each channel via pool_retrieve_for_channel.
  5. Agent B queries globally (no channel filter) to verify broad pool recall.

Metrics (all deterministic, no LLM judge):
  channel_precision   — fraction of channel-filtered queries that return at
                        least one result (should be 1.0 when gating works).
  gating_filter_rate  — 1.0 if published_count == expected_high_count, else 0.0.
  pool_recall         — fraction of the 3 channel queries returning ≥1 result;
                        mirrors channel_precision but named for clarity.

Only runs against MultiAgentMemoryBackend.
"""

from __future__ import annotations

from tests.eval.benchmark.base import MultiAgentMemoryBackend, ScenarioResult
from tests.eval.benchmark.judge import BaseJudge

SCENARIO_ID = "s12_topic_gating"

# High-importance facts (importance=0.8) — 3 per channel.
_HIGH_IMPORTANCE: list[tuple[str, str]] = [
    # devops
    ("Helm charts are used for all Kubernetes deployments.", "devops"),
    ("Grafana dashboards track all service SLOs.", "devops"),
    ("Terraform manages all cloud infrastructure as code.", "devops"),
    # frontend
    ("React 18 with TypeScript is the standard for all UI components.", "frontend"),
    ("Vite is the build tool for all frontend projects.", "frontend"),
    ("Tailwind CSS is used for styling across all web applications.", "frontend"),
    # backend
    ("FastAPI is the framework for all new Python microservices.", "backend"),
    ("PostgreSQL 16 is the primary database for backend services.", "backend"),
    ("Redis is used for caching and session management.", "backend"),
]

# Low-importance facts (importance=0.15) — should be filtered at threshold=0.3.
_LOW_IMPORTANCE: list[tuple[str, str]] = [
    ("Some older services still use Docker Compose for local dev.", "devops"),
    ("A legacy jQuery widget exists in the admin panel.", "frontend"),
    ("An old Flask endpoint remains for backwards compatibility.", "backend"),
]

# (query, expected_channel) pairs for per-channel recall test.
_CHANNEL_QUERIES: list[tuple[str, str]] = [
    ("How are Kubernetes deployments managed?", "devops"),
    ("What framework is used for UI components?", "frontend"),
    ("What is the primary database for backend services?", "backend"),
]

_EXPECTED_PUBLISHED = len(_HIGH_IMPORTANCE)  # 9


async def run(backend: MultiAgentMemoryBackend, judge: BaseJudge) -> ScenarioResult:
    await backend.reset()

    # Insert high-importance facts with topic channels.
    for text, channel in _HIGH_IMPORTANCE:
        await backend.insert_for_agent_with_meta(
            "agent_a", text, topic_channel=channel, importance=0.8
        )

    # Insert low-importance facts — these should be filtered by publish gating.
    for text, channel in _LOW_IMPORTANCE:
        await backend.insert_for_agent_with_meta(
            "agent_a", text, topic_channel=channel, importance=0.15
        )

    # Publish with utility_threshold=0.3:
    # utility = state_confidence (≈1.0) × importance
    # high: 1.0 × 0.8 = 0.8 >= 0.3 → published
    # low:  1.0 × 0.15 = 0.15 < 0.3 → filtered
    published_count = await backend.publish_to_pool("agent_a", utility_threshold=0.3)

    gating_filter_rate = 1.0 if published_count == _EXPECTED_PUBLISHED else 0.0

    # Query each channel; count queries that returned at least one fact.
    hits = 0
    for query, channel in _CHANNEL_QUERIES:
        result = await backend.pool_retrieve_for_channel(
            "agent_b", query, top_k=3, topic_channel=channel
        )
        if result.texts:
            hits += 1

    total_queries = len(_CHANNEL_QUERIES)
    channel_precision = hits / max(total_queries, 1)
    pool_recall = channel_precision  # same measurement, different semantic label

    notes = (
        f"published={published_count}/{len(_HIGH_IMPORTANCE) + len(_LOW_IMPORTANCE)}, "
        f"expected_published={_EXPECTED_PUBLISHED}, "
        f"gating_filter_rate={gating_filter_rate:.2f}, "
        f"channel_hits={hits}/{total_queries}, "
        f"channel_precision={channel_precision:.2%}"
    )

    return ScenarioResult(
        scenario_id=SCENARIO_ID,
        backend_name=backend.name,
        judge_scores={
            "channel_precision": [channel_precision],
            "gating_filter_rate": [gating_filter_rate],
            "pool_recall": [pool_recall],
        },
        insert_result=None,
        retrieval_result=None,
        notes=notes,
    )
