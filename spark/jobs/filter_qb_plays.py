"""
Filter to QB-Relevant Plays

This Spark job loads the standardized personnel data and filters to only
plays relevant for QB personnel matchup analysis:
- QB dropbacks (passes and sacks)
- Valid personnel data (not NULL)
- Regular season games
- Valid downs (1-4)
- Minimum sample size thresholds

Input:
    - data/processed/standardized_personnel_{year_range}.parquet

Output:
    - data/processed/qb_plays_{year_range}.parquet

Usage:
    python spark/jobs/filter_qb_plays.py
"""

import sys
from pathlib import Path
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spark.utils import (
    SparkSessionManager,
    DataQualityChecker
)


def load_standardized_data(spark, year_range: str = "2022_2024") -> DataFrame:
    """
    Load the standardized personnel data.
    
    Args:
        spark: SparkSession
        year_range: Year range identifier (e.g., "2022_2024")
        
    Returns:
        Standardized DataFrame
    """
    path = f"data/processed/standardized_personnel_{year_range}.parquet"
    
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Standardized data not found at {path}. "
            "Run standardize_personnel.py first."
        )
    
    print(f"Loading standardized data from {path}...")
    df = spark.read.parquet(path)
    
    print(f"✅ Loaded {df.count():,} plays")
    return df


def show_filtering_stats(original_df: DataFrame, filtered_df: DataFrame, filter_name: str) -> int:
    """
    Show statistics about a filtering operation.
    
    Args:
        original_df: DataFrame before filter
        filtered_df: DataFrame after filter
        filter_name: Name of the filter for display
        
    Returns:
        Count of filtered DataFrame
    """
    original_count = original_df.count()
    filtered_count = filtered_df.count()
    removed = original_count - filtered_count
    pct_kept = (filtered_count / original_count * 100) if original_count > 0 else 0
    
    print(f"  {filter_name}:")
    print(f"    Before: {original_count:,} plays")
    print(f"    After:  {filtered_count:,} plays")
    print(f"    Removed: {removed:,} plays ({100-pct_kept:.1f}%)")
    print(f"    Kept: {pct_kept:.1f}%")
    print()
    
    return filtered_count


def filter_to_qb_plays(df: DataFrame) -> DataFrame:
    """
    Apply all filters to get QB-relevant plays.
    
    Args:
        df: Standardized DataFrame
        
    Returns:
        Filtered DataFrame with only QB plays
    """
    print("\n" + "="*80)
    print("APPLYING FILTERS")
    print("="*80 + "\n")
    
    original_df = df
    
    # Filter 1: Has a passer (QB dropback)
    print("Filter 1: QB Dropbacks Only")
    print("-"*80)
    df = df.filter(
        (F.col('passer_player_id').isNotNull()) | 
        (F.col('passer_id').isNotNull())
    )
    show_filtering_stats(original_df, df, "Keep only plays with a passer")
    
    # Filter 2: Valid personnel data
    print("Filter 2: Valid Personnel Data")
    print("-"*80)
    df = df.filter(
        F.col('offense_personnel_std').isNotNull() &
        F.col('defense_personnel_std').isNotNull()
    )
    show_filtering_stats(original_df, df, "Remove NULL personnel")
    
    # Filter 3: Regular season only (optional - can include playoffs)
    print("Filter 3: Regular Season Only")
    print("-"*80)
    df = df.filter(
        F.col('season_type') == 'REG'
    )
    show_filtering_stats(original_df, df, "Keep regular season games only")
    
    # Filter 4: Valid downs (1-4)
    print("Filter 4: Valid Downs")
    print("-"*80)
    df = df.filter(
        F.col('down').between(1, 4)
    )
    show_filtering_stats(original_df, df, "Keep downs 1-4 only")
    
    # Filter 5: Non-NULL EPA (needed for analysis)
    print("Filter 5: Valid EPA")
    print("-"*80)
    df = df.filter(
        F.col('epa').isNotNull()
    )
    show_filtering_stats(original_df, df, "Remove plays with NULL EPA")
    
    # Summary
    final_count = df.count()
    original_count = original_df.count()
    total_removed = original_count - final_count
    pct_kept = (final_count / original_count * 100) if original_count > 0 else 0
    
    print("="*80)
    print("FILTERING SUMMARY")
    print("="*80)
    print(f"Started with:  {original_count:,} plays")
    print(f"Ended with:    {final_count:,} plays")
    print(f"Total removed: {total_removed:,} plays")
    print(f"Retention rate: {pct_kept:.1f}%")
    print("="*80 + "\n")
    
    return df


def analyze_qb_distribution(df: DataFrame) -> None:
    """
    Analyze the distribution of QBs in the filtered dataset.
    
    Args:
        df: Filtered QB plays DataFrame
    """
    print("\n" + "="*80)
    print("QB DISTRIBUTION ANALYSIS")
    print("="*80 + "\n")
    
    # Top QBs by play count
    print("Top 20 QBs by Play Count:")
    print("-"*80)
    df.groupBy('passer_player_name', 'passer_player_id').count() \
        .orderBy(F.desc('count')) \
        .withColumnRenamed('passer_player_name', 'QB') \
        .withColumnRenamed('count', 'Plays') \
        .select('QB', 'Plays') \
        .show(20, truncate=False)
    
    # QBs per season
    print("\nQBs per Season:")
    print("-"*80)
    df.groupBy('season').agg(
        F.countDistinct('passer_player_id').alias('Unique_QBs'),
        F.count('*').alias('Total_Plays')
    ).orderBy('season').show()
    
    # Plays per personnel matchup
    print("\nPlays per Personnel Matchup:")
    print("-"*80)
    df.groupBy('offense_personnel_std', 'defense_personnel_std').count() \
        .orderBy(F.desc('count')) \
        .withColumnRenamed('offense_personnel_std', 'Offense') \
        .withColumnRenamed('defense_personnel_std', 'Defense') \
        .withColumnRenamed('count', 'Plays') \
        .show(15, truncate=False)


