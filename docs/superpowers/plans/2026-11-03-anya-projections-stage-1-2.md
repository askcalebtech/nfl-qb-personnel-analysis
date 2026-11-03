# ANY/A Projections (Stages 1–2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect Airflow secrets, fix and backtest the ANY/A model, and publish its weekly output to a new `/projections` page that replaces the Claude Doc.

**Architecture:** A standalone `projections/` Python package reads nflverse data and writes one validated JSON file. GitHub Actions runs it weekly and commits the JSON, Vercel redeploys, and the page reads the static file. The Tuesday cloud task only handles QB news and the push summary.

**Tech Stack:** Python 3.9, pandas 2.1, numpy 1.26, pyarrow 14, pytest; Next.js 14 App Router, TypeScript, Tailwind, vitest; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-03-anya-projections-and-production-design.md`

## Global Constraints

- Work on branch `feat/anya-projections`, never directly on `main`. Pushing and merging require Caleb's approval, except the weekly automation's narrow exception once launched.
- Betting lines must never feed the model. They are display-only.
- Raw Off/Def/Total values must not change.
- Python code must run on 3.9 (no `match`, no `X | Y` annotations).
- Model dependencies go in `projections/requirements.txt`, never `api/requirements.txt`.
- Production code carries only one formula after the sign-off gate.
- Probabilities in the JSON are 0–1. The JSON is written with `allow_nan=False`.
- Never commit secrets, `nfl_out/`, or downloaded nflverse data.
- **Task 6 is a hard stop.** Tasks 7 onward don't start until Caleb signs off on the backtest.

## Review Focus

1. **A completed game is in `games.csv` but missing from play-by-play (Monday night lag):** the run fails validation, and the last good JSON stays live. Test in Task 8.
2. **A rerun with no football changes:** only `generated_at` differs, so nothing is committed and no redeploy happens. Test in Task 8.
3. **Missing market line, spread or stadium:** values become `null`, and the page shows "—" rather than crashing. Tests in Tasks 8 and 9.
4. **A misspelled or unknown starter override:** the run still completes using the prior rate, with a visible warning in the JSON and on the page. Tests in Tasks 3 and 11.
5. **A team on bye, or no games left in the season:** the page shows a clear empty message instead of a blank section. Tests in Tasks 9 and 11.

---

### Task 1: Branch and secret protection

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1:** Run `git switch -c feat/anya-projections`.
- [ ] **Step 2:** Append `airflow/airflow.db`, `airflow/airflow.cfg`, `airflow/logs/`, `airflow/standalone_admin_password.txt`, `airflow/webserver_config.py`, `nfl_out/` and `10730.jpg` to `.gitignore`.
- [ ] **Step 3: Verify.** Run `git check-ignore airflow/airflow.db airflow/airflow.cfg airflow/logs airflow/standalone_admin_password.txt airflow/webserver_config.py nfl_out 10730.jpg`. Expected: all 7 printed. Then run `git status --short`. Expected: none of them listed.
- [ ] **Step 4: Commit** `.gitignore` and `docs/superpowers/` with message `chore: ignore local Airflow state and add projections design`.

### Task 2: Confirm the cloud task can push (first implementation check)

**Files:** none.

- [ ] **Step 1:** Load `RemoteTrigger` via ToolSearch and find "Weekly NFL model update". Record its repo sources and whether it has this repo attached.
- [ ] **Step 2:** If this repo isn't attached or push access can't be confirmed from its config, ask Caleb how he wants to grant it. Don't change the live task, and don't trigger a test run without his approval.
- [ ] **Step 3:** If write access can't be granted, **stop** and bring it to Caleb, because the starters flow depends on it. Tasks 3–6 can proceed, since they don't depend on this.

### Task 3: Refactor the model with identical results

**Files:**
- Create: `projections/__init__.py`, `constants.py`, `data.py`, `ratings.py`, `game_model.py`, `simulate.py`, `requirements.txt`, `requirements-dev.txt`
- Move: `nfl_pipeline.py` → logic split across the modules above (delete the root file after Step 6 passes)
- Move: `CLAUDE_ANY_A_MODEL.md` → `projections/README.md`
- Test: `tests/projections/test_ratings.py`, `tests/projections/test_game_model.py`

**Interfaces:**
- Produces, in `constants.py`: `TEAMS`, `NAMES`, `DIV`, `DOF`, `CONF`; frozen dataclass `Params(reg, k, slope, hfa, sig, qb_k, qb_prior, rush_window, rush_pts, rush_cap, rushes)`; `LEGACY_PARAMS = Params(0.8, 800.0, 0.0150, 1.7, 11.0, 150, -1.5, 3.0, 0.5, 1.0, 25)`.
- Produces, in `data.py`: `download(season: int, data_dir: str) -> None` (standard-library HTTP, raises on failure); `load(season: int, data_dir: str) -> tuple[DataFrame, DataFrame, DataFrame]` returning `(done, todo, pbp)`.
- Produces, in `ratings.py`:
  - `dropbacks(pbp) -> DataFrame` adding a `pts` column
  - `raw_values(db) -> Raw` with `off`, `def_`, `lg`, `off_n`, `def_n` dicts, where every team in `TEAMS` has a key (0 when no data)
  - `rush_epa(pbp) -> tuple[dict, dict]`
  - `pick_starters(db, done, overrides) -> dict` where a team with no games maps to its override or `None`
  - `RatingSet` dataclass: `off_pred`, `def_pred`, `off_season`, `def_season`, `qb_adj_season`, `qb_adj_pred`, `starter`, `warnings: list[str]`, `ro`, `rd`
  - `build_ratings_legacy(done, pbp, overrides, params) -> RatingSet`, where `off_pred = adjusted × params.reg` and `off_season` is the unregressed adjusted value
- Produces, in `game_model.py`: `predict(away, home, neutral, rs: RatingSet, params) -> Prediction`, with fields `margin`, `p_home`, `nudge`, `home_matchup`, `away_matchup`, `matchup_points`, `hfa`. `predict` applies no regression of its own.
- Produces, in `simulate.py`: `simulate(done, games, n_sims=20000, seed=7) -> dict` with `avg_wins`, `p10`, `p90`, `div`, `playoffs`, `seed1` per team, keeping the original draw order.

- [ ] **Step 1: Capture the baseline before changing anything.** Install with `pip install --break-system-packages pandas numpy pyarrow`, then run the original script with the output directory set to the session scratchpad's `baseline/`. Expected: `OK: through week N`. Record N. Keep `baseline/results.json` and `baseline/data/`.
- [ ] **Step 2: Write failing tests.**

```python
def test_points_formula():          # 10-yd TD = 30; INT = -45; 7-yd sack = -7
def test_two_point_tries_excluded():
def test_spikes_count_as_dropbacks():
def test_raw_values_sum_to_zero():  # sum(off.values()) and sum(def_.values()) ≈ 0
def test_team_with_no_games_gets_zero_rating_and_no_crash():
def test_unknown_starter_override_uses_prior_and_adds_warning():
    assert any("Z.Nobody" in w for w in rs.warnings)

