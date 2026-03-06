"""
Standardize Personnel Notation

This Spark job loads the joined play-by-play + participation data and
standardizes the personnel strings into clean notation:
- Offensive: "1 RB, 1 TE, 3 WR" format → "11" notation
- Defensive: "3 CB, 2 DE, 2 DT, 1 FS, 2 ILB, 1 SS" → "Nickel" classification

Input:
    - data/processed/joined_pbp_participation_{year_range}.parquet

Output:
    - data/processed/standardized_personnel_{year_range}.parquet

Usage:
    python spark/jobs/standardize_personnel.py
"""

import sys
from pathlib import Path
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spark.utils import (
    SparkSessionManager,
    standardize_offensive_personnel,
    classify_defensive_personnel,
    DataQualityChecker
)


def load_joined_data(spark, year_range: str = "2022_2024") -> DataFrame:
    """
    Load the joined play-by-play + participation data.
    
    Args:
        spark: SparkSession
        year_range: Year range identifier (e.g., "2022_2024")
        
    Returns:
        Joined DataFrame
    """
    path = f"data/processed/joined_pbp_participation_{year_range}.parquet"
    
    if not Path(path).exists():
        raise FileNotFoundError(f"Joined data not found at {path}. Run join_pbp_participation.py first.")
    
    print(f"Loading joined data from {path}...")
    df = spark.read.parquet(path)
    
    print(f"✅ Loaded {df.count():,} plays")
    return df


def create_standardization_udfs(spark):
    """
    Create Spark UDFs (User Defined Functions) for personnel parsing.
    
    Args:
        spark: SparkSession
        
    Returns:
        Tuple of (offense_udf, defense_udf)
    """
    print("Creating standardization UDFs...")
    
    # Register the Python functions as Spark UDFs
    offense_udf = F.udf(standardize_offensive_personnel, StringType())
    defense_udf = F.udf(classify_defensive_personnel, StringType())
    
    print("✅ UDFs created")
    return offense_udf, defense_udf


def standardize_personnel_columns(df: DataFrame, offense_udf, defense_udf) -> DataFrame:
    """
    Apply personnel standardization to the DataFrame.
    
    Args:
        df: Input DataFrame with raw personnel strings
        offense_udf: UDF for offensive personnel standardization
        defense_udf: UDF for defensive personnel classification
        
    Returns:
        DataFrame with new standardized columns
    """
    print("\nStandardizing personnel columns...")
    
    # Apply UDFs to create new standardized columns
    df = df.withColumn(
        'offense_personnel_std',
        offense_udf(F.col('offense_personnel'))
    )
    
    df = df.withColumn(
        'defense_personnel_std',
        defense_udf(F.col('defense_personnel'))
    )
    
    print("✅ Standardization complete")
    return df


def show_standardization_examples(df: DataFrame) -> None:
    """
    Display examples of the standardization for validation.
    
    Args:
        df: DataFrame with standardized columns
    """
    print("\n" + "="*80)
    print("STANDARDIZATION EXAMPLES")
    print("="*80)
    
    print("\nOffensive Personnel Standardization:")
    print("-"*80)
    df.select(
        'offense_personnel',
        'offense_personnel_std'
    ).filter(
        F.col('offense_personnel').isNotNull()
    ).distinct().show(10, truncate=False)
    
    print("\nDefensive Personnel Classification:")
    print("-"*80)
    df.select(
        'defense_personnel',
        'defense_personnel_std'
    ).filter(
        F.col('defense_personnel').isNotNull()
    ).distinct().show(10, truncate=False)


