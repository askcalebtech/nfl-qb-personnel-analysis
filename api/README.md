# NFL QB Personnel Analysis — API

FastAPI service that serves QB performance data from the dbt-built SQLite database.

## Prerequisites

The full Spark + dbt pipeline must have been run at least once so the SQLite database exists at `data/analytics/nfl_qb_analysis.db`. See the root README for pipeline instructions.

## Setup

```bash
pip install -r api/requirements.txt
```

## Run locally

```bash
uvicorn api.app:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive docs (Swagger UI): `http://localhost:8000/docs`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check + DB reachability |
| `GET` | `/qbs` | All QBs with career aggregates |
| `GET` | `/qbs/{qb_id}/stats` | A QB's stats by personnel matchup |
| `GET` | `/trends` | League-wide personnel trends |
| `GET` | `/matchup/{matchup}` | All QBs for a specific matchup |

### Query parameters

**`GET /qbs/{qb_id}/stats`**
- `?season=2024` — filter to a single season
- `?min_plays=20` — only return matchups with at least N plays

**`GET /trends`**
- `?season=2024` — filter to a single season

**`GET /matchup/{matchup}`**
- Use underscores in place of spaces: `11_vs_Nickel`, `12_vs_Base`, etc.
- `?season=2024` — filter to a single season

### Example requests

```bash
# All QBs
curl http://localhost:8000/qbs

# Mahomes stats, 2024 season, 20+ play matchups only
curl "http://localhost:8000/qbs/00-0033873/stats?season=2024&min_plays=20"

# League trends for 2023
curl "http://localhost:8000/trends?season=2023"

# All QBs in the 11 vs Nickel matchup
curl "http://localhost:8000/matchup/11_vs_Nickel"
```
