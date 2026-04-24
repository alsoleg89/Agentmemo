"""
Architecture gate: no LLM imports allowed in core / ops / store / api.

This test is intentionally strict. Any import of an LLM provider library
in the memory core violates the "deterministic memory kernel" invariant
described in src/ai_knot_v2/CLAUDE.md §1.
"""

import ast
import subprocess
from pathlib import Path

import pytest

# Directories that must never import LLM providers.
CORE_DIRS = ["core", "ops", "store", "api"]

# Provider names whose presence in an import statement is forbidden.
FORBIDDEN_NAMES = ["openai", "anthropic", "gpt", "claude", "litellm", "langchain"]

V2_ROOT = Path(__file__).parents[2]  # src/ai_knot_v2/


def _python_files_under(directory: Path) -> list[Path]:
    return list(directory.rglob("*.py"))


def _imports_from_file(path: Path) -> list[str]:
    """Return a flat list of top-level module names imported by *path*."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("core_dir", CORE_DIRS)
def test_no_llm_import_in_core_dir(core_dir: str) -> None:
    """No forbidden LLM provider may be imported from core memory directories."""
    directory = V2_ROOT / core_dir
    if not directory.exists():
        pytest.skip(f"{directory} does not exist yet (pre-Sprint 1)")

    violations: list[str] = []
    for py_file in _python_files_under(directory):
        imported = _imports_from_file(py_file)
        for name in imported:
            if any(forbidden in name.lower() for forbidden in FORBIDDEN_NAMES):
                violations.append(f"{py_file.relative_to(V2_ROOT)}: imports '{name}'")

    assert not violations, (
        "LLM provider imports detected in memory core — this violates the "
        "deterministic-core invariant (see src/ai_knot_v2/CLAUDE.md §1):\n" + "\n".join(violations)
    )


def test_no_llm_import_grep_check() -> None:
    """Grep-based cross-check for any string occurrence, not just AST imports."""
    pattern = r"openai|anthropic|litellm|langchain"
    include_dirs = " ".join(f"src/ai_knot_v2/{d}" for d in CORE_DIRS)

    result = subprocess.run(
        f"grep -rl --include='*.py' '{pattern}' {include_dirs} 2>/dev/null || true",
        shell=True,
        capture_output=True,
        text=True,
        cwd=V2_ROOT.parents[1],  # repo root
    )
    found = result.stdout.strip()
    assert not found, "Grep found LLM provider strings in core directories:\n" + found
