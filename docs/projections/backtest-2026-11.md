# Model backtest

Walk-forward backtest over 2022, 2023, 2024, 2025, with 2026 as a forward check. Every prediction uses only games from strictly earlier weeks of the same season, including the rule that the starter is the QB who threw most in the team's previous game. Week 1 ratings are all zero, so Week 1 margins are home-field advantage alone. Betting lines are not used anywhere.

## Versions

- **Version A**: today's model with its current constants. Those constants were calibrated on 2026 Weeks 6-8, so only A's constants are in-sample on those weeks. Its ratings are walk-forward. Nothing is fit here.
- **Version B**: today's formula, with SLOPE, HFA and SIG refit at K=800, REG=0.8, scored leave-one-season-out.
- **Version C**: the per-dropback formula, with K, REG or shrinkage chosen by lowest training log loss and SLOPE, HFA and SIG refit, scored leave-one-season-out.

Forward-check constants for B and C are fit on all training seasons and never see 2026. QB_K, QB_PRIOR and the rush constants are held at their current values in every version. Version B's K and REG are fixed at values from the 2026 Weeks 6-8 calibration.

## Data

| Season | Completed games | Ties | Last week |
|---|---:|---:|---:|
| 2022 | 271 | 2 | 18 |
| 2023 | 272 | 0 | 18 |
| 2024 | 272 | 0 | 18 |
| 2025 | 272 | 1 | 18 |
| 2026 | 121 | 1 | 8 |

DB_PER_GAME: computed 35.39 dropbacks per team-game over 2022, 2023, 2024, 2025, which rounds to 35. The constant is 35.

## Results: leave-one-season-out, 2022, 2023, 2024, 2025

Version A uses its fixed constants on the same games.

| Version | Split | Games | RMSE | Log loss | Winners % |
|---|---|---:|---:|---:|---:|
| A | All | 1087 | 13.39 | 0.6830 | 59.6 |
| A | Early (Weeks 1-6) | 372 | 13.87 | 0.7095 | 52.4 |
| A | Mid (Weeks 7-12) | 345 | 12.67 | 0.6585 | 62.9 |
| A | Late (Weeks 13-18) | 370 | 13.55 | 0.6792 | 63.7 |
| B | All | 1087 | 13.07 | 0.6547 | 60.3 |
| B | Early (Weeks 1-6) | 372 | 13.72 | 0.6934 | 52.2 |
| B | Mid (Weeks 7-12) | 345 | 12.48 | 0.6379 | 64.3 |
| B | Late (Weeks 13-18) | 370 | 12.95 | 0.6316 | 64.8 |
| C | All | 1087 | 13.17 | 0.6618 | 59.7 |
| C | Early (Weeks 1-6) | 372 | 14.02 | 0.7130 | 50.8 |
| C | Mid (Weeks 7-12) | 345 | 12.49 | 0.6407 | 64.6 |
| C | Late (Weeks 13-18) | 370 | 12.92 | 0.6303 | 64.0 |

### By held-out season

| Version | Season | Games | RMSE | Log loss | Winners % |
|---|---|---:|---:|---:|---:|
| A | 2022 | 271 | 12.36 | 0.6861 | 58.4 |
| A | 2023 | 272 | 14.32 | 0.7078 | 54.8 |
| A | 2024 | 272 | 13.38 | 0.6464 | 64.9 |
| A | 2025 | 272 | 13.42 | 0.6917 | 60.3 |
| B | 2022 | 271 | 11.89 | 0.6582 | 60.2 |
| B | 2023 | 272 | 13.89 | 0.6676 | 57.0 |
| B | 2024 | 272 | 13.23 | 0.6342 | 64.5 |
| B | 2025 | 272 | 13.20 | 0.6587 | 59.6 |
| C | 2022 | 271 | 11.91 | 0.6635 | 61.0 |
| C | 2023 | 272 | 14.07 | 0.6815 | 55.1 |
| C | 2024 | 272 | 13.39 | 0.6434 | 63.4 |
| C | 2025 | 272 | 13.24 | 0.6589 | 59.2 |

### Early season by week

