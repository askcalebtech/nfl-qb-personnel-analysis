# NFL QB Personnel Analysis

A data engineering portfolio project analyzing NFL quarterback performance by personnel matchup (e.g., "11 personnel vs Nickel defense") across the 2022–2024 seasons.

Built to demonstrate modern data stack breadth: distributed processing with PySpark, SQL transformations with dbt, REST API with FastAPI, and pipeline orchestration with Airflow.

**Dataset:** 64,605 QB plays · 188 unique QBs · 2022–2024 regular season
**Most common matchup:** 11 vs Nickel — 52% of all plays
**Top QB by volume:** Patrick Mahomes (2,048 plays)

---

## Architecture

```
nflfastR (GitHub releases)
        │
        ▼
┌─────────────────┐
│   PySpark Jobs  │  Extract → Join → Standardize → Filter
│  (spark/jobs/)  │  148k plays → 64,605 QB-relevant plays
└────────┬────────┘
         │ Parquet
         ▼
┌─────────────────┐
│  SQLite + dbt   │  Staging → Intermediate → Marts
│ (dbt_project/)  │  5 models, QB stats by personnel matchup
└────────┬────────┘
         │ SQL tables
         ▼
┌─────────────────┐
│    FastAPI      │  4 endpoints serving QB + league data
│   (api/app.py)  │  Pydantic response models, CORS enabled
└─────────────────┘

Orchestrated by: Apache Airflow (airflow/dags/nfl_pipeline.py)
```

---

## Stack

| Layer | Tool | Version |
|-------|------|---------|
| Processing | PySpark | 3.5.0 |
| Transformation | dbt-core + dbt-sqlite | 1.5.11 / 1.5.1 |
| API | FastAPI + Uvicorn | 0.135.1 / 0.41.0 |
| Orchestration | Apache Airflow | 2.9.3 |
| Storage | SQLite | — |
| Language | Python | 3.9.13 |

---

## Project Structure

```
nfl-qb-personnell-analysis/
├── spark/
│   ├── utils/                         # Reusable Spark utilities
│   │   ├── spark_session.py           # M1-optimized session config
│   │   ├── personnel_parser.py        # Pure Python personnel string parser
│   │   └── data_quality.py            # DataQualityChecker class
│   └── jobs/
│       ├── extract_nflfastr.py        # Download raw parquet from nflfastR
│       ├── join_pbp_participation.py  # Join PBP + participation (95.2% join rate)
│       ├── standardize_personnel.py   # Parse personnel strings via Spark UDFs
│       └── filter_qb_plays.py         # Filter to 64,605 QB-relevant plays
├── dbt_project/
│   └── models/
│       ├── staging/stg_qb_plays.sql           # Clean QB plays (view)
│       ├── intermediate/int_qb_personnel_plays.sql  # Enriched plays (view)
│       └── marts/core/
│           ├── fct_qb_personnel_stats.sql     # QB stats by matchup (table)
│           ├── fct_league_trends.sql           # League-wide trends (table)
│           └── dim_qbs.sql                     # QB dimension table (table)
├── api/
│   └── app.py                         # FastAPI application
├── airflow/
│   └── dags/nfl_pipeline.py           # Full pipeline DAG
├── load_to_sqlite.py                  # Parquet → SQLite loader
└── data/                              # Gitignored — regenerate via pipeline
    ├── raw/                           # nflfastR parquet downloads
    ├── processed/                     # Spark job outputs
    └── analytics/nfl_qb_analysis.db  # SQLite DB (dbt target)
```

---

## Quickstart

### Prerequisites

- Python 3.9+
- Java 17 (required for PySpark — `brew install openjdk@17`)
- ~5GB disk space for raw data

```bash
git clone https://github.com/askcalebtech/nfl-qb-personnell-analysis.git
cd nfl-qb-personnell-analysis
pip install -r requirements.txt --break-system-packages
```

### Configure dbt

```bash
cp dbt_project/profiles.yml.example dbt_project/profiles.yml
# Edit profiles.yml and replace the placeholder path with your absolute project path
```

### Run the Pipeline

```bash
# 1. Download raw data from nflfastR (~5 min)
python spark/jobs/extract_nflfastr.py

# 2. Join play-by-play + participation datasets (~2 min)
python spark/jobs/join_pbp_participation.py

# 3. Standardize personnel notation (~1 min)
python spark/jobs/standardize_personnel.py

# 4. Filter to QB-relevant plays (~1 min)
python spark/jobs/filter_qb_plays.py

# 5. Load processed data into SQLite (~30 sec)
python load_to_sqlite.py

# 6. Run dbt transformations (~1 min)
cd dbt_project && dbt run --profiles-dir . && cd ..
```

### Run the API

```bash
pip install -r api/requirements.txt --break-system-packages
uvicorn api.app:app --reload
```

API available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

### Run with Airflow

```bash
pip install "apache-airflow==2.9.3" --break-system-packages \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.9.txt"
export AIRFLOW_HOME=$(pwd)/airflow
airflow standalone
# Visit http://localhost:8080 — trigger nfl_qb_pipeline manually
```