def test_legacy_margin_known_value():
    # off_pred[home]=80, all else 0, zero rush
    p = predict("A", "H", False, rs, LEGACY_PARAMS)
    assert p.margin == approx(2.896, abs=1e-3)
    assert p.p_home == approx(0.6038, abs=1e-3)
def test_neutral_site_removes_hfa():
def test_rush_nudge_capped_at_one_point():
def test_rush_nudge_ignored_outside_three_point_window():
def test_margin_is_sum_of_components():
    assert p.margin == approx(p.matchup_points + p.hfa + p.nudge)
```

- [ ] **Step 3:** Run `pytest tests/projections -v`. Expected: FAIL on import.
- [ ] **Step 4:** Implement the modules by moving existing logic with no formula changes. Add the no-games and unknown-starter handling. Importing any module must do no work.
- [ ] **Step 5:** Run `pytest tests/projections -v`. Expected: PASS.
- [ ] **Step 6: Prove equivalence.** On the Step 1 data, compare new against `baseline/results.json`. Expected: `off` and `def_` exactly equal, and `adj_off`, `adj_def`, `margin`, `p_home`, and all sim odds within 1e-9. Any difference is a bug.
- [ ] **Step 7:** Delete root `nfl_pipeline.py`, update paths in `projections/README.md`, and commit with message `refactor: split ANY/A model into tested projections package`.

### Task 4: Add the per-dropback ratings

**Files:**
- Modify: `projections/ratings.py`, `projections/constants.py`
- Test: `tests/projections/test_rate_ratings.py`

**Interfaces:**
- Consumes: `Raw`, `RatingSet`, `Params` from Task 3.
- Produces: `DB_PER_GAME: int` in `constants.py` (temporary 36, replaced in Task 5); `build_ratings_rate(done, pbp, overrides, params, shrink_s: Optional[float]) -> RatingSet`.

**Method:**
- `off_rate = team mean pts − lg`; `def_rate = lg − mean pts allowed`.
- Opponent-adjust rates with the same 50-iteration, re-centered loop as the legacy version.
- QB adjustment in rate terms: `starter rate − dropback-weighted QB mix`, added to adjusted offense.
- Prediction rating: `rate × DB_PER_GAME × w`. Weight `w` is `params.reg` when `shrink_s` is `None`, or `n / (n + shrink_s)` otherwise, where `n` is that unit's dropbacks.
- Published season values: `rate × that team's dropbacks`, so `off_season` is comparable with raw values.