def analyze_sample_sizes(df: DataFrame) -> None:
    """
    Analyze sample sizes for QB + personnel matchup combinations.
    
    Args:
        df: Filtered QB plays DataFrame
    """
    print("\n" + "="*80)
    print("SAMPLE SIZE ANALYSIS")
    print("="*80 + "\n")
    
    # QBs with plays by matchup
    matchup_counts = df.groupBy(
        'passer_player_name',
        'season',
        'offense_personnel_std',
        'defense_personnel_std'
    ).agg(
        F.count('*').alias('plays')
    )
    
    # Distribution of sample sizes
    print("Distribution of Sample Sizes (QB + Season + Personnel Matchup):")
    print("-"*80)
    matchup_counts.groupBy('plays').count() \
        .orderBy('plays') \
        .withColumnRenamed('plays', 'Plays_per_Matchup') \
        .withColumnRenamed('count', 'Number_of_Matchups') \
        .show(30)
    
    # Common minimum thresholds
    print("\nMatchups by Minimum Play Threshold:")
    print("-"*80)
    thresholds = [5, 10, 20, 30, 50]
    
    for threshold in thresholds:
        count = matchup_counts.filter(F.col('plays') >= threshold).count()
        print(f"  {threshold}+ plays: {count:,} matchups")
    
    print()


def show_sample_data(df: DataFrame) -> None:
    """
    Show sample of the filtered QB plays data.
    
    Args:
        df: Filtered DataFrame
    """
    print("\n" + "="*80)
    print("SAMPLE QB PLAYS DATA")
    print("="*80 + "\n")
    
    print("Random sample of 10 QB plays:")
    print("-"*80)
    df.select(
        'passer_player_name',
        'season',
        'week',
        'offense_personnel_std',
        'defense_personnel_std',
        'down',
        'ydstogo',
        'epa',
        'play_type'
    ).orderBy(F.rand()).show(10, truncate=False)


def run_quality_checks(df: DataFrame) -> None:
    """
    Run data quality checks on the filtered QB plays dataset.
    
    Args:
        df: Filtered DataFrame
    """
    print("\n" + "="*80)
    print("RUNNING DATA QUALITY CHECKS")
    print("="*80)
    
    checker = DataQualityChecker(df, "QB Plays")
    
    # Basic checks
    checker.check_row_count(min_rows=50000)
    
    # Required columns
    required_cols = [
        'passer_player_name', 'passer_player_id',
        'season', 'week', 'epa',
        'offense_personnel_std', 'defense_personnel_std'
    ]
    checker.check_required_columns(required_cols)
    
    # Null rate checks - should be very low after filtering
    checker.check_null_rates(
        ['passer_player_name', 'offense_personnel_std', 'defense_personnel_std', 'epa'],
        max_null_rate=0.05  # Very strict - expect <5% nulls
    )
    
    # Value range checks
    checker.check_value_range('epa', min_value=-15, max_value=15)
    checker.check_value_range('down', min_value=1, max_value=4)
    
    # Check QB count
    qb_count = checker.check_distinct_values('passer_player_id', min_distinct=50)
    
    # Print summary
    checker.print_summary()


def save_qb_plays(df: DataFrame, year_range: str = "2022_2024") -> None:
    """
    Save filtered QB plays to processed directory.
    
    Args:
        df: Filtered QB plays DataFrame
        year_range: Year range identifier
    """
    output_path = f"data/processed/qb_plays_{year_range}.parquet"
    
    print(f"\nSaving QB plays to {output_path}...")
    
    # Write as parquet with partitioning by season
    df.write.mode('overwrite').partitionBy('season').parquet(output_path)
    
    print(f"✅ Saved successfully!")
    print(f"   Location: {output_path}")
    print(f"   Partitioned by: season")


def main():
    """Main execution function."""
    YEAR_RANGE = "2022_2024"
    
    print("="*80)
    print("FILTER TO QB-RELEVANT PLAYS")
    print("="*80)
    print(f"Year range: {YEAR_RANGE}\n")
    
    with SparkSessionManager("Filter-QB-Plays") as spark:
        
        # Load standardized data
        df = load_standardized_data(spark, YEAR_RANGE)
        
        # Apply filters
        qb_plays = filter_to_qb_plays(df)
        
        # Analyze QBs
        analyze_qb_distribution(qb_plays)
        
        # Analyze sample sizes
        analyze_sample_sizes(qb_plays)
        
        # Show sample data
        show_sample_data(qb_plays)
        
        # Run quality checks
        run_quality_checks(qb_plays)
        
        # Save results
        save_qb_plays(qb_plays, YEAR_RANGE)
    
    print("\n" + "="*80)
    print("✅ FILTERING COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. The QB plays dataset is ready for dbt transformations")
    print("2. Or create aggregation script for direct analysis")
    print("3. Data is at: data/processed/qb_plays_2022_2024.parquet")


if __name__ == "__main__":
    main()