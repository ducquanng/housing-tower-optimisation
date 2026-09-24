"""The data a tower plan needs, and a generator for a realistic example.

Nothing here is real project data. The structure mirrors a university case study:
a developer picks how many floors to build in each layout, who owns them, and which
tenure sector each finished apartment is sold or let into, subject to the policy
constraints a municipality attaches to planning permission.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Tenure sectors: regulated social rent, mid-market rent, and open market.
SECTORS = ("social", "middle", "free")
# Who holds the floor: a housing corporation, an institutional investor, a private buyer.
OWNERS = ("corporation", "investor", "private")
# Apartment sizes in square metres.
AREAS = (45, 60, 75, 95, 120)
# Floor layouts, each a different mix of apartment sizes.
LAYOUTS = ("compact", "balanced", "spacious", "penthouse")


@dataclass
class Instance:
    """Every set, parameter and policy limit the model reads."""

    floors: int = 23
    sectors: tuple[str, ...] = SECTORS
    owners: tuple[str, ...] = OWNERS
    areas: tuple[int, ...] = AREAS
    layouts: tuple[str, ...] = LAYOUTS

    # apartments_per_floor[layout][area] -> count of that size on one floor of that layout
    apartments_per_floor: dict[str, dict[int, int]] = field(default_factory=dict)
    # profit[sector][area][owner] -> euro profit per apartment
    profit: dict[str, dict[int, dict[str, float]]] = field(default_factory=dict)

    # Policy and commercial constraints
    min_sector_share: dict[str, float] = field(default_factory=dict)      # share of all apartments
    min_average_area: dict[str, float] = field(default_factory=dict)      # m2, per sector
    min_area_by_owner: dict[str, dict[str, int]] = field(default_factory=dict)  # sector x owner floor
    min_owner_share: dict[str, float] = field(default_factory=dict)       # share of all apartments
    forbidden: tuple[tuple[str, str], ...] = (("free", "corporation"),)   # (sector, owner) pairs

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2, default=str))


def example_instance() -> Instance:
    """A 23-floor tower with four layouts and the usual mixed-tenure obligations."""
    apartments_per_floor = {
        "compact":   {45: 6, 60: 3, 75: 0, 95: 0, 120: 0},
        "balanced":  {45: 2, 60: 3, 75: 2, 95: 1, 120: 0},
        "spacious":  {45: 0, 60: 1, 75: 2, 95: 2, 120: 1},
        "penthouse": {45: 0, 60: 0, 75: 0, 95: 2, 120: 2},
    }
    # Profit rises with size and is highest in the free sector; social rent is capped
    # and barely breaks even on large apartments.
    base = {"social": 22_000.0, "middle": 46_000.0, "free": 88_000.0}
    slope = {"social": 120.0, "middle": 520.0, "free": 1_450.0}
    owner_factor = {"corporation": 0.92, "investor": 1.00, "private": 1.06}
    profit = {
        sector: {
            area: {
                owner: round(base[sector] + slope[sector] * (area - 45)) * owner_factor[owner]
                for owner in OWNERS
            }
            for area in AREAS
        }
        for sector in SECTORS
    }
    return Instance(
        apartments_per_floor=apartments_per_floor,
        profit=profit,
        min_sector_share={"social": 0.40, "middle": 0.40, "free": 0.0},
        min_average_area={"social": 55.0, "middle": 60.0, "free": 0.0},
        # Social and mid-market apartments must sit below the given floor area limits
        # for a given owner; an investor cannot hold small social units at all.
        min_area_by_owner={
            "social": {"corporation": 45, "investor": 95, "private": 60},
            "middle": {"corporation": 45, "investor": 60, "private": 45},
            "free": {"corporation": 45, "investor": 45, "private": 45},
        },
        min_owner_share={"corporation": 0.0, "investor": 0.30, "private": 0.0},
    )