def analyze_standardization_results(df: DataFrame) -> None:
    """
    Analyze the distribution of standardized personnel groupings.
    
    Args:
        df: DataFrame with standardized columns
    """
    print("\n" + "="*80)
    print("STANDARDIZATION ANALYSIS")
    print("="*80)
    
    # Offensive personnel distribution
    print("\nOffensive Personnel Distribution:")
    print("-"*80)
    df.groupBy('offense_personnel_std').count() \
        .orderBy(F.desc('count')) \
        .show(15)
    
    # Defensive personnel distribution
    print("\nDefensive Personnel Distribution:")
    print("-"*80)
    df.groupBy('defense_personnel_std').count() \
        .orderBy(F.desc('count')) \
        .show(15)
    
    # Null analysis
    total_rows = df.count()
    offense_nulls = df.filter(F.col('offense_personnel_std').isNull()).count()
    defense_nulls = df.filter(F.col('defense_personnel_std').isNull()).count()
    
    print("\nNull Analysis:")
    print("-"*80)
    print(f"Total plays: {total_rows:,}")
    print(f"Offense personnel nulls: {offense_nulls:,} ({offense_nulls/total_rows*100:.1f}%)")
    print(f"Defense personnel nulls: {defense_nulls:,} ({defense_nulls/total_rows*100:.1f}%)")
    
    # Most common matchups
    print("\nTop 10 Personnel Matchups:")
    print("-"*80)
    df.groupBy('offense_personnel_std', 'defense_personnel_std').count() \
        .orderBy(F.desc('count')) \
        .withColumnRenamed('offense_personnel_std', 'Offense') \
        .withColumnRenamed('defense_personnel_std', 'Defense') \
        .withColumnRenamed('count', 'Plays') \
        .show(10, truncate=False)


def run_quality_checks(df: DataFrame) -> None:
    """
    Run data quality checks on the standardized dataset.
    
    Args:
        df: Standardized DataFrame
    """
    print("\n" + "="*80)
    print("RUNNING DATA QUALITY CHECKS")
    print("="*80)
    
    checker = DataQualityChecker(df, "Standardized Personnel")
    
    # Basic checks
    checker.check_row_count(min_rows=100000)
    
    # Required columns
    required_cols = [
        'game_id', 'play_id', 'season', 'epa',
        'offense_personnel', 'defense_personnel',
        'offense_personnel_std', 'defense_personnel_std'
    ]
    checker.check_required_columns(required_cols)
    
    # Null rate checks - standardized columns should have similar null rates to originals
    checker.check_null_rates(
        ['offense_personnel_std', 'defense_personnel_std'],
        max_null_rate=0.25  # Allow up to 25% (some plays legitimately don't have personnel)
    )
    
    # Check that we have reasonable personnel distributions
    offense_distinct = checker.check_distinct_values('offense_personnel_std', min_distinct=5, max_distinct=23)
    defense_distinct = checker.check_distinct_values('defense_personnel_std', min_distinct=3, max_distinct=10)
    
    # Print summary
    checker.print_summary()


def save_standardized_data(df: DataFrame, year_range: str = "2022_2024") -> None:
    """
    Save standardized data to processed directory.
    
    Args:
        df: Standardized DataFrame
        year_range: Year range identifier
    """
    output_path = f"data/processed/standardized_personnel_{year_range}.parquet"
    
    print(f"\nSaving standardized data to {output_path}...")
    
    # Write as parquet with partitioning by season
    df.write.mode('overwrite').partitionBy('season').parquet(output_path)
    
    print(f"✅ Saved successfully!")
    print(f"   Location: {output_path}")
    print(f"   Partitioned by: season")


def main():
    """Main execution function."""
    YEAR_RANGE = "2022_2024"
    
    print("="*80)
    print("STANDARDIZE PERSONNEL NOTATION")
    print("="*80)
    print(f"Year range: {YEAR_RANGE}\n")
    
    with SparkSessionManager("Standardize-Personnel") as spark:
        
        # Load joined data
        df = load_joined_data(spark, YEAR_RANGE)
        
        # Create UDFs for standardization
        offense_udf, defense_udf = create_standardization_udfs(spark)
        
        # Apply standardization
        df = standardize_personnel_columns(df, offense_udf, defense_udf)
        
        # Show examples
        show_standardization_examples(df)
        
        # Analyze results
        analyze_standardization_results(df)
        
        # Run quality checks
        run_quality_checks(df)
        
        # Save results
        save_standardized_data(df, YEAR_RANGE)
    
    print("\n" + "="*80)
    print("✅ STANDARDIZATION COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. Run: python spark/jobs/filter_qb_plays.py")
    print("2. This will filter to only QB-relevant plays")


if __name__ == "__main__":
    main()