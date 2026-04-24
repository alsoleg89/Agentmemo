"""ai-knot v2 CLI entry point.

Commands: learn | recall | explain | trace | inspect-memory
"""

from __future__ import annotations

import json
import os
import sys

from ai_knot_v2.api.product import MemoryAPI
from ai_knot_v2.api.sdk import EpisodeIn, LearnRequest, RecallRequest

_DEFAULT_DB = os.environ.get("AI_KNOT_V2_DB", ":memory:")
_DEFAULT_AGENT = os.environ.get("AI_KNOT_V2_AGENT", "agent-1")


def _get_api() -> MemoryAPI:
    return MemoryAPI(db_path=_DEFAULT_DB, agent_id=_DEFAULT_AGENT)


def _print_json(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_learn(args: list[str]) -> int:
    """learn <text> [<text> ...]  — ingest one or more episode texts."""
    if not args:
        print("Usage: ai-knot-v2 learn <text> [<text> ...]", file=sys.stderr)
        return 1
    api = _get_api()
    episodes = [EpisodeIn(text=t) for t in args]
    result = api.learn(LearnRequest(episodes=episodes))
    _print_json(result.model_dump())
    return 0


def cmd_recall(args: list[str]) -> int:
    """recall <query>  — retrieve atoms relevant to query."""
    if not args:
        print("Usage: ai-knot-v2 recall <query>", file=sys.stderr)
        return 1
    api = _get_api()
    result = api.recall(RecallRequest(query=" ".join(args)))
    _print_json(result.model_dump())
    return 0


def cmd_explain(args: list[str]) -> int:
    """explain <atom_id>  — explain provenance of an atom."""
    if not args:
        print("Usage: ai-knot-v2 explain <atom_id>", file=sys.stderr)
        return 1
    api = _get_api()
    try:
        result = api.explain(args[0])
        _print_json(result.model_dump())
        return 0
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_trace(args: list[str]) -> int:
    """trace <atom_id>  — show audit trail for an atom."""
    if not args:
        print("Usage: ai-knot-v2 trace <atom_id>", file=sys.stderr)
        return 1
    api = _get_api()
    result = api.trace(args[0])
    _print_json(result.model_dump())
    return 0


def cmd_inspect(args: list[str]) -> int:
    """inspect-memory [--risk-class <cls>] [--predicate <pred>]  — list atoms."""
    filters: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i] == "--risk-class" and i + 1 < len(args):
            filters["risk_class"] = args[i + 1]
            i += 2
        elif args[i] == "--predicate" and i + 1 < len(args):
            filters["predicate"] = args[i + 1]
            i += 2
        else:
            i += 1
    api = _get_api()
    result = api.inspect_memory(filters or None)
    _print_json(result.model_dump())
    return 0


_COMMANDS = {
    "learn": cmd_learn,
    "recall": cmd_recall,
    "explain": cmd_explain,
    "trace": cmd_trace,
    "inspect-memory": cmd_inspect,
}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: ai-knot-v2 <command> [args]")
        print("Commands:", ", ".join(_COMMANDS))
        return 0

    cmd = args[0]
    handler = _COMMANDS.get(cmd)
    if handler is None:
        print(f"Unknown command: {cmd!r}. Commands: {', '.join(_COMMANDS)}", file=sys.stderr)
        return 1

    return handler(args[1:])


if __name__ == "__main__":
    sys.exit(main())
