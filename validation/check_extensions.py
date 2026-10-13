"""Extra checks: python -m pytest -q validation/check_extensions.py.

Named separately so default pytest still discovers the original 15 BTC tests.
"""
import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finops.extensions import reasoning_budget, carbon_scheduling


def test_reasoning_counterfactual_and_same_token_control():
    rows = [{"input_tokens": "1000", "output_tokens": "600", "is_reasoning": "1",
             "cached_input_tokens": "0", "is_batch": "0", "route_tier": "small"}]
    r = reasoning_budget(rows, {"small": (1.0, 2.0)}, cap_fraction=0)
    assert r["baseline_cost_usd"] == pytest.approx(0.0022)
    assert r["scenario_cost_usd"] == pytest.approx(0.0012)
    assert r["baseline_energy_wh"] == pytest.approx(38.4)
    assert r["scenario_energy_wh"] == pytest.approx(0.33)
    assert r["same_token_saved_cost_usd"] == 0
    assert r["same_token_saved_energy_wh"] == pytest.approx(37.92)


def test_cap_does_not_reroute_if_already_below_limit():
    r = reasoning_budget([], {}, cap_fraction=0.05)
    assert r["saved_cost_usd"] == 0 and r["saved_energy_wh"] == 0
    row = {"input_tokens": "1000", "output_tokens": "600", "is_reasoning": "1",
           "cached_input_tokens": "0", "is_batch": "0", "route_tier": "small"}
    normal = dict(row, is_reasoning="0")
    below = reasoning_budget([row] + [normal] * 19, {"small": (1.0, 2.0)}, 0.05)
    assert below["rerouted_requests"] == 0
    assert below["scenario_cost_usd"] == below["baseline_cost_usd"]
    with pytest.raises(ValueError):
        reasoning_budget([], {}, cap_fraction=1.1)


def test_carbon_units_days_and_interruptible_gate():
    jobs = [{"job_id": "move", "gpu_type": "X", "hours_per_day": 2,
             "days": 3, "num_gpus": 2, "interruptible": 1},
            {"job_id": "stay", "gpu_type": "X", "hours_per_day": 24,
             "days": 30, "num_gpus": 1, "interruptible": 0}]
    r = carbon_scheduling(jobs, {"X": {"watts": 100}})
    assert len(r["jobs"]) == 1
    assert r["total_energy_wh"] == 1200
    assert r["baseline_carbon_g"] == 456
    assert r["cleanest_carbon_g"] == 36
    assert r["saved_carbon_g"] == 420
    assert r["cheapest_region"] == "us-east-wa"


def test_btc_reference_unchanged_and_extension_totals_reconcile():
    from missions import m1_efficiency_audit, m2_inference_levers, m3_purchasing
    from missions import m4_allocation, m5_report, your_turn
    root = Path(__file__).resolve().parents[1]
    reference = json.loads((root / "outputs/baseline_reference.json").read_text(encoding="utf-8"))
    for name, mission in zip(("M1", "M2", "M3", "M4", "M5"),
                             (m1_efficiency_audit, m2_inference_levers, m3_purchasing,
                              m4_allocation, m5_report)):
        assert mission.run(False) == reference[name]
    result = your_turn.run(False)
    r, c = result["reasoning"], result["carbon"]
    assert r["baseline_cost_usd"] == pytest.approx(reference["M2"]["optimized_daily"], abs=0.005)
    assert r["reasoning_requests_after"] <= sum(g["requests"] for g in r["groups"].values()) * r["cap_fraction"]
    assert r["saved_cost_usd"] == pytest.approx(r["baseline_cost_usd"] - r["scenario_cost_usd"])
    assert c["saved_carbon_g"] == pytest.approx(sum(j["saved_carbon_g"] for j in c["jobs"]))
    assert sum(g["traffic_pct"] for g in r["groups"].values()) == pytest.approx(100)
