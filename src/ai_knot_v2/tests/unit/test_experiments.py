"""Sprint 18-20 — E1/E2/E3 experiment smoke tests."""

from __future__ import annotations

from ai_knot_v2.bench.experiments import E1Config, E2Config, E3Config, run_e1, run_e2, run_e3


class TestE1RareCriticalSurvival:
    def test_critical_fact_survives_noise(self) -> None:
        cfg = E1Config(noise_count=10)
        result = run_e1([0], cfg)
        assert result["survival_rate"] == 1.0
        assert result["passed"]

    def test_result_has_expected_keys(self) -> None:
        result = run_e1([0], E1Config(noise_count=5))
        assert "survival_rate" in result
        assert "passed" in result
        assert "results" in result


class TestE2PhaseTransition:
    def test_recall_stable_at_small_noise(self) -> None:
        cfg = E2Config(transcript_sizes=[10], max_atoms_list=[100])
        result = run_e2([0], cfg)
        rows = result["rows"]
        assert rows[0]["recall_rate"] == 1.0

    def test_result_structure(self) -> None:
        cfg = E2Config(transcript_sizes=[5, 10], max_atoms_list=[100])
        result = run_e2([0], cfg)
        assert len(result["rows"]) == 2
        for row in result["rows"]:
            assert "noise_count" in row
            assert "recall_rate" in row


class TestE3CausalDependency:
    def test_depth2_recalls_penicillin(self) -> None:
        cfg = E3Config(chain_depths=[2], max_atoms=100)
        result = run_e3([0], cfg)
        assert result["rows"][0]["recall_rate"] == 1.0

    def test_depth1_recalls_city_hospital(self) -> None:
        cfg = E3Config(chain_depths=[2], max_atoms=100)
        result = run_e3([0], cfg)
        assert result["passed"]
