# NFL QB Personnel Analysis — Claude Code Context

## Project Overview

Portfolio project analyzing NFL QB performance by personnel matchup (e.g., "11 personnel vs Nickel defense") using a modern data stack. Primary purpose: demonstrate data engineering breadth (Spark, dbt, FastAPI, Airflow) for job search, complementing 6 years of PySpark/AWS experience at Oracle Health.

**Local path:** `~/Documents/Projects/nfl-qb-personnell-analysis`  
**GitHub:** Check `git remote -v` for the remote URL  
**Machine:** M1 Mac, 32GB RAM, Python 3.9.13

---

## Stack & Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.9.13 | Runtime |
| PySpark | 3.5.0 | Data processing |
| dbt-core | 1.7.4 | Transformations |
| dbt-sqlite | 1.5.1 | dbt adapter |
| FastAPI | TBD | API layer (TODO) |
| Airflow | TBD | Orchestration (TODO) |

**Key pip flag:** Always use `pip install --break-system-packages` on this machine.

---

## Repository Structure

```
nfl-qb-personnell-analysis/       # Note: "personnell" is a typo in the dir name — do not rename
├── spark/
│   ├── utils/
│   │   ├── spark_session.py      # Reusable Spark session (M1-optimized: 8g driver/executor)
│   │   ├── personnel_parser.py   # Pure Python personnel string parser (no Spark dependency)
│   │   └── data_quality.py       # DataQualityChecker class for pipeline validation
│   └── jobs/
│       ├── extract_nflfastr.py   # Downloads nflfastR parquet files from GitHub releases
│       ├── join_pbp_participation.py   # Joins PBP + participation on old_game_id + play_id
│       ├── standardize_personnel.py    # Applies personnel UDFs, creates offense/defense std cols
│       └── filter_qb_plays.py          # Filters to QB-relevant regular season plays
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml               # LOCAL ONLY — gitignored, contains SQLite path
│   ├── profiles.yml.example       # TODO: create this as safe committed version
│   └── models/
│       ├── staging/
│       │   ├── stg_qb_plays.sql           # Materialized as view
│       │   └── _staging_schema.yml
│       ├── intermediate/
│       │   └── int_qb_personnel_plays.sql # Materialized as view
│       └── marts/core/
│           ├── fct_qb_personnel_stats.sql # QB stats by personnel matchup — materialized as table
│           ├── fct_league_trends.sql       # League-wide trends — materialized as table
│           ├── dim_qbs.sql                 # QB dimension table — materialized as table
│           └── _marts_schema.yml
├── api/                           # FastAPI app (6 endpoints)
├── airflow/                       # Airflow DAG
├── frontend/                      # Next.js dashboard (QB Dashboard, Leaderboard, League Trends)
├── tests/                         # Test utilities
├── data/                          # GITIGNORED — never commit anything in here
│   ├── raw/                       # nflfastR parquet downloads
│   ├── processed/                 # Spark job outputs
│   └── analytics/
│       └── nfl_qb_analysis.db     # SQLite DB — dbt reads/writes here
├── load_to_sqlite.py              # Loads processed parquet → SQLite for dbt
├── requirements.txt
├── makefile
└── execute.sh
```

---

## Data Pipeline (Manual Execution Order)

```bash
# 1. Extract raw data (~5 min, skips already-downloaded files)
python spark/jobs/extract_nflfastr.py

# 2. Join PBP + participation datasets (~2 min)
python spark/jobs/join_pbp_participation.py

# 3. Standardize personnel strings (~1 min)
python spark/jobs/standardize_personnel.py

# 4. Filter to QB plays (~1 min)
python spark/jobs/filter_qb_plays.py

# 5. Load processed parquet → SQLite (~30 sec)
python load_to_sqlite.py

# 6. Run dbt transformations (~1 min)
cd dbt_project && dbt run --profiles-dir . && cd ..
```

**Total runtime:** ~10-15 minutes end to end.

---

## Key Data Facts

- **Final dataset:** 85,568 QB plays (2022-2025 regular seasons)
- **Source:** nflfastR via `https://github.com/nflverse/nflverse-data/releases/download`
- **Join keys:** `old_game_id` + `play_id` (not `game_id` — this is important)
- **Join rate:** ~95% (consistent across all seasons)
- **Unique QBs:** 216
- **Top QB by volume:** Patrick Mahomes (2,634 plays)
- **Most common matchup:** "11 vs Nickel" — 43,942 plays (51% of all plays)

### Personnel Encoding

