"""
Pipeline Configuration

Single source of truth for season configuration across all Spark jobs.
When adding a new season, update SEASONS here and nowhere else.
"""

# ============================================================
# UPDATE THIS WHEN ADDING A NEW SEASON
# ============================================================
SEASONS = [2022, 2023, 2024, 2025]
# ============================================================

# Derived values — do not edit these directly
MIN_SEASON = min(SEASONS)
MAX_SEASON = max(SEASONS)
YEAR_RANGE = f"{MIN_SEASON}_{MAX_SEASON}"  # e.g. "2022_2025"

# Data paths
RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
ANALYTICS_DB_PATH = "data/analytics/nfl_qb_analysis.db"

# Processed file paths (derived from YEAR_RANGE)
JOINED_PARQUET_PATH = f"{PROCESSED_DATA_DIR}/joined_pbp_participation_{YEAR_RANGE}.parquet"
STANDARDIZED_PARQUET_PATH = f"{PROCESSED_DATA_DIR}/standardized_personnel_{YEAR_RANGE}.parquet"
QB_PLAYS_PARQUET_PATH = f"{PROCESSED_DATA_DIR}/qb_plays_{YEAR_RANGE}.parquet"
