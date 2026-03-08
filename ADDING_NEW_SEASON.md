# Adding a New Season to the Pipeline

This guide walks through adding a new NFL season (e.g. 2025) to the data pipeline.
The process takes about 15–20 minutes once the data is available from nflfastR.

---

## Before You Start

### Check that participation data is available

The pipeline requires **both** play-by-play and participation data. Play-by-play data
is typically available shortly after the season ends, but participation data can lag
by several weeks. Before starting, verify both files exist for your target season:

```
# Play-by-play
https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.parquet

# Participation (this is the one that may not be ready yet)
https://github.com/nflverse/nflverse-data/releases/download/pbp_participation/pbp_participation_2025.parquet
```

Paste each URL into your browser. If you get a download, the data is available. If you
get a 404, check back in a few weeks.

**Do not attempt to run the pipeline without both files.** The join step will fail
or produce a very low join rate if participation data is missing or incomplete.

---

## Step 1 — Update the Season Configuration

Open `config.py` in the project root and add the new season to the `SEASONS` list:

```python
# Before
SEASONS = [2022, 2023, 2024]

# After
SEASONS = [2022, 2023, 2024, 2025]
```

This is the **only place** you need to change the season list. All Spark jobs and
file paths are derived from this config automatically.

---

## Step 2 — Update the dbt Schema Test

Open `dbt_project/models/staging/_staging_schema.yml` and add the new year to the
`accepted_values` test for the `season` column:

```yaml
# Before
- accepted_values:
    values: [2022, 2023, 2024]

# After
- accepted_values:
    values: [2022, 2023, 2024, 2025]
```

If you skip this step, `dbt test` will fail after the pipeline runs because the new
season year won't be in the allowed values list.

---

## Step 3 — Run the Pipeline

Run each step in order from the project root. Each step depends on the previous one
completing successfully.

```bash
# Step 1: Download new raw data (~5 min)
# This skips files that already exist, so only 2025 files will be downloaded
python spark/jobs/extract_nflfastr.py

# Step 2: Re-join all seasons including the new one (~3-4 min)
python spark/jobs/join_pbp_participation.py

# Step 3: Re-standardize personnel notation (~2 min)
python spark/jobs/standardize_personnel.py

# Step 4: Re-filter to QB plays (~2 min)
python spark/jobs/filter_qb_plays.py

# Step 5: Reload SQLite database (~30 sec)
# Note: this replaces the entire database — all seasons are reloaded together
python load_to_sqlite.py

# Step 6: Re-run dbt models (~1 min)
cd dbt_project && dbt run --profiles-dir . && cd ..

# Step 7: Run dbt tests to verify data quality
cd dbt_project && dbt test --profiles-dir . && cd ..
```

**Total time:** ~15–20 minutes

---

## Step 4 — Validate the Results

After the pipeline completes, do a quick sanity check in SQLite:

```bash
sqlite3 data/analytics/nfl_qb_analysis.db
```

```sql
-- Confirm all seasons are present
SELECT season, COUNT(*) as plays
FROM qb_plays_raw
GROUP BY season
ORDER BY season;

-- Check 2025 join rate looks reasonable (should be 90%+ like prior years)
-- Compare raw PBP count vs joined count in the pipeline logs

-- Check top QBs for the new season
SELECT qb_name, play_count, round(epa_per_play, 3) as epa_per_play
FROM fct_qb_personnel_stats
WHERE season = 2025
  AND personnel_matchup = '11 vs Nickel'
  AND play_count >= 20
ORDER BY epa_per_play DESC
LIMIT 10;

-- Confirm dim_qbs updated
SELECT COUNT(*) as total_qbs FROM dim_qbs;
```

**What to look for:**
- All 4 seasons present in `qb_plays_raw`
- 2025 play count is in a reasonable range (a full season should be 18,000–25,000 QB plays)
- Join rate for 2025 is 90%+ (check the pipeline logs from step 2)
- Top QBs in 2025 look plausible — no obvious data issues like a backup QB leading the league with 5 plays

If the 2025 join rate is significantly lower than prior years (e.g. below 85%), the
participation data may be incomplete. Check the nflfastR GitHub releases page to see
if an updated participation file has been published.

---

## Step 5 — Update the Frontend Season Filter

The season filter buttons in the frontend are currently hardcoded. Open
`frontend/components/dashboard/SeasonFilter.tsx` and add 2025 to the seasons array:

```typescript
// Before
const seasons = ['2022', '2023', '2024', '2022–24']

// After
const seasons = ['2022', '2023', '2024', '2025', '2022–25']
```

Also update the all-seasons label from `'2022–24'` to `'2022–25'` everywhere it appears
in the frontend — search for `2022–24` across the `frontend/` directory.

---

## Step 6 — Update Documentation

Update these references in `README.md`:

- Dataset description: `2022–2024 seasons` → `2022–2025 seasons`
- Dataset stat: `64,605 QB plays` → actual new count (check `qb_plays_raw` row count)
- Dataset stat: `188 unique QBs` → updated count from `dim_qbs`
- Known limitations: remove or update the "2025 data not yet available" note
- Sample results tables: optionally re-run the leaderboard queries for 2025

Update `CLAUDE.md`:
- Change `2022-2024` references to `2022-2025`
- Update the play count and QB count stats

---

## Troubleshooting

**Low join rate for 2025 (<85%)**
The participation file may be a preliminary release. Check the nflfastR releases page
for an updated file. The pipeline logs will show the exact join rate.

**`dbt test` fails on `accepted_values`**
You forgot Step 2. Add 2025 to the accepted values list in `_staging_schema.yml`.

**Play counts look wrong for 2025**
Check whether the 2025 data includes playoffs. The filter in `filter_qb_plays.py`
already restricts to `season_type = 'REG'` so playoff plays are excluded — this is
expected behavior.

**Missing players or low QB count for 2025**
Some QBs may have retired or new ones entered the league. The pipeline handles this
automatically — `dim_qbs` will include any QB with plays in the data regardless of
whether they appeared in prior seasons.

**Pipeline runs but no 2025 data appears in the API**
The API reads from SQLite at query time, so no restart is needed. If data isn't
appearing, check that `load_to_sqlite.py` completed successfully and that the dbt
models rebuilt (check `dbt_project/target/run_results.json` for errors).

---

## Notes

- The Airflow DAG (`airflow/dags/nfl_pipeline.py`) reads from `config.py` so it will
  automatically pick up the new season — no DAG changes needed.
- All dbt models are written without hardcoded seasons, so they will automatically
  include 2025 data once it's in SQLite.
- The API has no hardcoded seasons — all endpoints accept a `?season=` query param
  and return whatever seasons exist in the database.