| Version | Week | Games | RMSE | Log loss | Winners % |
|---|---|---:|---:|---:|---:|
| A | 1 | 64 | 12.86 | 0.7025 | 49.2 |
| A | 2 | 64 | 12.76 | 0.7001 | 51.6 |
| A | 3 | 64 | 15.99 | 0.7275 | 53.1 |
| A | 4 | 64 | 15.09 | 0.7610 | 42.9 |
| A | 5 | 58 | 14.46 | 0.7435 | 50.0 |
| A | 6 | 58 | 11.35 | 0.6180 | 69.0 |
| B | 1 | 64 | 12.90 | 0.7030 | 49.2 |
| B | 2 | 64 | 12.77 | 0.7041 | 50.0 |
| B | 3 | 64 | 15.93 | 0.6957 | 56.2 |
| B | 4 | 64 | 14.33 | 0.7093 | 47.6 |
| B | 5 | 58 | 14.22 | 0.7081 | 50.0 |
| B | 6 | 58 | 11.62 | 0.6367 | 60.3 |
| C | 1 | 64 | 12.91 | 0.7031 | 49.2 |
| C | 2 | 64 | 12.81 | 0.7071 | 46.9 |
| C | 3 | 64 | 16.56 | 0.7610 | 54.7 |
| C | 4 | 64 | 14.93 | 0.7405 | 41.3 |
| C | 5 | 58 | 14.52 | 0.7249 | 51.7 |
| C | 6 | 58 | 11.65 | 0.6356 | 62.1 |

## Forward check: 2026

Constants fit on 2022, 2023, 2024, 2025 only. Version A's constants were fit on 2026 Weeks 6-8, but its ratings are walk-forward.

2026 has no late-season games, so this check cannot test late-season behavior.

| Version | Split | Games | RMSE | Log loss | Winners % |
|---|---|---:|---:|---:|---:|
| A | All | 121 | 13.13 | 0.6833 | 58.8 |
| A | Early (Weeks 1-6) | 93 | 12.70 | 0.6843 | 58.2 |
| A | Mid (Weeks 7-12) | 28 | 14.49 | 0.6802 | 60.7 |
| A | Late (Weeks 13-18) | 0 | no games | no games | no games |
| B | All | 121 | 12.98 | 0.6792 | 55.4 |
| B | Early (Weeks 1-6) | 93 | 12.56 | 0.6840 | 52.7 |
| B | Mid (Weeks 7-12) | 28 | 14.29 | 0.6634 | 64.3 |
| B | Late (Weeks 13-18) | 0 | no games | no games | no games |
| C | All | 121 | 13.03 | 0.6735 | 57.9 |
| C | Early (Weeks 1-6) | 93 | 12.60 | 0.6764 | 56.0 |
| C | Mid (Weeks 7-12) | 28 | 14.34 | 0.6637 | 64.3 |
| C | Late (Weeks 13-18) | 0 | no games | no games | no games |

### Version A on 2026 Weeks 6-8 (constants fit here, ratings walk-forward)

| Version | Split | Games | RMSE | Log loss | Winners % |
|---|---|---:|---:|---:|---:|
| A | Weeks 6-8 | 42 | 12.63 | 0.6867 | 59.5 |

The previously documented figure for A, RMSE about 10.9 with 27 of 41 winners, used ratings that included the games being scored (look-ahead). Reproduced on 42 games, ratings through Week 8 give RMSE 10.78 and 27 of 42 winners (measured on this data on 2026-11-03, not recomputed by this script). The walk-forward row above is the honest comparison, and predicting a margin of 0 gives RMSE 12.92.

## Calibration: 2022, 2023, 2024, 2025

Ties are excluded. Bins are by predicted home-win probability.

| Version | Predicted home win | Games | Mean predicted | Actual |
|---|---|---:|---:|---:|
| A | 0.0-0.2 | 92 | 0.134 | 0.348 |
| A | 0.2-0.4 | 196 | 0.308 | 0.423 |
| A | 0.4-0.6 | 334 | 0.513 | 0.512 |
| A | 0.6-0.8 | 304 | 0.689 | 0.615 |
| A | 0.8-1.0 | 158 | 0.879 | 0.759 |
| B | 0.0-0.2 | 2 | 0.181 | 0.000 |
| B | 0.2-0.4 | 146 | 0.341 | 0.384 |
| B | 0.4-0.6 | 510 | 0.519 | 0.496 |
| B | 0.6-0.8 | 396 | 0.675 | 0.657 |
| B | 0.8-1.0 | 30 | 0.832 | 0.800 |
| C | 0.0-0.2 | 1 | 0.186 | 1.000 |
| C | 0.2-0.4 | 135 | 0.346 | 0.363 |
| C | 0.4-0.6 | 525 | 0.518 | 0.493 |
| C | 0.6-0.8 | 401 | 0.673 | 0.668 |
| C | 0.8-1.0 | 22 | 0.844 | 0.727 |

## Calibration: 2026