See [airflow/README.md](airflow/README.md) for full setup details.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check + DB reachability |
| `GET` | `/qbs` | All QBs with career aggregates |
| `GET` | `/qbs/{qb_id}/stats` | QB stats by matchup (`?season=2024&min_plays=20`) |
| `GET` | `/trends` | League-wide personnel trends (`?season=2024`) |
| `GET` | `/matchup/{matchup}` | All QBs for a matchup (e.g. `11_vs_Nickel`) |

### Sample Results

```bash
# Top QBs in 11 vs Nickel, 2024 (filter to meets_starter_threshold client-side)
curl "http://localhost:8000/matchup/11_vs_Nickel?season=2024"
```

Top 5 by EPA/play among QBs with 50+ plays in this matchup:

```json
[
  { "qb_name": "M.Willis",  "play_count": 51,  "epa_per_play": 0.659, "pass_attempts": 41,  "sacks": 4,  "scrambles": 6,  "success_rate": 0.471 },
  { "qb_name": "J.Goff",    "play_count": 339, "epa_per_play": 0.273, "pass_attempts": 315, "sacks": 16, "scrambles": 8,  "success_rate": 0.516 },
  { "qb_name": "J.Allen",   "play_count": 305, "epa_per_play": 0.239, "pass_attempts": 268, "sacks": 10, "scrambles": 27, "success_rate": 0.475 },
  { "qb_name": "P.Mahomes", "play_count": 265, "epa_per_play": 0.206, "pass_attempts": 236, "sacks": 15, "scrambles": 14, "success_rate": 0.494 },
  { "qb_name": "J.Hurts",   "play_count": 277, "epa_per_play": 0.204, "pass_attempts": 231, "sacks": 20, "scrambles": 26, "success_rate": 0.513 }
]
```

---

## Data Quality & Engineering Decisions

Several non-obvious issues were discovered and resolved during development:

**Join key discovery**  
nflfastR play-by-play and participation datasets don't share a clean `game_id`. The correct join keys are `old_game_id` + `play_id`, discovered during data exploration. Final join rate: 95.2%.

**Personnel string parsing**  
Raw personnel strings (`"1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR"`) are parsed into standard notation (`"11"`) using a pure Python function wrapped as a Spark UDF. Built as pure Python first for testability, then registered as a UDF for distributed processing.

**QB identity across play types**  
nflfastR uses different ID fields depending on play type: `passer_player_id` is populated for passes and sacks, but scramble plays only populate `passer_id`. Fixed via `coalesce(passer_player_id, passer_id) as qb_id` in staging — without this, all scrambles aggregate to a NULL QB row in the fact table.

**`pass_attempt = 1` on sack plays**  
The nflfastR `pass_attempt` flag is set to `1` on sack plays, meaning a naive `sum(pass_attempt)` double-counts sacks. Fixed with `sum(case when pass_attempt = 1 and sack = 0 then 1 else 0 end)`.

**SQLite stddev compatibility**  
SQLite has no native `stddev()` function. Replaced with the population standard deviation formula: `sqrt(max(0, avg(epa * epa) - avg(epa) * avg(epa)))` in `fct_league_trends.sql`.

**Reusable data quality framework**  
`DataQualityChecker` validates join rates, null rates, value ranges, and distinct counts at every pipeline stage. Failures log warnings rather than hard-stopping, keeping the pipeline observable without being brittle.

---

## dbt Model Lineage

```
qb_plays_raw (SQLite source)
        │
        ▼
stg_qb_plays (view)
        │
        ▼
int_qb_personnel_plays (view)
     ├──▶ fct_qb_personnel_stats (table)  ──▶ dim_qbs (table)
     └──▶ fct_league_trends (table)
```

---

## Key Findings

- **11 vs Nickel** is the dominant matchup at 52% of all QB plays — the modern NFL is a nickel-vs-spread game
- **2,461 QB × season × personnel matchup** combinations tracked across 50 distinct matchup types
- **Lamar Jackson** leads EPA/play in 11 vs Nickel in 2024 at 0.312, driven partly by scramble efficiency
- **Year-over-year trends** in `fct_league_trends` show Dime defense usage increasing as offenses push more 11 personnel

---

## Interview Talking Points

**Why Spark for 64k rows?**  
The raw dataset is 148k plays across 372 columns — Spark handles the join, column pruning, and UDF application cleanly. More importantly, the architecture is designed to scale: adding seasons or expanding to all plays (not just QB plays) requires no structural changes.

**Why SQLite instead of Postgres?**  
Deliberately chosen to keep the project fully local and zero-infrastructure. The dbt models are standard SQL with no SQLite-specific syntax (except the stddev workaround), so migrating to Postgres is a one-line profiles.yml change.

**Personnel parser design**  
Pure Python first, Spark UDF second. This separation means the parser has unit tests independent of Spark, and the same function can be used in pandas contexts (like the load script) without a SparkSession.

**Pragmatic data decisions**  
2025 participation data isn't yet available from nflfastR. Rather than waiting, the project uses complete 2022–2024 data and the architecture supports incremental season additions without pipeline changes.

---

## Known Limitations

- **Designed QB runs** (e.g. read-option handoff fakes) are not captured — nflfastR attributes these to the rusher, not the passer, and they don't have a `passer_player_id`. This is a source data constraint, not a pipeline bug.
- **2025 data** not yet available from nflfastR participation dataset.
- **SQLite** is not suitable for concurrent API access at scale — production deployment would swap to Postgres.

---

## License

MIT
