# NFL Projection Model (2026 season)

Weekly win-probability and season projection model for the 2026 NFL regular season, built on
ANY/A Value ratings. Everything lives in one script, `nfl_pipeline.py`.

## Quick start

```bash
pip install pandas numpy pyarrow
python3 nfl_pipeline.py nfl_out                                   # default starting QBs
python3 nfl_pipeline.py nfl_out --starters '{"BAL":"J.Fagnano"}'  # with QB overrides
```

Outputs, in the output directory you pass:
- `report.md`: season outlook table (sorted by division), one table per remaining week (model vs market), and a ratings table
- `results.json`: ratings, per-game predictions and simulation results, for scripting
- `data/`: the raw downloads (`pbp.parquet`, `games.csv`), overwritten on every run

A run takes about 12 seconds; almost all of that is the Monte Carlo.

## Data sources

Both are downloaded fresh on every run, and nothing else is needed.
- **Play-by-play:** `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet`
- **Schedule, results and betting lines:** `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv`
  - `location == 'Neutral'` marks international and other neutral-site games.
  - `away_moneyline` and `home_moneyline` give the market odds; the margin is removed before comparing.

nflverse updates play-by-play overnight. Monday night games are usually in by Tuesday morning.
Check the script's `through week N` output line before trusting a run.

nflverse team codes: the Rams are `LA`, not `LAR`. Passer names look like `C.Williams`.

## Model pipeline

1. **ANY/A Value ratings**
   - ANY/A per dropback = (passing yards + 20×TD − 45×INT − sack yards) ÷ (attempts + sacks).
   - Dropbacks include spikes; two-point tries are excluded.
   - Value = (team ANY/A − league ANY/A) × dropbacks.
   - Offense uses the team's own dropbacks. Defense uses opponents' dropbacks against them, with the sign flipped so positive = good.
   - These rules reproduce the user's original ANY/A Value chart exactly (all 64 values within rounding, verified).
2. **Opponent adjustment**
   - Each unit is credited or penalized by the average rating of the units it faced.
   - This is iterated 50 times, then re-centered to zero.
   - The original chart is *not* opponent-adjusted; this step adds it.
3. **Starting-QB adjustment**
   - Each QB's per-team ANY/A per dropback is shrunk toward a prior of (league average − 1.5), with a weight of 150 dropbacks.
   - Team offense += (projected starter's rate − dropback-weighted rate of the QBs who actually played) × team dropbacks.
   - The default starter is the QB with the most dropbacks in the team's most recent game. Override it with `--starters`.
   - A QB with no 2026 dropbacks for that team gets the prior rate.
4. **Game margin**
   - Ratings are regressed: × 0.8.
   - Each side scores as matchup = 800 × tanh((offense − opposing defense) ÷ 800). The curve dampens big mismatches.
   - Margin = 0.0150 × (home matchup − away matchup) + 1.7 home field (0 at neutral sites).
5. **Rushing tiebreaker**
   - Applies only when |margin| < 3 points.
   - Uses opponent-adjusted rushing EPA per play: a ridge regression of play EPA on offense and defense team dummies, with λ = 50.
   - Edge = 25 carries × ((home rush offense − away run defense) − (away rush offense − home run defense)).
   - Nudge = 0.5 × edge, capped at ±1 point.
6. **Win probability:** Φ(margin ÷ 11).
7. **Monte Carlo**
   - 20,000 seasons, seed 7. Completed games use actual results.
   - Tiebreakers: win %, then head-to-head among tied teams, then division record (division ties only), then conference record, then random.
   - Seeds and playoff spots: 4 division winners plus 3 wild cards per conference.

## Constants and calibration

All constants sit at the top of the script.

| Constant | Value | Meaning |
|---|---|---|
| `REG` | 0.8 | Shrink ratings 20% toward zero |
| `K` | 800 | tanh curve width. A linear fit was equally good; 800 keeps some matchup logic |
| `SLOPE` | 0.0150 | Points per rating unit |
| `HFA` | 1.7 | Home-field points |
| `SIG` | 11.0 | Standard deviation of actual margin around projected |
| `QB_K`, `QB_PRIOR` | 150, −1.5 | QB shrinkage weight and prior (ANY/A vs league) |
| `RUSH_*` | 3.0 / 0.5 / 1.0 / 25 | Tiebreaker window, points per EPA, cap, carries |

Calibration history, all on 2026 Weeks 6–8 (41 games):
- **Raw ratings:** RMSE 11.4 points, against 12.8 for predicting 0.
- **Opponent adjustment:** RMSE 11.4 → 11.0.
- **QB adjustment:** RMSE about 10.9; 27 of 41 winners picked correctly.
- **Rushing EPA:** carries over poorly week to week (run defense split-half correlation ≈ −0.24), so it is used only as a capped tiebreaker. Out of sample, it correlated +0.37 with residuals in close games.
- **Separate offense/defense regression:** shrinking defense harder made the fit worse, so both units use the same `REG`.

These fits are in-sample and small. **Refit `SLOPE`, `HFA` and `SIG` every few weeks** by regressing actual margin on the matchup difference over recent games. Do not tune constants to match betting lines: the market is kept as a comparison, never an input.

## Weekly workflow

A cloud scheduled task named "Weekly NFL model update" runs Tuesdays at 8:23 AM ET. Each run:
1. runs the pipeline,
2. checks QB news (injuries, injured reserve, benchings, returns) and reruns with `--starters` overrides where needed,
3. rewrites the Claude Doc "2026 NFL Remaining Games — Model Win Probabilities" (https://claude.ai/artifact/7521qze4Y6fgLeikoec1XW): the method section stays; everything from "## Season outlook and remaining games" down is replaced with `report.md`,
4. pushes a short summary covering QB overrides, odds changes, the NFC North race, and the 3 biggest model-vs-market gaps.

The scheduled task embeds its own copy of the script. **If you change `nfl_pipeline.py` here, update the task's prompt too**, or it will keep running the old version.

QB override notes as of Nov 3, 2026:
- `BAL`: J.Fagnano. Jackson is on injured reserve with a thumb injury, and Huntley is out with a toe injury. Restore `L.Jackson` when he returns.
- These starters are correct by default, but watch them: `CHI` C.Williams (returned Week 6 from a hamstring injury), `NYG` J.McCarthy (named starter), `PHI` T.McKee (Hurts on injured reserve with a blood clot).

## Owner preferences

- The user (Caleb) mostly follows the **NFC North** (Vikings, Packers, Lions, Bears). Game-by-game detail is wanted for those four teams only; the rest of the league is shown as standings.
- Present expected wins plus division, playoff and #1-seed odds. Show margins as "Team by X.X" with a win %.
- Keep betting-market data separate, for display and comparison only.
- Prefer showing the calculation behind a surprising number (matchup components, nudges, QB adjustment) over asserting it.

## Known limitations and ideas

- The projected starter is assumed to play the rest of the season. Return dates are not modeled.
- Ratings are season-to-date with no recency weighting. Exponential decay is a possible next step.
- No injuries are modeled beyond QB.
- Ratings stay fixed within a simulated season, so simulated outcomes are a little too narrow. Each simulation could draw a rating shift per team.
- Tiebreakers skip common games and strength of victory/schedule.
- Ties are not simulated for future games.
- Playoff bracket odds (reseeding, conference title games, Super Bowl) were computed ad hoc in an earlier session. They are a good candidate for a `--playoffs` mode that takes seeds as input.
