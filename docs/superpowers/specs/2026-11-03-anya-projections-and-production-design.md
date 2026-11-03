# ANY/A Projections Page and Production Readiness: Design

Once approved, save this as `docs/superpowers/specs/2026-11-03-anya-projections-and-production-design.md`.

## Context

Caleb has a working ANY/A projection model (`nfl_pipeline.py`, documented in `CLAUDE_ANY_A_MODEL.md`) and a ratings chart (`10730.jpg`). Each Tuesday, a cloud scheduled task updates a Claude Doc and pushes a summary. He wants this inside his Next.js app, and wants the app and pipeline made production-ready.

The primary user is Caleb, checking the page weekly. Portfolio value is a side benefit, not the design driver.

## Decisions Caleb made

- The new page is his weekly check-in, and **it replaces the Claude Doc**. The push summary stays and links to the page.
- This week's games come first, shown **league-wide, with filters by conference, division and team**. NFC North is not pinned.
- **Fix the model's scaling first**, and show old vs. new results before the page uses the new numbers.
- In scope: protecting Airflow secrets, loading and error fixes, tests and CI, Airflow and docs fixes, and productionizing the app and pipeline.
- **"Production" means hands-off and low cost:** scheduled jobs run without his laptop and alert on failure, using free tiers where possible. Airflow stays a local or demo tool. Cold starts may remain.
- **Weekly automation may push directly to `main`, for the projections JSON, weekly snapshots and starters file only.** Record this narrow exception in `CLAUDE.md`. Every other push still needs his approval.
- **The QB pipeline runs weekly in season, including 2026,** on GitHub Actions, with the database delivered through a release file that Render downloads.

## Goals, non-goals, anti-goals

**Goals:** fresh numbers every Tuesday with no laptop involved; one source of truth for model logic; a page usable on a phone; failures that are visible rather than silent.

**Non-goals:** hosted Airflow, cloud Spark, a paid always-on API, playoff bracket odds, ties in simulated games, injuries beyond QB, a redesign of the existing QB pages.

**Anti-goals:**
- Betting lines must never feed the model. They are display-only (`CLAUDE_ANY_A_MODEL.md:87,107`).
- The raw Off/Def/Total values must not change, because they must still match his chart's definition.
- The page must never show stale numbers without saying so.
- Secrets must never be committed.

## Work order (each stage ships on its own)

### Stage 1: Secret protection
Add `airflow/airflow.db`, `airflow/airflow.cfg`, `airflow/logs/`, `airflow/standalone_admin_password.txt`, `airflow/webserver_config.py` and `nfl_out/` to `.gitignore`. Confirm with `git check-ignore`. None of them have ever been committed, so no history rewrite or key rotation is needed.

### Stage 2: Model and projections page

