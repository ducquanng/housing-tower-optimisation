"""Solve the example tower, run the policy sweep, and write reports/."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .instance import example_instance  # noqa: E402
from .solve import solve  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports"
FIG_DIR = REPORT_DIR / "figures"
SOCIAL_SHARES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]


def md_table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def sweep_social_share(base, shares=SOCIAL_SHARES):
    """Re-solve with a rising social housing obligation; the rest of the policy holds."""
    results = []
    for share in shares:
        data = replace(base, min_sector_share={**base.min_sector_share, "social": share})
        results.append((share, solve(data)))
    return results


def run() -> dict:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    base = example_instance()
    solution = solve(base)
    if not solution.feasible:
        raise RuntimeError(f"Base instance is {solution.status}")

    sweep = sweep_social_share(base)
    feasible = [(s, r) for s, r in sweep if r.feasible]
    baseline_profit = next(r.profit for s, r in feasible if s == 0.0)

    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.plot([s for s, _ in feasible], [r.profit / 1e6 for _, r in feasible], "o-", color="#4C72B0")
    ax.set(xlabel="Minimum social housing share", ylabel="Total profit (EUR million)",
           title="What the social housing obligation costs")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "social_share_tradeoff.png", dpi=150)
    plt.close(fig)

    lines = [
        "# Mixed-tenure tower: optimal plan and the cost of the policy constraints",
        "",
        f"Generated {date.today().isoformat()} by `python -m towerplan.report`. "
        f"{base.floors} floors, {len(base.layouts)} layouts, {len(base.areas)} apartment sizes, "
        f"{len(base.sectors)} tenure sectors, {len(base.owners)} owner types. "
        "All parameters are invented; see `instance.py`.",
        "",
        "## Optimal plan",
        "",
        f"Total profit **EUR {solution.profit / 1e6:.2f} million** across "
        f"{solution.total_apartments} apartments.",
        "",
        md_table(["Layout", "Floors"], [[k, v] for k, v in solution.layouts.items()]),
        "",
        md_table(["Owner", "Floors"], [[k, v] for k, v in solution.floors_by_owner.items()]),
        "",
        md_table(
            ["Sector", "Share of apartments", "Average area (m²)", "Required share"],
            [
                [s, f"{share:.1%}", f"{solution.average_area(s):.1f}",
                 f"{base.min_sector_share.get(s, 0):.0%}"]
                for s, share in sorted(solution.sector_shares().items())
            ],
        ),
        "",
        "Both regulated sectors land exactly on their minimum share. That is the model "
        "saying the obligation binds: every social apartment beyond the minimum would "
        "displace a free-sector one worth more.",
        "",
        "## What the social obligation costs",
        "",
        "![Trade-off](figures/social_share_tradeoff.png)",
        "",
        md_table(
            ["Minimum social share", "Profit (EUR m)", "Change vs 0%", "Apartments", "Status"],
            [
                [f"{share:.0%}",
                 f"{result.profit / 1e6:.2f}" if result.feasible else "—",
                 f"{(result.profit - baseline_profit) / 1e6:+.2f}" if result.feasible else "—",
                 result.total_apartments if result.feasible else "—",
                 "optimal" if result.feasible else result.status]
                for share, result in sweep
            ],
        ),
        "",
        "Read the last column before the others: past a point the obligation cannot be met "
        "at all alongside the average-area and ownership rules, and the model reports "
        "infeasible rather than returning a plan. For a planner, the useful output is the "
        "slope of the feasible part — the profit given up per percentage point of social "
        "housing — and the share at which the scheme stops being buildable.",
        "",
        "## Limitations",
        "",
        "- Profit per apartment is a fixed parameter. In reality it moves with the sales "
        "programme, financing cost and the timing of completion.",
        "- One tower in isolation, with no construction cost, phasing or planning risk.",
        "- Integer floors and apartments, so there is no partial-floor compromise; that is "
        "realistic here and is what makes the problem combinatorial.",
    ]
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "plan.md").write_text("\n".join(lines))

    summary = {
        "profit": solution.profit,
        "total_apartments": solution.total_apartments,
        "layouts": solution.layouts,
        "floors_by_owner": solution.floors_by_owner,
        "sector_shares": solution.sector_shares(),
        "sweep": [
            {"social_share": s, "status": r.status,
             "profit": r.profit if r.feasible else None} for s, r in sweep
        ],
    }
    (REPORT_DIR / "metrics.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