- [ ] **Step 1: Write failing tests.**

```python
def test_same_rate_different_game_counts_same_prediction_rating():
    # Teams with 7 and 8 games at identical per-dropback rates
    assert rs.off_pred["A"] == approx(rs.off_pred["B"])
def test_prediction_rating_does_not_grow_with_season_length():
def test_season_values_scale_with_dropbacks():
    assert rs.off_season["A"] == approx(rate_a * dropbacks_a)
def test_raw_values_unchanged_by_rate_build():
def test_week_one_all_ratings_zero_margin_is_hfa():
def test_shrink_weight_rises_with_dropbacks():
```

- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement `build_ratings_rate`.
- [ ] **Step 4:** Run `pytest tests/projections -v`. Expected: PASS.
- [ ] **Step 5: Commit** with message `feat: add per-dropback model ratings`.

### Task 5: Build the backtest

**Files:**
- Create: `projections/backtest.py`
- Test: `tests/projections/test_backtest.py`

**Interfaces:**
- Consumes: `build_ratings_legacy`, `build_ratings_rate`, `predict`, `data.download/load`.
- Produces:
  - `walk_forward_rows(season, data_dir, formula: str) -> DataFrame`, with one row per completed game using only data from earlier weeks, including `season`, `week`, `away`, `home`, `neutral`, `result`, unshrunk ratings, each unit's dropbacks and the rush edge
  - `fit_params(rows, formula) -> tuple[Params, Optional[float]]`
  - `evaluate(rows, params, shrink_s) -> DataFrame`
  - `score(preds) -> dict` with `n`, `rmse`, `log_loss`, `winners_pct`, and 5-bin calibration
  - `main()`, which writes the report

**Method:**
- Legacy fit: hold `K=800`, `REG=0.8`. Regress margin on matchup difference plus a non-neutral HFA term to get `SLOPE` and `HFA`. `SIG` is the residual SD.
- Rate fit: same regression, across a grid of `K ∈ {50, 75, 100, 150, 200, 400}`, flat `REG ∈ {0.6, 0.7, 0.8, 0.9, 1.0}`, and `shrink_s ∈ {50, 100, 200, 400}`. Choose the lowest log loss within the training seasons. Record whether flat or shrinkage won.
- Hold `QB_K`, `QB_PRIOR` and the rush constants fixed. They can be revisited later.
- Set `DB_PER_GAME` to the rounded 2022–2025 mean dropbacks per team-game.
- Season splits: early = Weeks 1–6, mid = 7–12, late = 13–18.
- Ties: excluded from winners and log loss, included in RMSE. Games with no result (such as the canceled 2022 Bills–Bengals game) are skipped.

