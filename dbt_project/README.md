# NFL QB Personnel Analysis - dbt Project

dbt models for transforming QB play-by-play data into analytics-ready tables.

## Project Structure

```
models/
├── staging/           # Raw data cleaning
│   └── stg_qb_plays.sql
├── intermediate/      # Enrichment and calculations
│   └── int_qb_personnel_plays.sql
└── marts/            # Final analytics tables
    └── core/
        ├── fct_qb_personnel_stats.sql   # QB stats by matchup
        ├── fct_league_trends.sql         # League-wide trends
        └── dim_qbs.sql                   # QB dimension table
```

## Model Descriptions

### Staging Layer

**`stg_qb_plays`**
- Loads QB plays from Spark-processed parquet files
- Applies basic cleaning and standardization
- Creates play identifiers and flags
- Materialized as: **VIEW**

### Intermediate Layer

**`int_qb_personnel_plays`**
- Enriches QB plays with calculated fields
- Adds personnel matchup combinations
- Categorizes performance and situations
- Materialized as: **VIEW**

### Marts Layer

**`fct_qb_personnel_stats`** (Main fact table)
- Aggregates QB performance by personnel matchup
- One row per QB + Season + Personnel combination
- Includes EPA, success rate, play counts
- Calculates percentiles and performance tiers
- Materialized as: **TABLE**

**`fct_league_trends`**
- League-wide personnel usage and performance
- One row per Season + Personnel Matchup
- Shows usage %, league averages, year-over-year changes
- Materialized as: **TABLE**

**`dim_qbs`**
- QB dimension table with career aggregates
- One row per QB
- Career EPA, play counts, seasons played
- Materialized as: **TABLE**

## Running dbt

### Prerequisites

1. Install dbt-sqlite:
```bash
pip install dbt-sqlite
```

2. Ensure Spark jobs have been run:
- `join_pbp_participation.py` ✓
- `standardize_personnel.py` ✓
- `filter_qb_plays.py` ✓

### Setup

1. Create analytics directory:
```bash
mkdir -p data/analytics
```

2. Load source data into SQLite (see `load_to_sqlite.py` script)

### Commands

```bash
cd dbt_project

# Test connection
dbt debug --profiles-dir .

# Run all models
dbt run --profiles-dir .

# Run specific model
dbt run --profiles-dir . --select fct_qb_personnel_stats

# Run with dependencies
dbt run --profiles-dir . --select +fct_qb_personnel_stats

# Test data quality
dbt test --profiles-dir .

# Generate documentation
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .
```

## Model Dependencies

```
stg_qb_plays
    ↓
int_qb_personnel_plays
    ↓
    ├─→ fct_qb_personnel_stats ─→ dim_qbs
    └─→ fct_league_trends
```

## Key Metrics

### fct_qb_personnel_stats
- `play_count` - Sample size for the matchup
- `epa_per_play` - Average EPA (main performance metric)
- `success_rate` - % of successful plays
- `pass_rate` - % of plays that were passes
- `epa_percentile` - Ranking among all QBs in that season

### fct_league_trends
- `usage_pct` - % of all plays using this matchup
- `league_epa_per_play` - League average EPA
- `usage_pct_change_yoy` - Year-over-year usage change
- `usage_rank` - Frequency rank (1 = most common)

### dim_qbs
- `career_plays` - Total plays across all matchups
- `career_epa_per_play` - Career-weighted average EPA
- `is_starter` - Flag for QBs with 500+ plays

## Testing

All models include data quality tests:
- Unique keys
- Not null checks
- Accepted values
- Relationships

Run tests:
```bash
dbt test --profiles-dir .
```

## Querying the Data

Once models are run, query them directly:

```sql
-- Top QBs in 11 vs Nickel matchup
SELECT 
    qb_name,
    season,
    play_count,
    epa_per_play,
    success_rate
FROM fct_qb_personnel_stats
WHERE personnel_matchup = '11 vs Nickel'
  AND play_count >= 20
ORDER BY epa_per_play DESC
LIMIT 10;

-- Most common matchups in 2024
SELECT 
    personnel_matchup,
    usage_pct,
    league_epa_per_play
FROM fct_league_trends
WHERE season = 2024
ORDER BY usage_pct DESC
LIMIT 5;

-- Top QBs by career EPA
SELECT 
    qb_name,
    career_plays,
    career_epa_per_play,
    seasons_played
FROM dim_qbs
WHERE is_starter = true
ORDER BY career_epa_per_play DESC
LIMIT 10;
```

## Next Steps

1. Run dbt models to create analytics tables
2. Build API endpoints that query these tables
3. Create frontend visualizations