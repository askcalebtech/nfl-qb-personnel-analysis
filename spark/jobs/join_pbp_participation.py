"""
Join Play-by-Play and Participation Data

This Spark job loads play-by-play and participation data, joins them on
old_game_id + play_id, and saves the enriched dataset for further processing.

Input:
    - data/raw/play_by_play_{year}.parquet
    - data/raw/participation_{year}.parquet

Output:
    - data/processed/joined_pbp_participation_{year}.parquet

Usage:
    python spark/jobs/join_pbp_participation.py
"""

import sys
from pathlib import Path
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spark.utils import (
    SparkSessionManager,
    validate_play_by_play,
    validate_participation,
    DataQualityChecker
)


def load_play_by_play(spark, years: list) -> DataFrame:
    """
    Load play-by-play data for specified years.
    
    Args:
        spark: SparkSession
        years: List of years to load (e.g., [2022, 2023, 2024])
        
    Returns:
        Combined DataFrame of all years
    """
    dfs = []
    
    for year in years:
        path = f"data/raw/play_by_play_{year}.parquet"
        
        if not Path(path).exists():
            print(f"⚠️  Warning: {path} not found, skipping...")
            continue
            
        print(f"Loading play-by-play data for {year}...")
        df = spark.read.parquet(path)
        
        # Add year column if not present
        if 'season' not in df.columns:
            df = df.withColumn('season', F.lit(year))
        
        dfs.append(df)
    
    if not dfs:
        raise FileNotFoundError("No play-by-play files found!")
    
    # Union all years
    combined = dfs[0]
    for df in dfs[1:]:
        combined = combined.unionByName(df, allowMissingColumns=True)
    
    print(f"✅ Loaded {combined.count():,} total plays from {len(dfs)} seasons")
    return combined


def load_participation(spark, years: list) -> DataFrame:
    """
    Load participation data for specified years.
    
    Args:
        spark: SparkSession
        years: List of years to load
        
    Returns:
        Combined DataFrame of all years
    """
    dfs = []
    
    for year in years:
        path = f"data/raw/participation_{year}.parquet"
        
        if not Path(path).exists():
            print(f"⚠️  Warning: {path} not found, skipping...")
            continue
            
        print(f"Loading participation data for {year}...")
        df = spark.read.parquet(path)
        dfs.append(df)
    
    if not dfs:
        raise FileNotFoundError("No participation files found!")
    
    # Union all years
    combined = dfs[0]
    for df in dfs[1:]:
        combined = combined.unionByName(df, allowMissingColumns=True)
    
    print(f"✅ Loaded {combined.count():,} total participation records from {len(dfs)} seasons")
    return combined


def join_datasets(pbp: DataFrame, participation: DataFrame) -> DataFrame:
    """
    Join play-by-play and participation data.
    
    Join keys: old_game_id + play_id (discovered during data exploration)
    
    Args:
        pbp: Play-by-play DataFrame
        participation: Participation DataFrame
        
    Returns:
        Joined DataFrame
    """
    print("\nJoining play-by-play with participation data...")
    
    # Verify join keys exist
    pbp_columns = set(pbp.columns)
    part_columns = set(participation.columns)
    
    if 'old_game_id' not in pbp_columns or 'play_id' not in pbp_columns:
        raise ValueError("Play-by-play data missing join keys: old_game_id and/or play_id")
    
    if 'old_game_id' not in part_columns or 'play_id' not in part_columns:
        raise ValueError("Participation data missing join keys: old_game_id and/or play_id")
    
    # Perform inner join (only keep plays with both datasets)
    joined = pbp.join(
        participation,
        on=['old_game_id', 'play_id'],
        how='inner'
    )
    
    pbp_count = pbp.count()
    joined_count = joined.count()
    join_rate = (joined_count / pbp_count * 100) if pbp_count > 0 else 0
    
    print(f"✅ Join complete:")
    print(f"   Play-by-play rows: {pbp_count:,}")
    print(f"   Participation rows: {participation.count():,}")
    print(f"   Joined rows: {joined_count:,}")
    print(f"   Join rate: {join_rate:.1f}%")
    
    if join_rate < 80:
        print(f"⚠️  Warning: Low join rate ({join_rate:.1f}%). Expected ~90%+")
    
    return joined