- [ ] **Step 1: Write failing tests.**

```python
def test_rows_use_only_earlier_weeks():
    # Changing a Week 5 result leaves Week 5 ratings unchanged and Week 6 changed
def test_starter_comes_from_previous_game_not_hindsight():
def test_game_with_no_result_is_skipped():
def test_score_known_values():  # hand-computed rmse, log_loss, winners on 4 games
def test_tie_excluded_from_winners_and_log_loss_but_in_rmse():
def test_fit_recovers_known_slope_and_hfa():  # synthetic data, within 5%
def test_holdout_season_absent_from_its_training_fold():
```

- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement `backtest.py`.
- [ ] **Step 4:** Run `pytest tests/projections/test_backtest.py -v`. Expected: PASS.
- [ ] **Step 5: Commit** with message `feat: add walk-forward model backtest`.

### Task 6: Run the backtest and get sign-off (HARD STOP)

**Files:**
- Create: `docs/projections/backtest-2026-11.md`

- [ ] **Step 1:** Run `python3 -m projections.backtest --seasons 2022 2023 2024 2025 --forward 2026 --out docs/projections/backtest-2026-11.md`.

The report has three versions, each split by early, mid and late season with game counts:
- A: today's model with its current constants, labeled in-sample on 2026 Weeks 6–8
- B: today's formula, refit by the same method, leave-one-season-out
- C: the new model, leave-one-season-out

Include the 2026 forward check for each, the chosen constants, and flat vs. shrinkage. State that 2026 has no late-season games.

- [ ] **Step 2: Verify.** Game counts match expected completed games per season, and version A on 2026 Weeks 6–8 is close to the documented RMSE of about 10.9. Investigate any large gap before reporting.
- [ ] **Step 3: Commit** the report with message `docs: add model backtest report`.
- [ ] **Step 4: STOP.** Show Caleb the results in plain terms, including any split where the new model is worse. Ask him to approve the new model or keep today's formula. Do not start Task 7 without his answer.

### Task 7: Lock in the approved formula

**Files:**
- Modify: `projections/ratings.py`, `constants.py`, `backtest.py`, `README.md`, and related tests

**Interfaces:**
- Produces: `build_ratings(done, pbp, overrides, params) -> RatingSet`, the only production entry point; `PARAMS: Params`, `SHRINK_S` (if used) and `MODEL_VERSION: str` in `constants.py`.

- [ ] **Step 1:** Refit once on all completed games from 2022 through 2026 using the approved formula's method. Write the constants to `constants.py` and set `MODEL_VERSION = "2026.1"`.
- [ ] **Step 2:** Remove the rejected formula from production modules, along with its tests. Keep the backtest report as the historical record. Version comparison in `backtest.py` may be removed if it needs the deleted formula.
- [ ] **Step 3:** Update `projections/README.md`: formula, constants, backtest link, manual refit procedure, and the rule that every refit bumps `MODEL_VERSION`.
- [ ] **Step 4:** Run `pytest tests/projections -v`. Expected: PASS. Confirm raw `off`/`def_` still exactly match the Task 3 baseline.
- [ ] **Step 5: Commit** with message `feat: adopt approved model formula and constants`.

### Task 8: Weekly output and command-line run

**Files:**
- Create: `projections/output.py`, `projections/run.py`, `projections/starters.json`
- Test: `tests/projections/test_output.py`

**Interfaces:**
- Consumes: Task 3 and Task 7 functions.
- Produces:
  - `build_payload(season, done, todo, rs, raw, games, sim) -> dict`
  - `validate(payload, done, pbp, previous: Optional[dict] = None) -> None`, raising `ValueError`, where `previous` is the currently published file
  - `write_if_changed(payload, path) -> bool`, comparing with `generated_at` ignored
  - `write_snapshot(payload, dir) -> str`, writing `{season}-through-wk{NN}.json`
  - `python3 -m projections.run --season 2026 --out frontend/public/data/projections.json --snapshots projections/snapshots --starters projections/starters.json [--data-dir DIR] [--no-download]`

