"""ai-knot quickstart — minimal working example."""

import shutil

from ai_knot import KnowledgeBase, MemoryType

# ── 1. Add facts one at a time ────────────────────────────────────────────────
kb = KnowledgeBase(agent_id="demo")

kb.add("User is a senior backend developer at Acme Corp", importance=0.95)
kb.add("User prefers Python, dislikes async code", type=MemoryType.PROCEDURAL, importance=0.85)
kb.add("User deploys everything in Docker", importance=0.80)
kb.add("Deploy failed last Tuesday", type=MemoryType.EPISODIC, importance=0.40)

# ── 2. Batch-insert facts without an LLM call (v0.4.0) ────────────────────────
kb.add_many(
    [
        "User works with FastAPI and PostgreSQL",
        {"content": "Always write tests with pytest", "type": "procedural", "importance": 0.9},
        {"content": "Team uses GitHub Actions for CI", "type": "semantic", "importance": 0.7},
    ]
)

# ── 3. Recall — plain string for prompt injection ─────────────────────────────
print("=== Query: 'how should I write this deployment script?' ===")
context = kb.recall("how should I write this deployment script?")
print(context)

print()

print("=== Query: 'where does the user work?' ===")
context = kb.recall("where does the user work?")
print(context)

print()

# ── 4. Recall with relevance scores (v0.4.0) ─────────────────────────────────
print("=== Scored retrieval: 'Docker deployment' ===")
scored = kb.recall_facts_with_scores("Docker deployment", top_k=3)
for fact, score in scored:
    print(f"  [{score:.2f}] [{fact.type.value}] {fact.content}")

print()

# Keep only highly confident results.
relevant = [fact for fact, score in scored if score >= 0.3]
print(f"  Facts above 0.3 threshold: {len(relevant)}")

print()

# ── 5. Provider config at init — set credentials once (v0.4.0) ───────────────
# In production you'd do this instead of passing api_key= on every learn() call:
#
#   kb_prod = KnowledgeBase(
#       agent_id="assistant",
#       provider="openai",
#       api_key="sk-...",       # or reads OPENAI_API_KEY from env
#   )
#   kb_prod.learn(turns_a)     # no credentials needed per call
#   kb_prod.learn(turns_b)
#
# Supported providers: openai, anthropic, gigachat, yandex, qwen, openai-compat

# ── 6. Async API — non-blocking for FastAPI / asyncio (v0.4.0) ───────────────
# All blocking operations have async variants:
#
#   facts = await kb.alearn(turns, provider="openai", api_key="sk-...")
#   context = await kb.arecall("query")
#   results = await kb.arecall_facts("query")
#
# Example FastAPI handler:
#
#   @app.post("/chat")
#   async def chat(turns: list[ConversationTurn]) -> str:
#       await kb.alearn(turns)
#       return await kb.arecall("current topic")

# ── 7. Stats and decay ────────────────────────────────────────────────────────
stats = kb.stats()
print("=== Stats ===")
print(f"Total facts: {stats['total_facts']}")
print(f"By type: {stats['by_type']}")
print(f"Avg importance: {stats['avg_importance']:.2f}")
print(f"Avg retention: {stats['avg_retention']:.2f}")

kb.decay()

# ── Cleanup ───────────────────────────────────────────────────────────────────
shutil.rmtree(".ai_knot", ignore_errors=True)
print("\nDemo complete. Cleaned up .ai_knot/")