def select_relevant_columns(df: DataFrame) -> DataFrame:
    """
    Select only the columns we need for downstream processing.
    
    This reduces data size and makes downstream jobs faster.
    
    Args:
        df: Joined DataFrame with all columns
        
    Returns:
        DataFrame with selected columns
    """
    # Core identifiers
    id_cols = [
        'game_id', 'old_game_id', 'play_id', 'season', 'week', 'season_type'
    ]
    
    # Game context
    game_cols = [
        'home_team', 'away_team', 'posteam', 'posteam_type', 'defteam',
        'game_date', 'game_half', 'quarter_end'
    ]
    
    # Play details
    play_cols = [
        'play_type', 'down', 'ydstogo', 'yardline_100', 'goal_to_go',
        'qtr', 'time', 'desc', 'yards_gained',
        'pass_attempt', 'sack', 'qb_scramble'
    ]
    
    # QB/Passer info
    qb_cols = [
        'passer_player_name', 'passer_player_id', 'passer_id',
        'qb_epa', 'air_epa', 'yac_epa', 'comp_air_epa', 'comp_yac_epa'
    ]
    
    # Performance metrics
    metric_cols = [
        'epa', 'wpa', 'success', 'cpoe', 'xyac_epa', 'xyac_mean_yardage'
    ]
    
    # Score/situation
    situation_cols = [
        'score_differential', 'posteam_score_post', 'defteam_score_post',
        'ep', 'wp'
    ]
    
    # Personnel (from participation data)
    personnel_cols = [
        'offense_personnel', 'defense_personnel', 'offense_formation',
        'defenders_in_box', 'number_of_pass_rushers',
        'offense_players', 'defense_players'
    ]
    
    # Combine all column lists
    all_cols = (
        id_cols + game_cols + play_cols + qb_cols + 
        metric_cols + situation_cols + personnel_cols
    )
    
    # Filter to only columns that exist in the DataFrame
    available_cols = [col for col in all_cols if col in df.columns]
    
    print(f"\nSelecting {len(available_cols)} relevant columns...")
    return df.select(*available_cols)


def save_joined_data(df: DataFrame, years: list) -> None:
    """
    Save joined data to processed directory.
    
    Args:
        df: Joined DataFrame
        years: List of years included in the data
    """
    # Create output directory
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine output filename
    if len(years) == 1:
        output_path = f"data/processed/joined_pbp_participation_{years[0]}.parquet"
    else:
        year_range = f"{min(years)}_{max(years)}"
        output_path = f"data/processed/joined_pbp_participation_{year_range}.parquet"
    
    print(f"\nSaving joined data to {output_path}...")
    
    # Write as parquet with partitioning by season for better performance
    df.write.mode('overwrite').partitionBy('season').parquet(output_path)
    
    print(f"✅ Saved successfully!")
    print(f"   Location: {output_path}")
    print(f"   Partitioned by: season")


def run_quality_checks(df: DataFrame) -> None:
    """
    Run data quality checks on the joined dataset.
    
    Args:
        df: Joined DataFrame
    """
    print("\n" + "="*60)
    print("RUNNING DATA QUALITY CHECKS")
    print("="*60)
    
    checker = DataQualityChecker(df, "Joined PBP + Participation")
    
    # Basic checks
    checker.check_row_count(min_rows=100000)
    
    # Required columns
    required_cols = [
        'game_id', 'play_id', 'season', 'epa',
        'offense_personnel', 'defense_personnel'
    ]
    checker.check_required_columns(required_cols)
    
    # Null rate checks
    checker.check_null_rates(
        ['offense_personnel', 'defense_personnel', 'epa'],
        max_null_rate=0.2
    )
    
    # Value range checks
    checker.check_value_range('epa', min_value=-15, max_value=15)
    checker.check_value_range('season', min_value=2016, max_value=2030)
    
    # Print summary
    checker.print_summary()


def main():
    """Main execution function."""
    from config import SEASONS
    YEARS = SEASONS
    
    print("="*60)
    print("JOIN PLAY-BY-PLAY AND PARTICIPATION DATA")
    print("="*60)
    print(f"Years: {YEARS}\n")
    
    with SparkSessionManager("Join-PBP-Participation") as spark:
        
        # Load data
        pbp = load_play_by_play(spark, YEARS)
        participation = load_participation(spark, YEARS)
        
        # Validate input data
        print("\n" + "-"*60)
        print("Validating input data...")
        print("-"*60)
        
        pbp_checker = validate_play_by_play(pbp)
        pbp_checker.print_summary()
        
        part_checker = validate_participation(participation)
        part_checker.print_summary()
        
        # Join datasets
        joined = join_datasets(pbp, participation)
        
        # Select relevant columns
        joined = select_relevant_columns(joined)
        
        # Run quality checks on joined data
        run_quality_checks(joined)
        
        # Save results
        save_joined_data(joined, YEARS)
    
    print("\n" + "="*60)
    print("✅ JOIN COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Run: python spark/jobs/standardize_personnel.py")
    print("2. This will parse personnel strings into standard notation")


if __name__ == "__main__":
    main()