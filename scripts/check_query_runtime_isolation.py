"""CI gate: query runtime modules must not import from storage/ or kb privates.

Checks that the following modules are storage-agnostic:
  - src/ai_knot/query_runtime.py
  - src/ai_knot/query_operators.py
  - src/ai_knot/query_contract.py

None of these may:
  1. Import anything from ai_knot.storage.*
  2. Reference ``kb._retriever``, ``kb._storage``, ``kb._bundle_store``,
     ``kb._claim_store``, or any other ``kb._*`` private attribute.

The only permitted retrieval path from runtime is ``ai_knot.support_retrieval``.

Exit codes:
  0 — clean
  1 — violations found
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_CHECKED_FILES = [
    Path("src/ai_knot/query_runtime.py"),
    Path("src/ai_knot/query_operators.py"),
    Path("src/ai_knot/query_contract.py"),
]

# AST-level import violations.
_FORBIDDEN_IMPORT_PREFIXES = (
    "ai_knot.storage",
    "ai_knot.knowledge",
)

# Regex-level attribute violations (covers getattr-style too).
_FORBIDDEN_ATTR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bkb\._\w+"),
    re.compile(r"\bself\._storage\b"),
    re.compile(r"\bself\._retriever\b"),
    re.compile(r"\bself\._bundle_store\b"),
    re.compile(r"\bself\._claim_store\b"),
]


def _check_imports(path: Path, tree: ast.Module) -> list[str]:
    errors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in _FORBIDDEN_IMPORT_PREFIXES:
                    if alias.name.startswith(prefix):
                        errors.append(
                            f"{path}:{node.lineno}: forbidden import '{alias.name}'"
                        )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for prefix in _FORBIDDEN_IMPORT_PREFIXES:
                if module.startswith(prefix):
                    errors.append(
                        f"{path}:{node.lineno}: forbidden import from '{module}'"
                    )
    return errors


def _check_attrs(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return errors

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pat in _FORBIDDEN_ATTR_PATTERNS:
            if pat.search(line):
                errors.append(f"{path}:{lineno}: forbidden storage access: {line.rstrip()}")
                break
    return errors


def main() -> int:
    all_errors: list[str] = []

    for path in _CHECKED_FILES:
        if not path.exists():
            # File not yet created — skip (module may not exist yet in early phases).
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            all_errors.append(f"{path}: syntax error — {exc}")
            continue

        all_errors.extend(_check_imports(path, tree))
        all_errors.extend(_check_attrs(path))

    if not all_errors:
        print("check_query_runtime_isolation: OK")
        return 0

    print("check_query_runtime_isolation: FAIL", file=sys.stderr)
    for err in all_errors:
        print(f"  {err}", file=sys.stderr)
    print(
        "\nquery_runtime / query_operators / query_contract must not import from\n"
        "ai_knot.storage.* or access kb._ private attributes.\n"
        "All retrieval goes through ai_knot.support_retrieval.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