**Payload:** matches the spec's contract, plus top-level `warnings: list[str]`. Each game has `components`: `home_matchup`, `away_matchup`, `matchup_points`, `hfa`, `nudge`, `home_qb_adj_pts`, `away_qb_adj_pts`. Each team's `record` is a string such as `"6-2"` or `"6-2-1"`. Seed `starters.json` with `{"BAL": "J.Fagnano"}`.

- [ ] **Step 1: Write failing tests.**

```python
def test_missing_market_and_spread_become_null():
    assert json.loads(json.dumps(payload, allow_nan=False))["games"][0]["mkt_home"] is None
def test_nan_anywhere_fails_loudly():
def test_validate_rejects_31_teams():
def test_validate_rejects_probability_above_one():
def test_validate_rejects_completed_game_missing_from_pbp():
def test_through_week_regression_rejected():  # lower than the currently published file
def test_rerun_with_only_generated_at_changed_writes_nothing():
    assert write_if_changed(payload_later, path) is False
def test_snapshot_overwrites_same_week():
def test_no_remaining_games_produces_valid_payload():
def test_market_never_reaches_model():
    # Changing moneylines changes mkt_home but not margin or p_home
```

- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement `output.py` and `run.py`. On any validation failure, exit nonzero without touching the output file.
- [ ] **Step 4:** Run `pytest tests/projections -v`. Expected: PASS.
- [ ] **Step 5:** Run for real with `python3 -m projections.run --season 2026 ...`, then run `node -e "JSON.parse(require('fs').readFileSync('frontend/public/data/projections.json'))"`. Expected: no error, 32 teams.
- [ ] **Step 6: Commit** code, `starters.json`, the JSON and first snapshot with message `feat: publish weekly projections JSON`.

### Task 9: Frontend logic and tests

**Files:**
- Create: `frontend/lib/projections.ts`, `frontend/lib/format.ts`, `frontend/lib/heat.ts`, `frontend/vitest.config.ts`
- Modify: `frontend/types/index.ts`, `frontend/package.json`
- Test: `frontend/lib/__tests__/projections.test.ts`, `heat.test.ts`, `format.test.ts`

**Interfaces:**
- Produces, in `types/index.ts`: `ProjectionsData`, `ProjectionTeam`, `ProjectionGame`, `GameComponents`, mirroring Task 8 with units commented.
- Produces, in `format.ts`: `fmt(v: number | null, decimals?: number, sign?: boolean): string`; `pct(p: number | null): string` (`<1%` when 0 < p < 0.005, `—` for null); `marginLabel(name: string, margin: number): string` (`"Packers by 2.8"`).
- Produces, in `projections.ts`:
  - `type Scope = { kind: 'all' } | { kind: 'conference'; value: string } | { kind: 'division'; value: string } | { kind: 'team'; value: string }`
  - `parseScope(param: string | null, teams): Scope`, `scopeToParam(s: Scope): string | null`
  - `teamsInScope(teams, s)`, `gamesInScope(games, teams, s)`, `defaultWeek(games): number | null`, `isStale(generatedAt: string, now: Date, gamesRemaining: number): boolean`
  - `rankRatings(teams, view: 'raw' | 'adjusted')`
- Produces, in `heat.ts`: `heatStyle(value: number, maxAbs: number): { backgroundColor: string; color: string }`, a blue-to-orange diverging scale.

- [ ] **Step 1:** Add `vitest` as a dev dependency and a `"test": "vitest run"` script.
- [ ] **Step 2: Write failing tests.**

```ts
test('gamesInScope includes a game when either team matches')
test('team on bye gets an empty list, not an error')
test('parseScope falls back to all on an unknown value')
test('parseScope and scopeToParam round-trip every scope kind')
test('defaultWeek is the earliest week with unplayed games')
test('defaultWeek is null when no games remain')
test('rankRatings keeps league-wide rank after filtering')
test('isStale true at 9 days with games left, false at 7 days')
test('isStale false when no games remain')
test('heatStyle: contrast is at least 4.5:1 at -max, 0 and +max')
test('heatStyle: never returns plain red or green hues')
test('pct: 0.003 shows <1%, null shows —')
test('marginLabel uses one decimal')
```

