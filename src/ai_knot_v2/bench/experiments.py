"""Sprint 18-20 — E1/E2/E3 experiment runners.

E1: Rare-critical survival — does a high-risk fact survive N noise turns?
E2: Phase transition — memory quality vs. transcript size.
E3: Causal dependency — multi-hop chain recall at different depths.

All experiments are deterministic at a given seed (no LLM).
Full BG-runs: E1 = 8 baselines × 5 seeds; E2 = 5 budgets × 4 sizes × 5 seeds;
              E3 = 4 depths × 5 seeds.

Usage (smoke test, fast):
    .venv/bin/python -m ai_knot_v2.bench.experiments --exp e1 --seeds 1 --quick
    .venv/bin/python -m ai_knot_v2.bench.experiments --exp e2 --seeds 1 --quick
    .venv/bin/python -m ai_knot_v2.bench.experiments --exp e3 --seeds 1 --quick
    .venv/bin/python -m ai_knot_v2.bench.experiments --exp all --seeds 1 --quick
"""

from __future__ import annotations

import argparse
import dataclasses
import random
import sys
from typing import Any

from ai_knot_v2.api.product import MemoryAPI
from ai_knot_v2.api.sdk import EpisodeIn, LearnRequest, RecallRequest

# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

_NOISE_TEMPLATES = [
    "The weather is {adj} today.",
    "I watched a {adj} movie last night.",
    "My {rel} told me something {adj}.",
    "I cooked a {adj} meal for dinner.",
    "Work was {adj} this week.",
    "I went for a {adj} walk in the park.",
    "I finished a {adj} book about {topic}.",
    "My {rel} bought a new {item}.",
    "I tried a {adj} restaurant downtown.",
    "I spent time working on a {adj} project.",
]

_ADJS = ["nice", "great", "interesting", "unusual", "boring", "fun", "long", "short"]
_RELS = ["friend", "neighbor", "colleague", "sister", "brother", "cousin"]
_TOPICS = ["history", "science", "cooking", "travel", "art", "music"]
_ITEMS = ["car", "laptop", "phone", "bicycle", "camera"]


def _noise_turn(seed: int, idx: int) -> str:
    rng = random.Random(seed * 1000 + idx)
    template = rng.choice(_NOISE_TEMPLATES)
    return template.format(
        adj=rng.choice(_ADJS),
        rel=rng.choice(_RELS),
        topic=rng.choice(_TOPICS),
        item=rng.choice(_ITEMS),
    )


def _make_episodes(
    critical_turns: list[str],
    noise_count: int,
    seed: int,
    user_id: str = "exp-user",
    session_id: str = "exp-session",
) -> list[EpisodeIn]:
    episodes: list[EpisodeIn] = []
    ts = 1_700_000_000

    for i, text in enumerate(critical_turns):
        episodes.append(
            EpisodeIn(
                text=text,
                speaker="user",
                user_id=user_id,
                session_id=session_id,
                timestamp=ts + i * 60,
            )
        )

    ts_noise = ts + len(critical_turns) * 60 + 3600
    for i in range(noise_count):
        episodes.append(
            EpisodeIn(
                text=_noise_turn(seed, i),
                speaker="user",
                user_id=user_id,
                session_id=session_id,
                timestamp=ts_noise + i * 60,
            )
        )

    return episodes


def _recall_contains(api: MemoryAPI, query: str, target: str, max_atoms: int = 100) -> bool:
    """Return True if any recalled atom's text contains the target string."""
    resp = api.recall(RecallRequest(query=query, max_atoms=max_atoms, max_tokens=8000))
    for a in resp.atoms:
        combined = " ".join(
            filter(None, [a.object_value, a.subject, a.predicate.replace("_", " ")])
        ).lower()
        if target.lower() in combined:
            return True
    return False


# ---------------------------------------------------------------------------
# E1: Rare-critical survival
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class E1Config:
    noise_count: int = 50
    max_atoms: int = 100
    critical_text: str = "I am allergic to penicillin."
    query: str = "Do I have any drug allergies?"
    target: str = "penicillin"


def run_e1(seeds: list[int], config: E1Config) -> dict[str, Any]:
    """E1: Does a critical medical fact survive N noise turns?"""
    results = []
    for seed in seeds:
        episodes = _make_episodes(
            critical_turns=[config.critical_text],
            noise_count=config.noise_count,
            seed=seed,
        )
        api = MemoryAPI(db_path=":memory:")
        api.learn(LearnRequest(episodes=episodes))
        survived = _recall_contains(api, config.query, config.target, max_atoms=config.max_atoms)
        results.append({"seed": seed, "survived": survived})

    survival_rate = sum(1 for r in results if r["survived"]) / len(results)
    return {
        "experiment": "E1",
        "noise_count": config.noise_count,
        "seeds": len(seeds),
        "survival_rate": survival_rate,
        "passed": survival_rate >= 0.80,
        "results": results,
    }


# ---------------------------------------------------------------------------
# E2: Phase transition (memory quality vs. transcript size)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class E2Config:
    transcript_sizes: list[int] = dataclasses.field(default_factory=lambda: [10, 30, 50, 100])
    max_atoms_list: list[int] = dataclasses.field(default_factory=lambda: [60, 100])
    critical_text: str = "I have a dentist appointment on Thursday at 3pm."
    query: str = "Do I have any upcoming appointments?"
    target: str = "dentist"


