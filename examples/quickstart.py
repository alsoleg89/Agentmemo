"""ai-knot quickstart — minimal working example covering v0.5.0 features."""

import shutil

from ai_knot import KnowledgeBase, MemoryType

# ── 1. Add facts one at a time ────────────────────────────────────────────────
# stability_hours=48 (default): decay visible within a day.
# Pass stability_hours=336 to restore the slower v0.4 preset.
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
    prefix = "[!]" if fact.low_confidence else "   "
    print(f"  {prefix} [{score:.2f}] [{fact.type.value}] {fact.content}")

print()

# Keep only highly confident results.
relevant = [fact for fact, score in scored if score >= 0.3]
print(f"  Facts above 0.3 threshold: {len(relevant)}")

print()

# ── 5. Verbatim extraction mode (v0.5.0) ─────────────────────────────────────
# Use extraction_detail="verbatim" when exact numbers and constraints matter.
# The LLM preserves specific values instead of paraphrasing.
#
#   # Compact (default): "использовать подзаголовки"
#   facts = kb.learn(tov_turns, extraction_detail="compact")
#
#   # Verbatim: "Telegram: посты до 4000 знаков, подзаголовки H2/H3"
#   facts = kb.learn(tov_turns, extraction_detail="verbatim")

# ── 6. Faithfulness filter (v0.5.0) ──────────────────────────────────────────
# Flags facts whose key words don't appear in the source turns.
# Useful to surface potential LLM hallucinations.
#
#   facts = kb.learn(turns, faithfulness_filter=True)
#   confident = [f for f in facts if not f.low_confidence]
#   uncertain  = [f for f in facts if f.low_confidence]

# ── 7. Provider config at init — set credentials once (v0.4.0) ───────────────
# In production you'd do this instead of passing api_key= on every learn() call:
#
#   kb_prod = KnowledgeBase(
#       agent_id="assistant",
#       provider="openai",
#       api_key="sk-...",       # or reads OPENAI_API_KEY from env
#       stability_hours=48,     # default: decay visible within a day
#   )
#   kb_prod.learn(turns_a)                             # no credentials needed
#   kb_prod.learn(turns_b, extraction_detail="verbatim")  # preserve exact values
#
# Supported providers: openai, anthropic, gigachat, yandex, qwen, openai-compat

# ── 8. Async API — non-blocking for FastAPI / asyncio (v0.4.0) ───────────────
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
#       await kb.alearn(turns, extraction_detail="verbatim")
#       return await kb.arecall("current topic")

# ── 9. Stats and decay ────────────────────────────────────────────────────────
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