- [ ] **Step 3:** Run `npm test` in `frontend/`. Expected: FAIL.
- [ ] **Step 4:** Implement the three modules.
- [ ] **Step 5:** Run `npm test`. Expected: PASS.
- [ ] **Step 6: Commit** with message `feat: add projections filter, format and heat-map helpers`.

### Task 10: Accessible sortable table

**Files:**
- Create: `frontend/components/ui/DataTable.tsx`
- Test: `frontend/components/ui/__tests__/DataTable.test.tsx`

**Interfaces:**
- Produces: `DataTable<T>` with props `rows: T[]`, `rowKey: (r: T) => string`, `columns: Column<T>[]`, `caption: string`, `defaultSort: { key: string; dir: 'asc' | 'desc' }`, `stickyFirstColumn?: boolean`. `Column<T>` has `key`, `label`, `align`, `render`, `sortValue?: (r: T) => string | number | null`, `cellStyle?: (r: T) => React.CSSProperties`.

- [ ] **Step 1:** Add `@testing-library/react`, `@testing-library/user-event` and `jsdom` as dev dependencies. Write failing tests:

```ts
test('header sort control is a button reachable by keyboard')
test('active column sets aria-sort; others do not')
test('Enter toggles sort direction')
test('nulls sort last in both directions')
test('cellStyle is applied to the cell')
test('table has a caption')
```

- [ ] **Step 2:** Run `npm test`. Expected: FAIL.
- [ ] **Step 3:** Implement it, following the `ColDef` pattern in `components/leaderboard/LeaderboardTable.tsx:25-30`. Use a sticky `thead` and optional sticky first column inside an `overflow-auto` wrapper. Use `fmt` from `lib/format.ts`.
- [ ] **Step 4:** Run `npm test`. Expected: PASS.
- [ ] **Step 5: Commit** with message `feat: add accessible sortable table`.

### Task 11: The `/projections` page

**Files:**
- Create: `frontend/app/projections/layout.tsx`, `page.tsx`; `frontend/components/projections/ScopeFilter.tsx`, `GamesSection.tsx`, `GameRow.tsx`, `OutlookSection.tsx`, `RatingsSection.tsx`, `TeamSchedule.tsx`
- Modify: `frontend/components/nav/Navbar.tsx:7-11,22`, `frontend/app/layout.tsx:6-7`
- Test: `frontend/components/projections/__tests__/GameRow.test.tsx`, `RatingsSection.test.tsx`

**Interfaces:**
- Consumes: everything from Tasks 8–10, `components/ui/LoadingSpinner.tsx`.
- Data: `fetch('/data/projections.json', { cache: 'no-cache' })`. Never use `lib/api.ts`, so the page never touches Render.
- URL: `?scope=` and `?week=`. Wrap the `useSearchParams` client component in `<Suspense>`, which Next 14 requires to build.

**Requirements:**
- Order: header ("Through Week N", generated time, stale banner, warnings), scope filter, games with week selector, team schedule (team scope only), outlook by division, ratings.
- Game rows show both win %, `marginLabel`, and market in a visibly separate labeled column. A real `<button aria-expanded>` reveals components in labeled points.
- Ratings show rank, team, Off, Def, Total, default sorted by Total, with heat-mapped numeric cells via `cellStyle`. `maxAbs` is computed per column across all 32 teams, so colors don't shift when filtering. The Raw/Adjusted toggle uses `aria-pressed`. Adjusted adds projected QB and QB adjustment.
- Empty states: `"{Team} is on bye in Week {N}."`, `"No games match this filter in Week {N}."`, `"The regular season is complete."`
- Load failure: an inline `role="alert"` banner saying the projections couldn't be loaded, with a retry button.
- Add `{ href: '/projections', label: 'Projections' }` to `links`. Change the navbar and site titles to "NFL Analytics". The route `layout.tsx` sets the title "ANY/A Projections".

