# NFL Projection Model (2026 season)

Weekly win-probability and season projection model for the 2026 NFL regular season, built on
ANY/A Value ratings. The code lives in the `projections/` package (`constants`, `data`, `ratings`, `game_model`, `simulate`, `output`, `run`); the original single script was split into it with identical results. `output.py` builds and validates the weekly JSON and `run.py` is the command line.

## Quick start

```bash
pip install -r projections/requirements.txt
python3 -m projections.run --season 2026 \
  --out frontend/public/data/projections.json \
  --snapshots projections/snapshots \
  --starters projections/starters.json
```

- `--starters` is a committed JSON file of QB overrides, e.g. `{"BAL": "J.Fagnano"}`.
- `--data-dir DIR` sets where the nflverse downloads go (default: a new temp directory outside the repo). `--no-download` reuses the files already in `--data-dir` and requires it.
- Validation runs before anything is written: 32 teams, probabilities in 0-1, every completed game present in play-by-play, no non-finite numbers, and `through_week` not lower than the published file's. On failure the command exits nonzero and leaves the output and snapshot untouched.
- The output is rewritten only when something other than `generated_at` changed. The snapshot (`{season}-through-wk{NN}.json`) for `through_week` is written when the output changes or the snapshot is missing, and isn't overwritten once any game after `through_week` has been played, so a no-op rerun leaves the repo clean. `through_week` is the last week in which every scheduled game has a result. The last line reads `OK: through week N, M games remaining, changed=True/False`.
- Unknown-starter warnings are printed and also stored in the JSON's `warnings`.

### Completed games

`games` holds only unplayed games. Every completed game is in `completed`, where its pre-game prediction is kept next to the actual result. The page shows these games in their week and adds a scorecard comparing the model with the closing market. Each entry has:

- The same prediction fields as a `games` entry, plus `home_starter`, `away_starter`, `source` and `predicted_at`. These are **frozen**: they are set the first time a game shows up as completed and are never recomputed. `validate` fails if a run would change them.
- `final`: `home_score`, `away_score`, `result` (home margin), `close_mkt_home` (vig removed) and `close_spread` (positive favors home). These are refreshed from `games.csv` on every run, so nflverse score corrections still come through.

Where the frozen prediction comes from, in order:

1. The published file's `completed`, carried forward verbatim.
2. The published file's `games`, giving the last prediction published before the game (`source: "published"`, `predicted_at` = that file's `generated_at`).
3. The latest snapshot in `--snapshots` that lists the game, also `published`.
4. Otherwise a walk-forward **backfill** (`source: "backfill"`, `predicted_at: null`). It uses ratings built only from games in earlier weeks, default starters and no overrides, the same method as `backtest.walk_forward_rows`.

The site started publishing on Nov 3, 2026, so Weeks 1–8 of 2026 are backfilled. Week 1 has no earlier games and is home field only. The backfill uses constants fit on 2022–2026 data that includes these games, so it slightly flatters the model.
- A run takes about 12 seconds; almost all of that is the Monte Carlo.

### Annual season bump

