"""CI gate: runtime source must not contain benchmark-category branches.

Scans src/ai_knot/ (excluding test helpers) for any string that would indicate
the runtime is routing by benchmark category labels (Cat1/Cat2/Cat3/Cat4,
LoCoMo) rather than by geometric query features.

Exit codes:
  0 — clean
  1 — violations found (prints each hit to stderr)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_RUNTIME_DIRS = [
    Path("src/ai_knot"),
]

_EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        # Evaluation / benchmark harness files — these may legitimately reference
        # category names for reporting purposes.
        "src/ai_knot/__init__.py",  # only version info
    }
)

_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        "migrations",  # migration files may have schema comments
    }
)

# Patterns that indicate a benchmark-shaped runtime branch.
_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bCat[1-4]\b"),
    re.compile(r"\bLoCoMo\b", re.IGNORECASE),
    re.compile(r"category\s*[=!]=\s*['\"]?[1-4]['\"]?"),
    re.compile(r"locomo_cat", re.IGNORECASE),
]

# Files that are explicitly allowed to contain these strings (e.g. research docs,
# test scenarios, benchmark harness).
_ALLOWED_PATH_PREFIXES: tuple[str, ...] = (
    "tests/",
    "scripts/",
    "research/",
    "aiknotbench/",
    "notes_",
    "MULTI_AGENT",
    "refactoring_",
)


def _is_allowed(path: Path) -> bool:
    s = str(path)
    return any(s.startswith(p) or ("/" + p) in s for p in _ALLOWED_PATH_PREFIXES)


def _scan() -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []

    for root in _RUNTIME_DIRS:
        if not root.exists():
            continue
        for py_file in sorted(root.rglob("*.py")):
            if any(part in _EXCLUDED_DIRS for part in py_file.parts):
                continue
            if str(py_file) in _EXCLUDED_FILES:
                continue
            if _is_allowed(py_file):
                continue

            try:
                text = py_file.read_text(encoding="utf-8")
            except OSError:
                continue

            for lineno, line in enumerate(text.splitlines(), start=1):
                # Skip comment-only lines that document the prohibition itself.
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pat in _PATTERNS:
                    if pat.search(line):
                        hits.append((py_file, lineno, line.rstrip()))
                        break

    return hits


def main() -> int:
    hits = _scan()
    if not hits:
        print("check_no_benchmark_branches: OK")
        return 0

    print("check_no_benchmark_branches: FAIL — runtime contains benchmark-category references", file=sys.stderr)
    for path, lineno, line in hits:
        print(f"  {path}:{lineno}: {line}", file=sys.stderr)
    print(
        "\nRuntime code must not branch on Cat1/Cat2/Cat3/Cat4 or LoCoMo labels.\n"
        "Move any such logic to tests/ or benchmark harnesses.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
