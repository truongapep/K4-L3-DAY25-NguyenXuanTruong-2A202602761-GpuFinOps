"""Two offline extensions using the BTC data and lab energy assumptions.

No measured hardware energy or model quality is implied by these estimates.
"""
from __future__ import annotations

import math
from finops import pricing, sustainability


def reasoning_budget(rows, model_prices, cap_fraction=0.05):
    """Group observed traffic, then simulate a cap with explicit output assumptions.

    The generator multiplies reasoning output by six. The counterfactual reverses
    that factor only for rerouted requests; input, model tier, cache and batch stay
    fixed. Highest-output reasoning requests are rerouted first for a reproducible
    offline sensitivity estimate, not a validated production routing policy.
    """
    if not 0 <= cap_fraction <= 1:
        raise ValueError("cap_fraction must be between zero and one")
    rows = list(rows)
    groups = {name: {"requests": 0, "tokens": 0, "cost_usd": 0.0,
                     "energy_wh": 0.0, "same_tokens_normal_wh": 0.0}
              for name in ("normal", "reasoning")}
    candidates = []
    for i, row in enumerate(rows):
        inp, out = int(row["input_tokens"]), int(row["output_tokens"])
        reasoning = bool(int(row["is_reasoning"]))
        group = groups["reasoning" if reasoning else "normal"]
        pin, pout = model_prices[row["route_tier"]]
        cost = pricing.request_cost(inp, out, pin, pout,
                                    cached_in=int(row["cached_input_tokens"]),
                                    batch=bool(int(row["is_batch"])))
        wh = sustainability.wh_per_query(inp + out, is_reasoning=reasoning)
        group["requests"] += 1
        group["tokens"] += inp + out
        group["cost_usd"] += cost
        group["energy_wh"] += wh
        group["same_tokens_normal_wh"] += sustainability.wh_per_query(inp + out)
        if reasoning:
            candidates.append((i, out, cost, wh))

    count = len(rows)
    before_cost = sum(g["cost_usd"] for g in groups.values())
    before_wh = sum(g["energy_wh"] for g in groups.values())
    limit = math.floor(count * cap_fraction)
    reroute_count = max(0, len(candidates) - limit)
    # Stable index tie-break avoids relying on row ordering from a database.
    selected = sorted(candidates, key=lambda c: (-c[1], c[0]))[:reroute_count]
    saved_cost = saved_wh = same_token_saved_wh = 0.0
    for i, out, cost, wh in selected:
        row = rows[i]
        inp = int(row["input_tokens"])
        pin, pout = model_prices[row["route_tier"]]
        normal_out = out / 6.0
        new_cost = pricing.request_cost(inp, normal_out, pin, pout,
                                        cached_in=int(row["cached_input_tokens"]),
                                        batch=bool(int(row["is_batch"])))
        saved_cost += cost - new_cost
        saved_wh += wh - sustainability.wh_per_query(inp + normal_out)
        same_token_saved_wh += wh - sustainability.wh_per_query(inp + out)
    for group in groups.values():
        group["traffic_pct"] = group["requests"] / count * 100 if count else 0.0
        group["cost_pct"] = group["cost_usd"] / before_cost * 100 if before_cost else 0.0
        group["energy_pct"] = group["energy_wh"] / before_wh * 100 if before_wh else 0.0
    return {"groups": groups, "cap_fraction": cap_fraction,
            "rerouted_requests": reroute_count,
            "reasoning_requests_after": len(candidates) - reroute_count,
            "baseline_cost_usd": before_cost, "scenario_cost_usd": before_cost - saved_cost,
            "saved_cost_usd": saved_cost, "baseline_energy_wh": before_wh,
            "scenario_energy_wh": before_wh - saved_wh, "saved_energy_wh": saved_wh,
            "same_token_saved_cost_usd": 0.0,
            "same_token_saved_energy_wh": same_token_saved_wh}


def carbon_scheduling(jobs, catalog, baseline_region="us-east-1"):
    """Estimate electricity and carbon using catalog watts at constant rated power.

    Use each job's actual `days`, not M3's common 30-day extrapolation. Electricity
    is separate from GPU rent and is never subtracted from the M5 bill.
    """
    if baseline_region not in sustainability.REGION_CARBON:
        raise ValueError("unknown baseline region")
    cleanest = min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get)
    cheapest = min(sustainability.REGION_PRICE_KWH, key=sustainability.REGION_PRICE_KWH.get)
    details = []
    for job in jobs:
        if not int(job["interruptible"]):
            continue
        gpu_hours = float(job["hours_per_day"]) * float(job["days"]) * int(job["num_gpus"])
        wh = gpu_hours * float(catalog[job["gpu_type"]]["watts"])
        before = sustainability.carbon_g(wh, baseline_region)
        after = sustainability.carbon_g(wh, cleanest)
        details.append({"job_id": job["job_id"], "gpu_hours": gpu_hours,
                        "energy_wh": wh, "baseline_carbon_g": before,
                        "cleanest_carbon_g": after, "saved_carbon_g": before - after})
    total_wh = sum(j["energy_wh"] for j in details)
    regions = [{"region": region,
                "usd_per_kwh": sustainability.REGION_PRICE_KWH[region],
                "gco2_per_kwh": intensity,
                "electricity_usd": sustainability.energy_cost_usd(total_wh, region),
                "carbon_g": sustainability.carbon_g(total_wh, region)}
               for region, intensity in sustainability.REGION_CARBON.items()]
    before = sustainability.carbon_g(total_wh, baseline_region)
    after = sustainability.carbon_g(total_wh, cleanest)
    return {"baseline_region": baseline_region, "cleanest_region": cleanest,
            "cheapest_region": cheapest, "jobs": details, "regions": regions,
            "total_energy_wh": total_wh, "baseline_carbon_g": before,
            "cleanest_carbon_g": after, "saved_carbon_g": before - after,
            "saved_carbon_pct": (1 - after / before) * 100 if before else 0.0}
