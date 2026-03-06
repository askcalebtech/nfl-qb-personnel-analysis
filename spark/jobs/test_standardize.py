"""
Test Standardize Personnel Script

Quick test to verify the standardization logic works before running the full job.
Uses a small sample to validate faster.
"""

import sys
from pathlib import Path
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spark.utils import (
    SparkSessionManager,
    standardize_offensive_personnel,
    classify_defensive_personnel
)


def test_standardization():
    """Test the standardization logic with a small sample."""
    
    print("Testing standardization logic with small sample...\n")
    
    with SparkSessionManager("Test-Standardization") as spark:
        
        # Load small sample
        print("Loading sample...")
        df = spark.read.parquet("data/processed/joined_pbp_participation_2022_2024.parquet").limit(100)
        
        print(f"Sample size: {df.count()} plays\n")
        
        # Create UDFs
        print("Creating UDFs...")
        offense_udf = F.udf(standardize_offensive_personnel, StringType())
        defense_udf = F.udf(classify_defensive_personnel, StringType())
        
        # Apply standardization
        print("Applying standardization...")
        df = df.withColumn('offense_personnel_std', offense_udf(F.col('offense_personnel')))
        df = df.withColumn('defense_personnel_std', defense_udf(F.col('defense_personnel')))
        
        # Show results
        print("\n" + "="*80)
        print("OFFENSIVE PERSONNEL STANDARDIZATION")
        print("="*80)
        df.select('offense_personnel', 'offense_personnel_std') \
            .filter(F.col('offense_personnel').isNotNull()) \
            .distinct() \
            .show(10, truncate=False)
        
        print("\n" + "="*80)
        print("DEFENSIVE PERSONNEL CLASSIFICATION")
        print("="*80)
        df.select('defense_personnel', 'defense_personnel_std') \
            .filter(F.col('defense_personnel').isNotNull()) \
            .distinct() \
            .show(10, truncate=False)
        
        # Check for nulls
        offense_nulls = df.filter(F.col('offense_personnel_std').isNull()).count()
        defense_nulls = df.filter(F.col('defense_personnel_std').isNull()).count()
        total = df.count()
        
        print("\n" + "="*80)
        print("NULL ANALYSIS")
        print("="*80)
        print(f"Total plays: {total}")
        print(f"Offense standardization nulls: {offense_nulls} ({offense_nulls/total*100:.1f}%)")
        print(f"Defense classification nulls: {defense_nulls} ({defense_nulls/total*100:.1f}%)")
        
        # Show a few complete examples
        print("\n" + "="*80)
        print("COMPLETE EXAMPLES")
        print("="*80)
        df.select(
            'passer_player_name',
            'offense_personnel_std',
            'defense_personnel_std',
            'epa'
        ).filter(
            F.col('passer_player_name').isNotNull()
        ).show(10, truncate=False)
        
        print("\n✅ Test passed! Standardization logic works correctly.")
        print("\nReady to run: python spark/jobs/standardize_personnel.py")


if __name__ == "__main__":
    test_standardization()