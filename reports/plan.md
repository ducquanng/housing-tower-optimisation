# Mixed-tenure tower: optimal plan and the cost of the policy constraints

Generated 2026-09-24 by `python -m towerplan.report`. 23 floors, 4 layouts, 5 apartment sizes, 3 tenure sectors, 3 owner types. All parameters are invented; see `instance.py`.

## Optimal plan

Total profit **EUR 11.40 million** across 170 apartments.

| Layout | Floors |
| --- | --- |
| compact | 4 |
| balanced | 10 |
| spacious | 9 |
| penthouse | 0 |

| Owner | Floors |
| --- | --- |
| corporation | 4 |
| investor | 9 |
| private | 10 |

| Sector | Share of apartments | Average area (m²) | Required share |
| --- | --- | --- | --- |
| free | 20.0% | 101.6 | 0% |
| middle | 40.0% | 65.1 | 40% |
| social | 40.0% | 55.1 | 40% |

Both regulated sectors land exactly on their minimum share. That is the model saying the obligation binds: every social apartment beyond the minimum would displace a free-sector one worth more.

## What the social obligation costs

![Trade-off](figures/social_share_tradeoff.png)

| Minimum social share | Profit (EUR m) | Change vs 0% | Apartments | Status |
| --- | --- | --- | --- | --- |
| 0% | 18.13 | +0.00 | 160 | optimal |
| 10% | 16.58 | -1.55 | 160 | optimal |
| 20% | 15.01 | -3.12 | 165 | optimal |
| 30% | 13.28 | -4.85 | 160 | optimal |
| 40% | 11.40 | -6.73 | 170 | optimal |
| 50% | 9.27 | -8.86 | 170 | optimal |
| 60% | 6.85 | -11.28 | 175 | optimal |
| 70% | — | — | — | infeasible |

Read the last column before the others: past a point the obligation cannot be met at all alongside the average-area and ownership rules, and the model reports infeasible rather than returning a plan. For a planner, the useful output is the slope of the feasible part — the profit given up per percentage point of social housing — and the share at which the scheme stops being buildable.

## Limitations

- Profit per apartment is a fixed parameter. In reality it moves with the sales programme, financing cost and the timing of completion.
- One tower in isolation, with no construction cost, phasing or planning risk.
- Integer floors and apartments, so there is no partial-floor compromise; that is realistic here and is what makes the problem combinatorial.