**Offense** (`offense_personnel_std`): `"{RBs}{TEs}"` — e.g., `"11"` = 1 RB, 1 TE, 3 WR  
**Defense** (`defense_personnel_std`): DB count → `"Base"` (≤4), `"Nickel"` (5), `"Dime"` (6), `"Quarter"` (7+)

### Known Safe Data Warnings (do not treat as bugs)
- 9.9% of plays have NULL `passer_player_name` — these are QB runs; `passer_player_id` is populated
- 23 offensive personnel types exist (expected max ~20) — exotic formations, safe to keep

---

## dbt Configuration

- **Adapter:** SQLite via dbt-sqlite 1.5.1
- **Database:** `data/analytics/nfl_qb_analysis.db` (relative to project root)
- **Run commands from:** `dbt_project/` directory with `--profiles-dir .` flag always
- **Staging:** materialized as views
- **Intermediate:** materialized as views  
- **Marts:** materialized as tables

```bash
# Always run dbt from dbt_project/ with profiles-dir flag
cd dbt_project
dbt debug --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
dbt docs generate --profiles-dir .
```

---

## Spark Session Config (M1 Mac Optimized)

```python
SparkSession.builder \
    .appName(app_name) \
    .master("local[*]") \
    .config("spark.driver.memory", "8g") \
    .config("spark.executor.memory", "8g") \
    .config("spark.sql.adaptive.enabled", "true")
```

Always import the session from `spark/utils/spark_session.py` — do not create ad hoc sessions.

---

## What's Built vs TODO

| Layer | Status | Notes |
|-------|--------|-------|
| Data ingestion | ✅ Done | `extract_nflfastr.py` |
| Spark pipeline | ✅ Done | 4 jobs + utils |
| dbt models | ✅ Done | 5 models, staging → marts |
| SQLite load | ✅ Done | `load_to_sqlite.py` |
| `profiles.yml.example` | ✅ Done | Safe committed version of profiles.yml |
| README.md | ✅ Done | Portfolio-quality readme with architecture diagram |
| FastAPI layer | ✅ Done | 6 endpoints (api/app.py) |
| Airflow DAG | ✅ Done | 1 DAG, 6 tasks |
| Frontend | ✅ Done | Next.js dashboard — QB Dashboard, Leaderboard, League Trends |

---

## API Endpoints (FastAPI — api/app.py)

```
GET /health                       # Liveness check + DB reachability
GET /qbs                          # All QBs from dim_qbs
GET /qbs/{qb_id}/stats            # QB stats by matchup; ?season=2024&min_plays=20
GET /trends                       # League trends from fct_league_trends; ?season=2024
GET /matchup/{matchup}            # All QBs in a specific matchup (e.g. "11_vs_Nickel")
GET /rankings                     # Season QB rankings by weighted EPA/play; ?season=2024&min_plays=20
GET /leaderboard                  # QB leaderboard for a matchup with auto min-plays threshold; ?season=2024&matchup=11_vs_Nickel
```

---

## Airflow DAG Spec (not yet built)

Target file: `airflow/dags/nfl_pipeline.py`

```
extract_data → join_pbp_participation → standardize_personnel → filter_qb_plays → load_to_sqlite → dbt_run
```

Schedule: weekly during season, monthly off-season.

---

## Permissions for Claude Code

Claude Code is permitted to do the following **without asking**:
- Create new files anywhere in the project
- Run dbt commands (`dbt run`, `dbt test`, `dbt debug`, `dbt docs generate`) with `--profiles-dir .`
- Run Python and PySpark jobs
- Install pip packages using `pip install --break-system-packages`

Claude Code should **always ask** before:
- Deleting or overwriting existing Spark jobs or dbt models
- Modifying `load_to_sqlite.py` or `spark/utils/` utilities
- Running the full pipeline end to end (takes 10-15 min)
- Pushing to GitHub

---

## Interview Talking Points (for context on project framing)

- **Architecture:** 3-layer pipeline — Spark for distributed processing, dbt for SQL transformations, API for serving. Demonstrates separation of concerns.
- **Scale:** ~200k plays processed across 4 seasons (2022-2025), 95% join accuracy, 807 statistically significant QB/matchup combinations (≥20 plays).
- **Personnel parser:** Raw strings like `"1 C, 2 G, 1 QB, 1 RB..."` → standardized `"11"` notation. Built as pure Python for testability, wrapped as Spark UDF for scale.
- **Data quality:** Reusable `DataQualityChecker` validates join rates, null rates, value ranges at every pipeline stage.
- **Pragmatic decisions:** Covers four complete regular seasons (2022-2025). Adding a new season requires only updating `config.py` and re-running the pipeline.
