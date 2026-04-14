"""CI gate: query_runtime, query_operators, and query_contract must not import
from ai_knot.storage.* or access kb private attributes.

This mirrors scripts/check_query_runtime_isolation.py but runs as a pytest test
for tighter integration into the test suite.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src" / "ai_knot"

ISOLATED_MODULES = [
    SRC / "query_runtime.py",
    SRC / "query_operators.py",
    SRC / "query_contract.py",
]

FORBIDDEN_IMPORTS = [
    "ai_knot.storage",
    "ai_knot.knowledge",
]

FORBIDDEN_ATTRS = [
    "kb._",
    "self._storage",
    "self._retriever",
    "self._bundle_store",
    "self._claim_store",
]


def _check_imports(tree: ast.AST, filepath: Path) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in FORBIDDEN_IMPORTS:
                    if alias.name.startswith(forbidden):
                        violations.append(f"{filepath.name}:{node.lineno}: imports {alias.name!r}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for forbidden in FORBIDDEN_IMPORTS:
                if module.startswith(forbidden):
                    violations.append(f"{filepath.name}:{node.lineno}: imports from {module!r}")
    return violations


def _check_forbidden_attrs(tree: ast.AST, filepath: Path) -> list[str]:
    violations: list[str] = []
    source = filepath.read_text(encoding="utf-8")
    for attr_pattern in FORBIDDEN_ATTRS:
        for lineno, line in enumerate(source.splitlines(), start=1):
            if attr_pattern in line:
                violations.append(
                    f"{filepath.name}:{lineno}: uses forbidden pattern {attr_pattern!r} in {line.strip()!r}"
                )
    return violations


def test_query_runtime_no_storage_imports():
    """query_runtime.py must not import from ai_knot.storage.* or ai_knot.knowledge."""
    path = SRC / "query_runtime.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations = _check_imports(tree, path)
    assert not violations, "query_runtime.py isolation violated:\n" + "\n".join(violations)


def test_query_operators_no_storage_imports():
    """query_operators.py must not import from ai_knot.storage.* or ai_knot.knowledge."""
    path = SRC / "query_operators.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations = _check_imports(tree, path)
    assert not violations, "query_operators.py isolation violated:\n" + "\n".join(violations)


def test_query_contract_no_storage_imports():
    """query_contract.py must not import from ai_knot.storage.* or ai_knot.knowledge."""
    path = SRC / "query_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations = _check_imports(tree, path)
    assert not violations, "query_contract.py isolation violated:\n" + "\n".join(violations)


def test_isolated_modules_no_forbidden_private_attrs():
    """Isolated modules must not access kb._ or self._storage etc."""
    all_violations: list[str] = []
    for path in ISOLATED_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        violations = _check_forbidden_attrs(tree, path)
        all_violations.extend(violations)
    assert not all_violations, "Private attribute access in isolated modules:\n" + "\n".join(
        all_violations
    )


def test_support_retrieval_is_the_only_physical_retrieval_in_query_runtime():
    """query_runtime must import from support_retrieval, not bypass it."""
    path = SRC / "query_runtime.py"
    source = path.read_text(encoding="utf-8")
    # Must import support_retrieval
    assert "support_retrieval" in source, (
        "query_runtime.py should import from support_retrieval "
        "as the sole physical retrieval boundary"
    )
