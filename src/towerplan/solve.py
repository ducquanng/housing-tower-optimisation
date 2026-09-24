"""Solve a tower instance and read the plan back out."""

from __future__ import annotations

from dataclasses import dataclass, field

import pyomo.environ as pyo

from .instance import Instance
from .model import build_model

SOLVERS = ("appsi_highs", "highs", "cbc", "glpk")


def available_solver() -> str:
    for name in SOLVERS:
        try:
            if pyo.SolverFactory(name).available():
                return name
        except Exception:  # noqa: BLE001 - a missing solver raises in several ways
            continue
    raise RuntimeError(f"No MILP solver found. Install one of: {', '.join(SOLVERS)}")


@dataclass
class Solution:
    status: str
    profit: float
    layouts: dict[str, int] = field(default_factory=dict)
    floors_by_owner: dict[str, int] = field(default_factory=dict)
    apartments: dict[tuple[str, int, str], int] = field(default_factory=dict)

    @property
    def total_apartments(self) -> int:
        return sum(self.apartments.values())

    def sector_shares(self) -> dict[str, float]:
        total = self.total_apartments
        out: dict[str, float] = {}
        for (sector, _, _), count in self.apartments.items():
            out[sector] = out.get(sector, 0.0) + count
        return {s: n / total for s, n in out.items()} if total else {}

    def average_area(self, sector: str) -> float:
        rows = [(a, n) for (s, a, _), n in self.apartments.items() if s == sector]
        total = sum(n for _, n in rows)
        return sum(a * n for a, n in rows) / total if total else 0.0

    @property
    def feasible(self) -> bool:
        return self.status == "optimal"


def solve(data: Instance, solver: str | None = None, time_limit: int = 120) -> Solution:
    model = build_model(data)
    opt = pyo.SolverFactory(solver or available_solver())
    # Solve without loading: an infeasible instance has no values to read back, and
    # asking for them raises. Infeasibility is an answer here, not an error.
    results = opt.solve(model, load_solutions=False)
    status = str(getattr(results, "termination_condition", None) or
                 results.solver.termination_condition).lower().split(".")[-1]
    if "optimal" not in status:
        return Solution(status=status, profit=float("nan"))
    model.solutions.load_from(results) if hasattr(results, "solution") else None
    try:
        pyo.value(model.total_profit)
    except (ValueError, RuntimeError):
        opt.solve(model)  # reload values through the default path

    value = pyo.value
    return Solution(
        status="optimal",
        profit=float(value(model.total_profit)),
        layouts={v: int(round(value(model.X[v]))) for v in model.LAYOUTS},
        floors_by_owner={
            h: int(round(sum(value(model.W[v, h]) for v in model.LAYOUTS))) for h in model.OWNERS
        },
        apartments={
            (s, a, h): int(round(value(model.Y[s, a, h])))
            for s in model.SECTORS
            for a in model.AREAS
            for h in model.OWNERS
            if round(value(model.Y[s, a, h])) > 0
        },
    )