- [ ] **Step 1: Write failing tests.**

```ts
test('GameRow shows — when market is null')
test('GameRow expand button toggles aria-expanded and shows components')
test('GameRow displayed components sum to the margin')
test('RatingsSection Adjusted view shows QB columns; Raw does not')
test('RatingsSection heat scale is unchanged by filtering')
test('warnings from the JSON are displayed')
```

- [ ] **Step 2:** Run `npm test`. Expected: FAIL.
- [ ] **Step 3:** Implement the page and components.
- [ ] **Step 4:** Run `npm test && npx tsc --noEmit && npm run lint && npm run build`. Expected: all pass.
- [ ] **Step 5: Verify in a browser** with the `run` skill at desktop and 375px widths: all, conference, division and team scopes; week change; row expansion; Raw/Adjusted toggle; sticky columns; bookmarked URL reload. Force a stale `generated_at` and a null market in a temporary local copy of the JSON, confirm the banner and "—", then restore the file. Confirm no horizontal page scroll at 375px.
- [ ] **Step 6: Commit** with message `feat: add projections page`.

### Task 12: Weekly workflow

**Files:**
- Create: `.github/workflows/projections.yml` (all logic stays in `projections.run`)
- Modify: `CLAUDE.md` (record the narrow push exception; add `projections/` to the structure)

**Workflow requirements:**
- Triggers: `schedule` at `30 11 * * 2` and `30 15 * * 2` (always before the 8:23 AM ET task, with a later catch-up for play-by-play lag); `push` to `main` on `projections/starters.json`; `workflow_dispatch`.
- `permissions: contents: write`, `concurrency` set to a single group, Python 3.9, install from `projections/requirements.txt`.
- Run `pytest tests/projections`, then `python3 -m projections.run --season 2026 ...`.
- Stage only `frontend/public/data/projections.json` and `projections/snapshots/`. Commit and push only if the staged diff is non-empty, as `github-actions[bot]`.
- A failed run leaves the last good file live. GitHub's failed-run email is the alert. Tell Caleb to confirm that notification setting is on.

- [ ] **Step 1:** Validate the YAML locally with `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/projections.yml'))"`.
- [ ] **Step 2: Commit** with message `ci: add weekly projections workflow`.
- [ ] **Step 3: STOP and ask Caleb to approve pushing the branch and merging to `main`.** List what will go live.
- [ ] **Step 4:** After merge, run the workflow via manual dispatch with `gh workflow run projections.yml`. Expected: green. A second dispatch with no new data commits nothing.
- [ ] **Step 5: Confirm Vercel deploys bot commits.** Check the live `/data/projections.json` has the new `generated_at`, and load `/projections` on the production URL. Vercel can block deployments based on commit author or plan. If it doesn't deploy, bring the deployment status to Caleb before changing anything.

### Task 13: Switch over the Tuesday task

**Files:** none in the repo, except `projections/README.md`.

- [ ] **Step 1:** Draft the new "Weekly NFL model update" prompt with these steps:
  1. Check QB news and commit any change to `projections/starters.json`.
  2. Wait up to 30 minutes for `projections.json` with a `through_week` matching the latest completed week and, if starters changed, a `generated_at` after that commit.
  3. Read it and the prior snapshot.
  4. Push the summary: QB overrides, odds changes, NFC North race, three biggest model-vs-market gaps, the page link, and any `warnings`. If data isn't fresh, say so instead of reporting numbers.
- [ ] **Step 2: Show Caleb the draft and get approval** before updating the live task, since it's outward-facing.
- [ ] **Step 3:** Update the task with `RemoteTrigger`. Update the Weekly workflow section of `projections/README.md`. Commit it, and ask Caleb before pushing, because this README isn't covered by the automation exception.
- [ ] **Step 4:** After the first successful automated Tuesday, ask Caleb to confirm before retiring the Claude Doc. Don't delete the doc without that confirmation.

---

Stages 3 (app reliability, tests and CI) and 4 (hosted QB pipeline and docs) get their own plans after this launches.
