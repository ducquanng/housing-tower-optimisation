"""The mixed-integer programme itself.

Decisions
    X[layout]                 how many floors are built to each layout
    W[layout, owner]          how many of those floors each owner takes
    Y[sector, area, owner]    how many apartments of each size go to each sector and owner

Objective
    maximise total development profit

The link between floors and apartments is what makes this a single model rather
than two: choosing a layout fixes the mix of apartment sizes available, and every
apartment of a given size must be assigned to exactly one sector and one owner.
"""

from __future__ import annotations

import pyomo.environ as pyo

from .instance import Instance


def build_model(data: Instance) -> pyo.ConcreteModel:
    m = pyo.ConcreteModel("MixedTenureTower")

    m.SECTORS = pyo.Set(initialize=data.sectors)
    m.AREAS = pyo.Set(initialize=data.areas)
    m.OWNERS = pyo.Set(initialize=data.owners)
    m.LAYOUTS = pyo.Set(initialize=data.layouts)

    m.floors = pyo.Param(initialize=data.floors)
    m.per_floor = pyo.Param(
        m.AREAS, m.LAYOUTS,
        initialize=lambda m, a, v: data.apartments_per_floor[v][a],
        within=pyo.NonNegativeIntegers,
    )
    m.profit = pyo.Param(
        m.SECTORS, m.AREAS, m.OWNERS,
        initialize=lambda m, s, a, h: data.profit[s][a][h],
        within=pyo.Reals,
    )

    m.X = pyo.Var(m.LAYOUTS, within=pyo.NonNegativeIntegers)
    m.W = pyo.Var(m.LAYOUTS, m.OWNERS, within=pyo.NonNegativeIntegers)
    m.Y = pyo.Var(m.SECTORS, m.AREAS, m.OWNERS, within=pyo.NonNegativeIntegers)

    m.total_apartments = pyo.Expression(
        expr=sum(m.Y[s, a, h] for s in m.SECTORS for a in m.AREAS for h in m.OWNERS)
    )

    @m.Objective(sense=pyo.maximize)
    def total_profit(m):
        return sum(m.profit[s, a, h] * m.Y[s, a, h] for s in m.SECTORS for a in m.AREAS for h in m.OWNERS)

    @m.Constraint()
    def floors_built(m):
        """Every floor of the tower gets exactly one layout."""
        return sum(m.X[v] for v in m.LAYOUTS) == m.floors

    @m.Constraint(m.AREAS)
    def apartment_balance(m, a):
        """Apartments assigned of each size equal the apartments the layouts produce."""
        return sum(m.per_floor[a, v] * m.X[v] for v in m.LAYOUTS) == sum(
            m.Y[s, a, h] for s in m.SECTORS for h in m.OWNERS
        )

    @m.Constraint(m.LAYOUTS)
    def floor_ownership(m, v):
        """Each built floor is owned by exactly one party."""
        return sum(m.W[v, h] for h in m.OWNERS) == m.X[v]

    @m.Constraint(m.AREAS, m.OWNERS)
    def ownership_consistency(m, a, h):
        """An owner's apartments of a size follow from the floors that owner holds.

        Without this the model could hand an owner the profitable apartments while
        someone else owned the floor they sit on.
        """
        return sum(m.W[v, h] * m.per_floor[a, v] for v in m.LAYOUTS) == sum(
            m.Y[s, a, h] for s in m.SECTORS
        )

    @m.Constraint(m.SECTORS)
    def sector_minimum_share(m, s):
        """Planning obligation: a minimum share of apartments per tenure sector."""
        share = data.min_sector_share.get(s, 0.0)
        if share <= 0:
            return pyo.Constraint.Skip
        return sum(m.Y[s, a, h] for a in m.AREAS for h in m.OWNERS) >= share * m.total_apartments

    @m.Constraint(m.SECTORS)
    def sector_average_area(m, s):
        """Regulated sectors may not be met with only the smallest apartments."""
        minimum = data.min_average_area.get(s, 0.0)
        if minimum <= 0:
            return pyo.Constraint.Skip
        delivered = sum(a * sum(m.Y[s, a, h] for h in m.OWNERS) for a in m.AREAS)
        return delivered >= minimum * sum(m.Y[s, a, h] for a in m.AREAS for h in m.OWNERS)

    @m.Constraint(m.SECTORS, m.AREAS, m.OWNERS)
    def owner_area_limits(m, s, a, h):
        """Some owners may only hold apartments above a given size in a given sector."""
        if a < data.min_area_by_owner.get(s, {}).get(h, 0):
            return m.Y[s, a, h] == 0
        if (s, h) in data.forbidden:
            return m.Y[s, a, h] == 0
        return pyo.Constraint.Skip

    @m.Constraint(m.OWNERS)
    def owner_minimum_share(m, h):
        """Financing condition: an owner has committed to taking at least this share."""
        share = data.min_owner_share.get(h, 0.0)
        if share <= 0:
            return pyo.Constraint.Skip
        return sum(m.Y[s, a, h] for s in m.SECTORS for a in m.AREAS) >= share * m.total_apartments

    return m
