"""
Load QB Plays Data to SQLite

This script loads the Spark-processed QB plays parquet data into
a SQLite database so dbt can query it.

Input:
    - data/processed/qb_plays_2022_2024.parquet

Output:
    - data/analytics/nfl_qb_analysis.db (SQLite database)

Usage:
    python load_to_sqlite.py
"""

import sqlite3
import pandas as pd
from pathlib import Path


def load_parquet_to_sqlite():
    """Load QB plays parquet data into SQLite database."""
    
    print("="*80)
    print("LOADING QB PLAYS TO SQLITE")
    print("="*80 + "\n")
    
    from config import QB_PLAYS_PARQUET_PATH, ANALYTICS_DB_PATH

    # Paths
    parquet_path = QB_PLAYS_PARQUET_PATH
    db_path = ANALYTICS_DB_PATH
    
    # Create analytics directory
    Path("data/analytics").mkdir(parents=True, exist_ok=True)
    
    # Check if parquet file exists
    if not Path(parquet_path).exists():
        raise FileNotFoundError(
            f"QB plays data not found at {parquet_path}. "
            "Run filter_qb_plays.py first."
        )
    
    print(f"Loading parquet data from {parquet_path}...")
    
    # Read parquet file
    df = pd.read_parquet(parquet_path)
    
    print(f"✅ Loaded {len(df):,} QB plays\n")
    
    # Show sample
    print("Sample of data:")
    print("-"*80)
    print(df[['passer_player_name', 'season', 'offense_personnel_std', 
              'defense_personnel_std', 'epa']].head())
    print()
    
    # Connect to SQLite
    print(f"Creating SQLite database at {db_path}...")
    conn = sqlite3.connect(db_path)
    
    # Write to SQLite
    print("Writing to database table 'qb_plays_raw'...")
    df.to_sql('qb_plays_raw', conn, if_exists='replace', index=False)
    
    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM qb_plays_raw")
    count = cursor.fetchone()[0]
    
    print(f"✅ Successfully loaded {count:,} rows to database\n")
    
    # Show table info
    cursor.execute("PRAGMA table_info(qb_plays_raw)")
    columns = cursor.fetchall()
    
    print("Database schema (first 10 columns):")
    print("-"*80)
    for col in columns[:10]:
        col_name = col[1]
        col_type = col[2]
        print(f"  {col_name}: {col_type}")
    print(f"  ... and {len(columns) - 10} more columns\n")
    
    # Close connection
    conn.close()
    
    print("="*80)
    print("✅ SQLITE LOADING COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. cd dbt_project")
    print("2. dbt debug --profiles-dir . (test connection)")
    print("3. dbt run --profiles-dir . (run all models)")
    print()
    print(f"Database location: {db_path}")


if __name__ == "__main__":
    load_parquet_to_sqlite()