| Version | Predicted home win | Games | Mean predicted | Actual |
|---|---|---:|---:|---:|
| A | 0.0-0.2 | 1 | 0.195 | 0.000 |
| A | 0.2-0.4 | 14 | 0.321 | 0.286 |
| A | 0.4-0.6 | 60 | 0.517 | 0.500 |
| A | 0.6-0.8 | 37 | 0.675 | 0.622 |
| A | 0.8-1.0 | 8 | 0.864 | 0.625 |
| B | 0.0-0.2 | 0 | - | - |
| B | 0.2-0.4 | 4 | 0.379 | 0.250 |
| B | 0.4-0.6 | 76 | 0.534 | 0.474 |
| B | 0.6-0.8 | 40 | 0.655 | 0.625 |
| B | 0.8-1.0 | 0 | - | - |
| C | 0.0-0.2 | 0 | - | - |
| C | 0.2-0.4 | 4 | 0.324 | 0.250 |
| C | 0.4-0.6 | 76 | 0.533 | 0.461 |
| C | 0.6-0.8 | 40 | 0.665 | 0.650 |
| C | 0.8-1.0 | 0 | - | - |

## Chosen constants

Version A: Params(reg=0.8, k=800.0, slope=0.015, hfa=1.7, sig=11.0, qb_k=150, qb_prior=-1.5, rush_window=3.0, rush_pts=0.5, rush_cap=1.0, rushes=25)

| Version | Fit on | K | Weighting | SLOPE | HFA | SIG |
|---|---|---:|---|---:|---:|---:|
| B | all but 2022 | 800 | flat REG=0.8 | 0.00969 | 2.240 | 13.445 |
| B | all but 2023 | 800 | flat REG=0.8 | 0.00954 | 2.100 | 12.785 |
| B | all but 2024 | 800 | flat REG=0.8 | 0.00853 | 2.416 | 13.015 |
| B | all but 2025 | 800 | flat REG=0.8 | 0.00883 | 2.233 | 13.021 |
| B | 2022, 2023, 2024, 2025 | 800 | flat REG=0.8 | 0.00916 | 2.247 | 13.070 |
| C | all but 2022 | 150 | shrinkage s=400 | 0.12893 | 2.225 | 13.506 |
| C | all but 2023 | 50 | shrinkage s=100 | 0.10441 | 2.152 | 12.860 |
| C | all but 2024 | 400 | shrinkage s=400 | 0.11620 | 2.421 | 13.031 |
| C | all but 2025 | 400 | shrinkage s=400 | 0.11363 | 2.226 | 13.085 |
| C | 2022, 2023, 2024, 2025 | 100 | shrinkage s=400 | 0.12681 | 2.245 | 13.123 |

Flat vs. shrinkage for Version C: flat REG won 0 of 5 fits, shrinkage won 5. Version B is fixed at flat K=800 and REG=0.8 while C searches a grid, so this line compares weightings within C only and does not show that shrinkage beats flat weighting for today's formula. The chosen K also varied widely by fold, from 50 to 400.

## Limits

- QB_K, QB_PRIOR and the rush constants date from the 2026 Weeks 6-8 calibration, so they are not independent of the 2026 forward check. Version B's fixed K=800 and REG=0.8 come from the same calibration, which could favor B slightly in the forward check.
- Scoring rules: ties count in RMSE only. A zero margin gets half credit for winners. The Games column includes ties, while Winners % and Log loss exclude them.
- The direct solve for Version C was adopted after the 2022-2025 by-week results had been seen, and the change did not improve C.
- DB_PER_GAME is computed over all of 2022, 2023, 2024, 2025, including each held-out season. It is one rounded scale factor that SLOPE rescales against, so the effect is small.
- Version C uses a direct solve of the opponent adjustment because the original 50-iteration loop does not converge on sparse early-season schedules. Versions A and B keep the loop as-is, as it is part of today's formula. The two methods agree once the schedule is connected and the loop has settled, to within 1e-6 from about Week 8 on 2022-2025 data.
- The direct solve changes early values but does not make them reliable. After one game each it splits a gap evenly between offense and defense. The loop keeps the full gap in both units, so on one pairing with a raw +10/+10 the loop gives +10/+10 and the solve gives +5/+5, and the loop counts the gap twice in offense minus defense. Week 3 ratings can still be large, because two weeks of games leave long cycles that barely separate offense from defense. See the by-week table.
- With flat weights, K and REG only act through K/REG once SLOPE is refit, so grid pairs with the same ratio predict identically. The first such pair in the grid is reported.
