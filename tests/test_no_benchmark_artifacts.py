"""Guard: heuristic files must not contain LoCoMo dataset tokens or pf5 artifacts.

Scans only the three core heuristic files. 'Acme' is excluded because
types.py:47 uses it legitimately in a docstring example.
"""

from __future__ import annotations

import pathlib
import re

HEURISTIC_FILES = [
    "src/ai_knot/materialization.py",
    "src/ai_knot/query_contract.py",
    "src/ai_knot/support_retrieval.py",
]

LEAK_TOKENS = [
    "pf5",
    "LoCoMo",
    "added for pf5",
]

DATASET_NAMES = [
    "Audrey",
    "Andrew",
    "Pixie",
    "Tacoma",
    "Deborah",
    "Eagles",
]


def test_no_pf5_or_dataset_artifacts_in_heuristic_files() -> None:
    """Fail if any known bench artifact appears in heuristic source files."""
    leaks: list[tuple[str, str]] = []
    root = pathlib.Path(__file__).parent.parent
    for f in HEURISTIC_FILES:
        text = (root / f).read_text()
        for tok in LEAK_TOKENS + DATASET_NAMES:
            if re.search(rf"\b{re.escape(tok)}\b", text):
                leaks.append((f, tok))
    assert not leaks, f"Bench artifact leaked into heuristic file: {leaks}"
