from dataclasses import replace

import pytest

from towerplan.instance import example_instance
from towerplan.solve import solve


@pytest.fixture(scope="module")
def small():
    """A shorter tower keeps the suite fast while exercising every constraint."""
    return replace(example_instance(), floors=8)


@pytest.fixture(scope="module")
def solution(small):
    return solve(small)


def test_solution_is_optimal(solution):
    assert solution.feasible
    assert solution.profit > 0


def test_every_floor_is_built_to_exactly_one_layout(small, solution):
    assert sum(solution.layouts.values()) == small.floors
    assert sum(solution.floors_by_owner.values()) == small.floors


def test_apartments_match_what_the_layouts_produce(small, solution):
    for area in small.areas:
        built = sum(small.apartments_per_floor[v][area] * n for v, n in solution.layouts.items())
        assigned = sum(n for (_, a, _), n in solution.apartments.items() if a == area)
        assert built == assigned


def test_sector_minimum_shares_are_met(small, solution):
    shares = solution.sector_shares()
    for sector, required in small.min_sector_share.items():
        assert shares.get(sector, 0.0) >= required - 1e-9


def test_average_area_rules_are_met(small, solution):
    for sector, minimum in small.min_average_area.items():
        if minimum:
            assert solution.average_area(sector) >= minimum - 1e-9


def test_forbidden_sector_owner_pairs_are_empty(small, solution):
    for sector, owner in small.forbidden:
        assert not [k for k in solution.apartments if k[0] == sector and k[2] == owner]


def test_owner_area_limits_are_respected(small, solution):
    for (sector, area, owner), count in solution.apartments.items():
        assert count == 0 or area >= small.min_area_by_owner[sector][owner]


def test_raising_the_social_obligation_cannot_raise_profit(small):
    """A tighter constraint shrinks the feasible set, so the optimum cannot improve."""
    profits = []
    for share in (0.2, 0.4, 0.6):
        result = solve(replace(small, min_sector_share={**small.min_sector_share, "social": share}))
        if result.feasible:
            profits.append(result.profit)
    assert profits == sorted(profits, reverse=True)


def test_an_impossible_obligation_is_reported_as_infeasible_not_as_a_plan(small):
    impossible = replace(small, min_sector_share={"social": 0.8, "middle": 0.4, "free": 0.0})
    result = solve(impossible)
    assert not result.feasible
    assert "infeasible" in result.status
