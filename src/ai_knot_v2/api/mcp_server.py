"""MCP server for ai-knot v2 — exposes MemoryAPI as MCP tools.

Run with::

    python -m ai_knot_v2.api.mcp_server

Configuration via environment variables:

- ``AIKNOT_V2_DB_PATH``   — SQLite file path (default: ".ai_knot_v2/memory.db")
- ``AIKNOT_V2_AGENT_ID``  — agent namespace (default: "agent-1")
- ``AIKNOT_V2_MAX_ATOMS`` — default recall budget (default: 100)

No LLM calls in this module.
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

from mcp.server.fastmcp import FastMCP

from ai_knot_v2.api.product import MemoryAPI
from ai_knot_v2.api.sdk import EpisodeIn, LearnRequest, RecallRequest


def _build_api() -> MemoryAPI:
    db_path = os.environ.get("AIKNOT_V2_DB_PATH", ".ai_knot_v2/memory.db")
    agent_id = os.environ.get("AIKNOT_V2_AGENT_ID", "agent-1")
    if db_path != ":memory:":
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return MemoryAPI(db_path=db_path, agent_id=agent_id)


_api = _build_api()
_default_max_atoms = int(os.environ.get("AIKNOT_V2_MAX_ATOMS", "100"))

mcp = FastMCP("ai-knot-v2")


@mcp.tool()
def learn(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Ingest conversation episodes into memory.

    Each episode dict: {text, speaker?, session_id?, agent_id?, user_id?, timestamp?}
    Returns: {episode_ids, atom_ids, skipped_duplicate, skipped_dominated}
    """
    parsed = [EpisodeIn(**ep) for ep in episodes]
    resp = _api.learn(LearnRequest(episodes=parsed))
    return resp.model_dump()


@mcp.tool()
def recall(query: str, max_atoms: int = 0) -> dict[str, Any]:
    """Retrieve relevant memory atoms for a natural-language query.

    Returns: {query, atoms: [...], evidence_pack_id, intervention_variable}
    Each atom: {atom_id, predicate, subject, object_value, polarity, risk_class,
                risk_severity, credence, valid_from, valid_until, entity_orbit_id,
                synthesis_method}
    """
    budget = max_atoms if max_atoms > 0 else _default_max_atoms
    resp = _api.recall(RecallRequest(query=query, max_atoms=budget))
    return resp.model_dump()


@mcp.tool()
def explain(atom_id: str) -> dict[str, Any]:
    """Return provenance for a specific memory atom.

    Returns: {atom_id, predicate, subject, object_value, evidence_episodes,
              risk_class, synthesis_method}
    """
    resp = _api.explain(atom_id)
    return resp.model_dump()


@mcp.tool()
def trace(atom_id: str) -> dict[str, Any]:
    """Return full audit trail for a memory atom.

    Returns: {atom_id, events: [{event_id, operation, atom_id, agent_id, timestamp, details}]}
    """
    resp = _api.trace(atom_id)
    return resp.model_dump()


@mcp.tool()
def inspect_memory(
    risk_class: str = "",
    predicate: str = "",
    entity_orbit_id: str = "",
) -> dict[str, Any]:
    """List atoms in memory, optionally filtered.

    Returns: {atoms: [...], total}
    """
    filters: dict[str, str] = {}
    if risk_class:
        filters["risk_class"] = risk_class
    if predicate:
        filters["predicate"] = predicate
    if entity_orbit_id:
        filters["entity_orbit_id"] = entity_orbit_id
    resp = _api.inspect_memory(filters=filters or None)
    return resp.model_dump()


@mcp.tool()
def health() -> dict[str, Any]:
    """Return server health and memory stats."""
    atoms = _api.inspect_memory()
    return {"status": "ok", "total_atoms": atoms.total}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
