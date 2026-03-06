# Spark Jobs

Processing jobs for the NFL QB Personnel Analysis pipeline.

## Execution Order

Run jobs in this sequence:

```bash
# 1. Extract data from nflfastR
python spark/jobs/extract_nflfastr.py

# 2. (Optional) Explore the data structure
python spark/jobs/explore_data.py

# 3. (Optional) Test join logic with small sample
python spark/jobs/test_join.py

# 4. Join play-by-play and participation data
python spark/jobs/join_pbp_participation.py

# 5. Standardize personnel notation
python spark/jobs/standardize_personnel.py  # TODO: Create next

# 6. Filter to QB-relevant plays
python spark/jobs/filter_qb_plays.py  # TODO: Create next
```

---

## Job Descriptions

### `extract_nflfastr.py` ✅
**Purpose:** Download raw data from nflfastR GitHub repository

**Inputs:** None (downloads from URLs)

**Outputs:**
- `data/raw/play_by_play_{year}.parquet`
- `data/raw/participation_{year}.parquet`
- `data/raw/roster_{year}.parquet`

**Configuration:**
- Edit `YEARS` list to specify seasons (default: 2022-2024)
- Edit `OUTPUT_DIR` to change destination

---

### `explore_data.py` ✅
**Purpose:** Understand data structure and validate downloads

**Inputs:**
- `data/raw/play_by_play_2024.parquet`
- `data/raw/participation_2024.parquet`
- `data/raw/roster_2024.parquet`

**Outputs:** Console output with data summaries

**What it shows:**
- Row counts and column names
- Sample data from each dataset
- Personnel grouping distributions
- Join preview between datasets

---

### `test_join.py` ✅
**Purpose:** Quick validation that join logic works

**Inputs:**
- `data/raw/play_by_play_2024.parquet` (first 1000 rows)
- `data/raw/participation_2024.parquet` (first 1000 rows)

**Outputs:** Console output with join results

**Use when:**
- Testing join keys before full run
- Debugging join issues
- Validating data after re-download

---

### `join_pbp_participation.py` ✅
**Purpose:** Join play-by-play with participation data for all years

**Inputs:**
- `data/raw/play_by_play_{year}.parquet` (for each year)
- `data/raw/participation_{year}.parquet` (for each year)

**Outputs:**
- `data/processed/joined_pbp_participation_{year_range}.parquet`
- Partitioned by season

**Configuration:**
- Edit `YEARS` to specify seasons to process

**Data Quality Checks:**
- Validates input data structure
- Checks join rate (warns if <80%)
- Verifies required columns exist
- Checks for reasonable EPA values

**Processing:**
1. Loads all specified years
2. Joins on `old_game_id` + `play_id`
3. Selects relevant columns only
4. Runs quality checks
5. Saves with season partitioning

---

### `standardize_personnel.py` 🚧 TODO
**Purpose:** Parse personnel strings into standard notation

**Inputs:**
- `data/processed/joined_pbp_participation_{year_range}.parquet`

**Outputs:**
- `data/processed/standardized_personnel_{year_range}.parquet`

**What it does:**
- Converts `"1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR"` → `"11"`
- Classifies defense as "Base", "Nickel", "Dime", "Quarter"
- Uses `spark.utils.personnel_parser` functions

---

### `filter_qb_plays.py` 🚧 TODO
**Purpose:** Filter to only QB-relevant plays

**Inputs:**
- `data/processed/standardized_personnel_{year_range}.parquet`

**Outputs:**
- `data/processed/qb_plays_{year_range}.parquet`

**Filters:**
- Only plays with a passer (QB dropbacks)
- Minimum play threshold (e.g., 20+ plays per QB)
- Regular season only (optional)
- Valid down and distance

---

## Common Issues

### "File not found" errors
**Solution:** Make sure you ran `extract_nflfastr.py` first

### Low join rate (<80%)
**Possible causes:**
- Data corruption during download
- Mismatched years between datasets
- Run `explore_data.py` to investigate

### Out of memory errors
**Solutions:**
- Reduce `spark.driver.memory` in `spark_session.py`
- Process fewer years at once
- Use smaller sample for testing

### Import errors
**Solution:** Make sure you're running from project root:
```bash
cd nfl-qb-personnel-analysis
python spark/jobs/join_pbp_participation.py
```

---

## Performance Tips

- **Use test_join.py first** - Validates logic before processing full data
- **Process years separately** - If memory is tight, process one year at a time
- **Check output size** - Joined data should be ~2-3GB for 3 years
- **Monitor Spark UI** - Visit http://localhost:4040 during job execution