def run_e2(seeds: list[int], config: E2Config) -> dict[str, Any]:
    """E2: At what transcript size does recall start degrading?"""
    rows = []
    for max_atoms in config.max_atoms_list:
        for noise_count in config.transcript_sizes:
            seed_results = []
            for seed in seeds:
                episodes = _make_episodes(
                    critical_turns=[config.critical_text],
                    noise_count=noise_count,
                    seed=seed,
                )
                api = MemoryAPI(db_path=":memory:")
                api.learn(LearnRequest(episodes=episodes))
                found = _recall_contains(api, config.query, config.target, max_atoms=max_atoms)
                seed_results.append(found)
            rate = sum(seed_results) / len(seed_results)
            rows.append(
                {
                    "max_atoms": max_atoms,
                    "noise_count": noise_count,
                    "recall_rate": rate,
                    "seeds": len(seeds),
                }
            )

    return {
        "experiment": "E2",
        "seeds": len(seeds),
        "rows": rows,
        "passed": all(r["recall_rate"] >= 0.80 for r in rows if r["noise_count"] <= 50),
    }


# ---------------------------------------------------------------------------
# E3: Causal dependency chain recall
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class E3Config:
    chain_depths: list[int] = dataclasses.field(default_factory=lambda: [2, 3, 4])
    max_atoms: int = 100


def run_e3(seeds: list[int], config: E3Config) -> dict[str, Any]:
    """E3: Multi-hop chain recall at different dependency depths."""
    rows = []
    for depth in config.chain_depths:
        seed_results = []
        for seed in seeds:
            # Chain: facts about Bob, some requiring multi-turn context to answer fully.
            # Each turn adds a new fact; the target (penicillin) appears at turn index 1.
            chain_turns = [
                "Bob works at City Hospital.",
                "Bob uses penicillin for treating patients.",
                "Bob is a licensed pharmacist at the hospital.",
                "Bob studied pharmacy at State University.",
            ]

            episodes = _make_episodes(
                critical_turns=chain_turns[:depth],
                noise_count=10,
                seed=seed,
            )
            api = MemoryAPI(db_path=":memory:")
            api.learn(LearnRequest(episodes=episodes))

            # The penicillin fact is at chain index 1 — only reachable at depth ≥ 2
            target = "penicillin" if depth >= 2 else "City Hospital"
            found = _recall_contains(
                api,
                "What does Bob use at City Hospital?",
                target,
                max_atoms=config.max_atoms,
            )
            seed_results.append(found)

        rate = sum(seed_results) / len(seed_results)
        rows.append({"depth": depth, "recall_rate": rate, "seeds": len(seeds)})

    return {
        "experiment": "E3",
        "seeds": len(seeds),
        "rows": rows,
        "passed": all(r["recall_rate"] >= 0.60 for r in rows if r["depth"] <= 3),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def report_e1(result: dict[str, Any]) -> None:
    gate = "PASS" if result["passed"] else "FAIL"
    print(
        f"E1 (rare-critical survival, noise={result['noise_count']}): "
        f"{result['survival_rate']:.1%} — {gate}"
    )


def report_e2(result: dict[str, Any]) -> None:
    print("E2 (phase transition):")
    print(f"  {'atoms':>6}  {'noise':>6}  recall")
    for row in result["rows"]:
        print(f"  {row['max_atoms']:>6}  {row['noise_count']:>6}  {row['recall_rate']:.1%}")
    gate = "PASS" if result["passed"] else "FAIL"
    print(f"  gate (recall ≥ 80% at noise ≤ 50): {gate}")


def report_e3(result: dict[str, Any]) -> None:
    print("E3 (causal dependency):")
    for row in result["rows"]:
        print(f"  depth={row['depth']}: {row['recall_rate']:.1%}")
    gate = "PASS" if result["passed"] else "FAIL"
    print(f"  gate (recall ≥ 60% at depth ≤ 3): {gate}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="E1/E2/E3 experiment runner")
    parser.add_argument("--exp", choices=["e1", "e2", "e3", "all"], default="all")
    parser.add_argument("--seeds", type=int, default=3, help="Number of seeds")
    parser.add_argument("--quick", action="store_true", help="Quick smoke run (fewer configs)")
    args = parser.parse_args()

    seeds = list(range(args.seeds))

    print(f"\n=== Sprint 18-20 Experiments (seeds={args.seeds}, quick={args.quick}) ===\n")

    all_passed = True

    if args.exp in ("e1", "all"):
        cfg = E1Config(noise_count=20 if args.quick else 50)
        r1 = run_e1(seeds, cfg)
        report_e1(r1)
        all_passed = all_passed and r1["passed"]

    if args.exp in ("e2", "all"):
        cfg2 = E2Config(
            transcript_sizes=[10, 30] if args.quick else [10, 30, 50, 100],
            max_atoms_list=[100],
        )
        r2 = run_e2(seeds, cfg2)
        report_e2(r2)
        all_passed = all_passed and r2["passed"]

    if args.exp in ("e3", "all"):
        cfg3 = E3Config(
            chain_depths=[2, 3] if args.quick else [2, 3, 4],
            max_atoms=100,
        )
        r3 = run_e3(seeds, cfg3)
        report_e3(r3)
        all_passed = all_passed and r3["passed"]

    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