**Refactor (builder's call on exact layout; suggested `projections/`):**
- Move `nfl_pipeline.py` out of the repo root and rename it, because it collides with `airflow/dags/nfl_pipeline.py`.
- Split it into pure, testable functions behind `main()`, with no work on import. Add `--season` instead of the hard-coded value, and download without shelling out to `curl`.
- Give it its own requirements file (pandas, numpy, pyarrow). Don't add these to `api/requirements.txt`.
- Keep it compatible with Python 3.9.
- Keep it separate from the Spark/dbt QB pipeline. That database lacks 2026 data and the required columns.
- Move `CLAUDE_ANY_A_MODEL.md` next to the code and keep it current.

**Bug fixes:**
- `NaN` must become `null` in the JSON (`nfl_pipeline.py:116-117`). Write with `allow_nan=False` so any regression fails loudly.
- A team with no completed game must not crash the run (`:79`).

**Model fix:**
- Today's ratings are season totals, while `SLOPE` is a fixed rate fit on Weeks 6–8. This inflates late-season margins and favors teams that have played more games.
- Convert the ratings used for prediction to per-dropback rates multiplied by a fixed dropbacks-per-game constant. This includes the opponent adjustment and QB adjustment.
- Rework `K` and `SLOPE` to the new scale. Refit `SLOPE`, `HFA` and `SIG`. `REG`, `QB_K`, `QB_PRIOR` and the rush constants may also be refit if the backtest supports it.
- Per-dropback rates remove the accidental early-season damping of season totals, so replace the flat `REG` with sample-size shrinkage toward zero if the backtest supports it. Don't add prior-season priors in this project.
- With no completed games, a team's rating is 0, so Week 1 predictions reduce to home-field advantage.
- Raw chart values are unchanged.

**Backtest:**
- Run walk-forward: predict each week using only earlier data, including the "starter = QB from the previous game" rule.
- The same nflverse URL pattern gives 2022–2025 play-by-play. Use leave-one-season-out across those seasons, because 2026 has no late-season games and can't test the late-season flaw.
- Treat 2026 games to date as a forward check.
- Compare three versions: **today's model as it runs** (labeled in-sample on 2026 Weeks 6–8, since its constants were fit there), **today's formula refit by the same method**, and **the new model**.
- Report RMSE, log loss, winners picked and calibration, split by early, mid and late season. Give game counts for every split.
- **Gate:** show Caleb the results and get his sign-off before the page launches. The page, cron and Claude Doc retirement all wait for this, and the existing Tuesday task keeps running until launch.
- If he rejects the new math, the default is launching on today's formula. Production code carries only one formula.

**Constants after sign-off:**
- Refit once, including 2026 games, then freeze the constants. The backtest validates the method; the final constants themselves can't be held out.
- Later refits are manual and bump `model_version`. Weekly runs don't refit, so numbers don't move for non-football reasons. Document the procedure.

**Weekly data:**
- Output is one small JSON file, assumed to be `frontend/public/data/projections.json`, using this contract:
  - Top level: `season`, `through_week`, `generated_at`, `league_anya`, `model_version`.
  - `teams[]`: `team`, name, conference, division, record, raw `off`/`def`, adjusted `adj_off`/`adj_def`, `starter`, `qb_adj`, `rush_off`, `rush_def`, `avg_wins`, 10th and 90th percentile wins, and `div`, `playoffs`, `seed1` odds (all 0–1).
  - `games[]`: `game_id`, `week`, `gameday`, `away`, `home`, `neutral`, `stadium`, `p_home`, `margin`, `nudge`, the matchup components that produce the margin, `mkt_home`, `spread`.
  - **Scale:** `adj_off`, `adj_def` and `qb_adj` are published in season-total terms (per-dropback value × that team's dropbacks), so the Raw/Adjusted toggle stays on one comparable scale. Game-row components use the per-game prediction scale and are labeled as points or per-game values.
- Also save each week's predictions as a dated snapshot, so accuracy can be measured later. Accuracy UI is a follow-up.
- `starters` overrides live in a committed JSON file.

**Scheduling:**
- A GitHub Actions workflow runs the model and commits the JSON, which triggers a Vercel redeploy. Triggers: Tuesday cron, a push to the starters file, and manual dispatch. Commit only if the file changed.
- Validate before committing: 32 teams, a plausible `through_week`, probabilities in 0–1. A failure leaves the last good file live, and GitHub's failed-run email is the alert.
- The Tuesday cloud task no longer embeds a copy of the script. Its steps:
  1. Check QB news and commit any starters change.
  2. Wait for the workflow to publish.
  3. Read the published JSON and the prior week's snapshot from the repo.
  4. Push the same summary as today (QB overrides, odds changes, NFC North race, three biggest model-vs-market gaps), now linking to the page.
- If the data isn't fresh by the task's time limit, the summary says so rather than reporting stale numbers. If the task fails, the cron still publishes with the last known starters.
- **First implementation check:** confirm the cloud task can push to the repo. If it can't, stop and bring that back to Caleb, because the starters flow depends on it.
- Retire the Claude Doc after the first successful automated week.

**Page (`/projections`, added to `links` in `frontend/components/nav/Navbar.tsx:7-11`):**
- Filter bar: All, conference, division, team. It applies to every section and is stored in the URL so views can be bookmarked.
- This week's games: both win percentages, "Team by X.X", and the market's favorite shown visibly separate from the model. A week selector reaches later weeks.
- Each game row expands to show matchup components, rush nudge and QB adjustment (his stated preference, `CLAUDE_ANY_A_MODEL.md:108`).
- Season outlook grouped by division: record, expected wins, 80% range, division, playoff and #1-seed odds.
- Ratings table in the format of `10730.jpg`: rank, team, Off/Def/Total, sorted by Total, with a Raw/Adjusted toggle. Adjusted view includes projected QB and QB adjustment.
- Choosing a team adds its remaining schedule.
- Header: "Through Week N" and generated time. Show a stale banner when data is more than 8 days old in season.
- Data loads from the static file, so it never waits on Render.

**Page details left to the builder:**
- Add a new accessible, generic sortable table, following the `ColDef` pattern at `frontend/components/leaderboard/LeaderboardTable.tsx:25-30`. It needs a per-cell style hook, real sort buttons with `aria-sort`, a sticky header and a sticky team column.
- Heat map: colorblind-safe diverging scale (e.g. blue/orange) via inline styles, with explicit text color and contrast. Numbers always visible.
- Put shared helpers (`fmt`, team metadata, color scale) in `frontend/lib/`. Don't add a seventh copy of `fmt`.
- Rename "QB Personnel" branding (`Navbar.tsx:22`, `app/layout.tsx:6-7`) to something broader, and give the page its own title via a route `layout.tsx`.

### Stage 3: App reliability, tests and CI

**Frontend:**
- Fix: endless spinner (`app/leaderboard/page.tsx:33,60`), stuck spinner beside errors (`app/dashboard/page.tsx:35,39`), stale rows after failed refetch, race conditions, `MatchupTable` pagination reset, career ranks shown as season ranks (`StatsGrid.tsx:70,78-85`), medal borders following the sort (`LeaderboardTable.tsx:152-155`).
- Add: timeout and automatic retry in `frontend/lib/api.ts` sized for a cold start, a retry button, a shared error banner, user-facing error text, `error.tsx`. Fail the production build when `NEXT_PUBLIC_API_URL` is missing rather than falling back to localhost.
- Centralize seasons and the `'2022–25'` string, and align default seasons.
- Move existing tables to the shared table. This fixes keyboard sorting along the way.
- Fix the most serious accessibility gaps: labels, `QBSelector` keyboard use, `aria-pressed`, `role="alert"`/`status`, one `h1` per page.

**API (`api/app.py`):**
- Open SQLite read-only, and close connections reliably.
- Remove the filesystem path and raw exception from `/health`.
- Restrict CORS to the Vercel domain and localhost, GET only.
- Fail clearly when the DB file is missing.

**Tests and CI:**
- `pytest`: ANY/A math, opponent adjustment, QB adjustment, margin math and JSON schema, on small fixtures. API endpoints via `TestClient` against a tiny fixture SQLite DB. Personnel parser (replace the print-only scripts).
- `vitest`: filter logic, color scale, formatting helpers.
- GitHub Actions on PRs: pytest, frontend lint, typecheck and build. Wire up the empty `make test` and `make lint` targets. `dbt test` runs wherever the QB pipeline runs.

### Stage 4: Production pipeline and docs

- **Hosted QB pipeline:**
  - A GitHub Actions workflow runs Spark, `load_to_sqlite.py`, dbt run and dbt test weekly in season, plus manual dispatch. Start with a spike proving Spark and Java work on a standard runner within its limits.
  - Publish the SQLite DB as a GitHub release file. Render downloads it during build or startup, and the app fails clearly if it's missing. Publish only after dbt tests pass, so a bad run leaves the last good DB live.
  - Stop tracking `data/analytics/nfl_qb_analysis.db` going forward. Don't rewrite git history.
- **Adding 2026 (issues already found):**
  - Adding it to `SEASONS` renames every processed parquet file via `YEAR_RANGE` (`config.py:17,25-27`), and stale `2022_2024` paths must be cleaned first.
  - The dbt `accepted_values` test needs updating (`_staging_schema.yml:30`).
  - The extractor skips files that already exist (`extract_nflfastr.py:88,122,156`), so the current season must always re-download.
  - Participation data can lag by weeks (`ADDING_NEW_SEASON.md:14-30`). A missing current-season file must not fail or wipe prior seasons, and QB pages should show how current the data is.
  - Add 2026 to the frontend season lists through the Stage 3 centralization.
  - Per `CLAUDE.md`, ask Caleb before overwriting Spark jobs or changing `load_to_sqlite.py` or `spark/utils/`, and before running the full pipeline.
- **Airflow (local/demo):** set `cwd=PROJECT_DIR` on every task (relative paths currently break it), replace hard-coded paths at `airflow/dags/nfl_pipeline.py:16-18` with config, use `schedule`, set `load_examples = False`, add `dbt test`, and run the DAG once end to end.
- **Docs:** correct the stale claims in `CLAUDE.md` and `README.md` (gitignored `data/`, endpoint count, versions, DAG status, test claims, "zero-infrastructure", clone URL), replace the boilerplate `frontend/README.md`, and clear `2022_2024` references.
- **Render:** confirm the live service's settings in its dashboard, since `api/render.yaml` may not be in use. Fix the mismatch.

## Left to the builder
File and module names, JSON field naming beyond the contract's meaning, component breakdown, the fixed dropbacks-per-game value, visual styling within the constraints above, and test fixture design.

## Calls Claude made (Caleb hasn't explicitly agreed to these)
- Static JSON on Vercel rather than a new API endpoint, to avoid cold starts on a weekly page.
- GitHub Actions runs the model. The cloud task only handles QB news and the summary.
- Backtesting on 2022–2025 with 2026 as a forward check, instead of refitting on 2026 alone.
- Allowing sample-size shrinkage and refits of other constants if the backtest supports them, but no prior-season priors.
- Launching on today's formula if the new math is rejected.
- Freezing constants after one final refit, with manual refits afterward.
- Publishing adjusted ratings in season-total terms.
- Keeping the summary's current contents.
- Saving weekly snapshots now and building accuracy UI later.
- Keeping `10730.jpg` out of git unless the page needs it.

## Verification

- **Stage 1:** `git check-ignore` matches each path, and `git status` no longer lists them.
- **Stage 2:**
  - A snapshot of the refactored model's raw Off/Def values is compared with the original script on the same data; they must match exactly.
  - The backtest report is reviewed by Caleb.
  - `JSON.parse` succeeds on the output.
  - The workflow runs via manual dispatch and commits the file.
  - The page is driven in a browser at desktop and 375px widths, covering every filter level, week change, row expansion, Raw/Adjusted toggle and the stale banner.
- **Stage 3:** CI passes on a PR. With the API stopped or slow, each existing page shows an error and retry, not an endless spinner. Tables sort by keyboard.
- **Stage 4:** the hosted workflow completes via manual dispatch, publishes the release file, and Render serves 2026 data from it. A forced dbt test failure leaves the prior DB live. One full local DAG run succeeds with outputs in the project directory. Live API and Vercel smoke-tested after deployment.
