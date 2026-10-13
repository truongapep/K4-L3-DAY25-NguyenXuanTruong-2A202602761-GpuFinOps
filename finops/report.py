"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly") -> str:
    """Return a markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — GPU Cost Optimization Report",
        "",
        f"**Period:** {period}  ",
        f"**Baseline spend:** ${baseline_usd:,.0f}  ",
        f"**Optimized spend:** ${optimized_usd:,.0f}  ",
        f"**Projected savings:** ${savings:,.0f}  (**{pct:.0f}%**)",
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD) |",
        "|---|---|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.0f} |")
    if sustainability:
        lines += [
            "",
            "## Sustainability",
            "",
            f"- Energy per query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per query: {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Cheapest+cleanest region: {sustainability.get('best_region', 'n/a')}",
        ]
    lines += ["", "_Figures are June-2026 as-of snapshots; re-baseline before acting._"]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str, baseline_usd: float | None = None) -> str:
    """Write a waterfall when baseline is supplied; keep the original bar fallback."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = list(levers.keys())
    vals = [levers[n] for n in names]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    if baseline_usd is None:
        ax.bar(names, vals, color="#2e548a")
    else:
        labels = ["Baseline"] + names + ["Optimized"]
        current = baseline_usd
        ax.bar(0, current, color="#2e548a")
        ax.text(0, current, f"${current:,.0f}", ha="center", va="bottom", fontsize=9)
        for i, value in enumerate(vals, 1):
            next_value = current - value
            ax.plot([i-1+0.4, i-0.4], [current, current], color="#888888", linewidth=1)
            ax.bar(i, value, bottom=next_value, color="#30966b")
            ax.text(i, current, f"-${value:,.0f}", ha="center", va="bottom", fontsize=9)
            current = next_value
        ax.plot([len(vals)+0.4, len(vals)+0.6], [current, current], color="#888888", linewidth=1)
        ax.bar(len(labels)-1, current, color="#2e548a")
        ax.text(len(labels)-1, current, f"${current:,.0f}", ha="center", va="bottom", fontsize=9)
        ax.set_xticks(range(len(labels)), labels)
        ax.set_ylim(0, baseline_usd * 1.15)
    ax.set_ylabel("USD / month")
    ax.set_title("GPU cost savings by FinOps lever")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
