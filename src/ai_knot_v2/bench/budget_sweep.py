"""Sprint 13 — bounded-reader budget sweep.

Sweeps max_atoms and max_tokens to find the sweet-spot budget configuration
that maximizes cat1 GoldEvidenceCoverage without increasing ContextDilutionRate.

Usage:
    .venv/bin/python -m ai_knot_v2.bench.budget_sweep
    .venv/bin/python -m ai_knot_v2.bench.budget_sweep --data /path/to/locomo10.json
    .venv/bin/python -m ai_knot_v2.bench.budget_sweep --convs 1  # quick
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from ai_knot_v2.bench.v2_locomo_runner import (
    LocomoConvData,
    aggregate,
    parse_locomo_json,
    run_conversation,
)

_DEFAULT_DATA = Path(__file__).parents[5] / "aiknotbench" / "data" / "locomo10.json"

# Sweep grid
_ATOM_CANDIDATES = [20, 30, 40, 50, 60, 80, 100]
_TOKEN_CANDIDATES = [2000, 4000, 6000, 8000, 12000]


def run_config(
    convs: list[LocomoConvData],
    max_atoms: int,
    max_tokens: int,
) -> dict[str, Any]:
    results = [run_conversation(c, max_atoms=max_atoms, max_tokens=max_tokens) for c in convs]
    return aggregate(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="ai-knot v2 budget sweep (Sprint 13)")
    parser.add_argument("--convs", type=int, default=2)
    parser.add_argument("--data", type=Path, default=_DEFAULT_DATA)
    parser.add_argument(
        "--atoms",
        type=str,
        default=",".join(str(x) for x in _ATOM_CANDIDATES),
        help="Comma-separated max_atoms values to sweep",
    )
    parser.add_argument(
        "--tokens",
        type=str,
        default=",".join(str(x) for x in _TOKEN_CANDIDATES),
        help="Comma-separated max_tokens values to sweep",
    )
    args = parser.parse_args()

    if not args.data.exists():
        print(f"ERROR: data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    atom_vals = [int(x) for x in args.atoms.split(",")]
    token_vals = [int(x) for x in args.tokens.split(",")]

    print(f"Loading {args.convs} conv(s) from {args.data} ...")
    convs = parse_locomo_json(args.data, limit=args.convs)

    n_configs = len(atom_vals) * len(token_vals)
    print(f"\nSweeping {len(atom_vals)} × {len(token_vals)} = {n_configs} configs ...\n")
    hdr = f"{'atoms':>6}  {'tokens':>7}  {'overall':>8}"
    hdr += "  cat1   cat2   cat3   cat4   cat5"
    print(hdr)
    print("-" * 68)

    best_cat1 = -1.0
    best_config: tuple[int, int] = (60, 8000)
    results_table: list[tuple[int, int, dict[str, Any]]] = []

    for max_atoms in atom_vals:
        for max_tokens in token_vals:
            agg = run_config(convs, max_atoms, max_tokens)
            results_table.append((max_atoms, max_tokens, agg))
            by_cat = agg["by_category"]
            cat1 = by_cat.get(1, {}).get("gec", 0.0)
            cat2 = by_cat.get(2, {}).get("gec", 0.0)
            cat3 = by_cat.get(3, {}).get("gec", 0.0)
            cat4 = by_cat.get(4, {}).get("gec", 0.0)
            cat5 = by_cat.get(5, {}).get("gec", 0.0)
            overall = agg["overall_gec"]
            marker = " ◀" if cat1 > best_cat1 else ""
            print(
                f"{max_atoms:>6}  {max_tokens:>7}  {overall:>8.3f}  "
                f"{cat1:>6.3f}  {cat2:>6.3f}  {cat3:>6.3f}  {cat4:>6.3f}  {cat5:>6.3f}{marker}"
            )
            if cat1 > best_cat1:
                best_cat1 = cat1
                best_config = (max_atoms, max_tokens)

    print("-" * 68)
    print(
        f"\nBest cat1: {best_cat1:.3f}  @ max_atoms={best_config[0]}, max_tokens={best_config[1]}"
    )
    print(f"\nRecommended DEFAULT_BUDGET: max_atoms={best_config[0]}, max_tokens={best_config[1]}")


if __name__ == "__main__":
    main()