The workflow in `.github/workflows/projections.yml` hardcodes `--season 2026`. Change it each year (and the season in this README's commands) before the new season starts, or the weekly job keeps rebuilding last season.

## Data sources

Both are downloaded fresh on every run, and nothing else is needed.
- **Play-by-play:** `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet`
- **Schedule, results and betting lines:** `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv`
  - `location == 'Neutral'` marks international and other neutral-site games.
  - `away_moneyline` and `home_moneyline` give the market odds; the margin is removed before comparing.

nflverse updates play-by-play overnight. Monday night games are usually in by Tuesday morning.
Check the `through week N` figure in the run's final `OK:` line before trusting a run.

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
   - Margin = `slope` × (home matchup − away matchup) + `hfa` home field (0 at neutral sites), using the constants below.
5. **Rushing tiebreaker**
   - Applies only when |margin| < 3 points.
   - Uses opponent-adjusted rushing EPA per play: a ridge regression of play EPA on offense and defense team dummies, with λ = 50.
   - Edge = 25 carries × ((home rush offense − away run defense) − (away rush offense − home run defense)).
   - Nudge = 0.5 × edge, capped at ±1 point.
6. **Win probability:** Φ(margin ÷ `sig`).
7. **Monte Carlo**
   - 20,000 seasons, seed 7. Completed games use actual results.
   - Tiebreakers: win %, then head-to-head among tied teams, then division record (division ties only), then conference record, then random.
   - Seeds and playoff spots: 4 division winners plus 3 wild cards per conference.

## Formula and constants

The model is a season-total formula. Ratings are opponent-adjusted ANY/A value (plus the starting-QB adjustment), summed over the games played so far, then regressed by `reg`:

```
matchup(x) = k × tanh(x / k)
margin     = slope × (matchup(home off − away def) − matchup(away off − home def)) + hfa   (hfa = 0 at neutral sites)
             + rush nudge when |margin| < rush_window
P(home win) = Φ(margin / sig)
```

All constants live in `projections/constants.py` as `PARAMS` (a `Params` instance), with the version in `MODEL_VERSION`. The current version is `2026.1`.

| `Params` field | Value | Meaning | Source |
|---|---|---|---|
| `reg` | 0.8 | Shrink ratings 20% toward zero | Held from the 2026 Weeks 6-8 calibration |
| `k` | 800 | tanh curve scale | Held from the 2026 Weeks 6-8 calibration |
| `slope` | 0.00906 | Points per rating unit | Refit on 2022-2026 |
| `hfa` | 2.11 | Home-field points | Refit on 2022-2026 |
| `sig` | 13.06 | SD of actual margin around projected | Refit on 2022-2026 |
| `qb_k`, `qb_prior` | 150, −1.5 | QB shrinkage weight (dropbacks) and prior (ANY/A vs league) | 2026 Weeks 6-8 calibration, not refit |
| `rush_window`, `rush_pts`, `rush_cap`, `rushes` | 3.0, 0.5, 1.0, 25 | Tiebreaker window, points per EPA, cap, carries | 2026 Weeks 6-8 calibration, not refit |

`slope`, `hfa` and `sig` were refit once, on all 1,208 completed games from 2022 through 2026, with `k` and `reg` held fixed. Before this they were 0.0150, 1.7 and 11.0.

## Backtest

The full report is [docs/projections/backtest-2026-11.md](../docs/projections/backtest-2026-11.md). It scores a walk-forward backtest over 2022-2025 (2026 as a forward check), where every prediction uses only games from strictly earlier weeks. Log loss over 2022-2025 (lower is better):

| Version | Log loss |
|---|---:|
| Constants in use before the refit (0.0150, 1.7, 11.0) | 0.683 |
| Same formula, `slope`, `hfa`, `sig` refit leave-one-season-out (adopted) | 0.655 |
| Per-dropback formula (rejected) | 0.662 |

The per-dropback formula was rejected because it was worse in Weeks 1-6, level afterward, and showed no measured gain over the refit season-total formula.

The report was generated by code that is no longer in the tree. It is at commit `27ebf92`, and the report is kept as the historical record and is not regenerated. `projections/backtest.py` now holds only the walk-forward rows, the fit, leave-one-season-out scoring and the refit command.

The old calibration (RMSE about 10.9 with 27 of 41 winners on 2026 Weeks 6-8) used look-ahead ratings that included the games being scored. It is not a forecast figure. Honest walk-forward on those weeks, with the pre-refit constants, gave RMSE 12.63, against 12.92 for predicting a margin of 0. Walk-forward leave-one-season-out on the refit formula over 2022-2026 gives RMSE 13.06 and 59.8% winners.

Other findings that still hold: rushing EPA carries over poorly week to week (run defense split-half correlation about −0.24), so it is used only as a capped tiebreaker. Shrinking defense harder than offense made the fit worse, so both units use the same `reg`. Do not tune constants to match betting lines: the market is kept as a comparison, never an input.

### Known limits

- Ratings still grow with games played, and teams with more games get larger values. The backtest found no measured cost to this.
- Early-season opponent adjustment is unstable: the 50-iteration loop does not settle on sparse schedules, so early-week ratings can be large.
- `qb_k`, `qb_prior` and the rush constants were not refit.
- `k` and `reg` were held at their 2026 Weeks 6-8 values, not searched.

### Refitting

A refit is manual, and weekly runs never refit.
1. Run `python3 -m projections.backtest --refit` (add `--data-dir DIR` to reuse downloaded data; keep it outside the repo). It prints `slope`, `hfa` and `sig` for all completed games.
2. Paste the values into `PARAMS` in `projections/constants.py`.
3. Bump `MODEL_VERSION`.
4. Rerun `pytest tests/projections`. `tests/projections/test_constants.py` fails if a refit lands outside the expected ranges, which is a signal to investigate rather than widen them.

## Weekly workflow

- `.github/workflows/projections.yml` runs Tuesdays at 11:30 and 15:30 UTC, on a push to `projections/starters.json` on `main`, and on manual dispatch. A read-only `build` job runs tests and the model; a `publish` job commits only `frontend/public/data/projections.json` and `projections/snapshots/` if they changed. A failed run leaves the last good file live, and GitHub's failed-run email is the alert. Vercel redeploys on each commit.
- The cloud routine "Weekly NFL QB check and summary" (https://claude.ai/code/routines/trig_01U9cRtcJn41vnwH3KqNNTuz), Tuesdays at 13:23 UTC (8:23 AM Eastern during standard time), checks QB news, edits `projections/starters.json` when needed, and sends a summary linking to https://nfl-qb-personnel-analysis.vercel.app/projections. It runs the repo's code and has no copy of the model. Starter overrides belong in `projections/starters.json`.
- The older "Weekly NFL model update" task and its Claude Doc are still running during the transition. They use the old constants, so their numbers won't match the page. They'll be retired after the new routine's first good run.

QB override notes as of Nov 3, 2026:
- `BAL`: J.Fagnano. Jackson is on injured reserve with a thumb injury, and Huntley is out with a toe injury. Restore `L.Jackson` when he returns.
- These starters are correct by default, but watch them: `CHI` C.Williams (returned Week 6 from a hamstring injury), `NYG` J.McCarthy (named starter), `PHI` T.McKee (Hurts on injured reserve with a blood clot).

## Owner preferences

- The page is league-wide, with filters by conference, division and team. The user (Caleb) mostly follows the **NFC North** (Vikings, Packers, Lions, Bears), and the Tuesday summary covers that race.
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
