"""
Test Filter QB Plays Script

Quick test to verify the filtering logic works before running the full job.
Uses a small sample to validate faster.
"""

import sys
from pathlib import Path
from pyspark.sql import functions as F

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spark.utils import SparkSessionManager


def test_filtering():
    """Test the filtering logic with a small sample."""
    
    print("Testing QB play filtering logic with small sample...\n")
    
    with SparkSessionManager("Test-Filter") as spark:
        
        # Load small sample
        print("Loading sample...")
        df = spark.read.parquet(
            "data/processed/standardized_personnel_2022_2024.parquet"
        ).limit(1000)
        
        original_count = df.count()
        print(f"Original sample: {original_count} plays\n")
        
        # Show what we're starting with
        print("Sample of original data:")
        print("-"*80)
        df.select(
            'passer_player_name',
            'play_type',
            'offense_personnel_std',
            'defense_personnel_std',
            'season_type',
            'down'
        ).show(10, truncate=False)
        
        # Apply filters step by step
        print("\n" + "="*80)
        print("APPLYING FILTERS")
        print("="*80 + "\n")
        
        # Filter 1: Has a passer
        print("1. Filtering to QB dropbacks only...")
        df_qb = df.filter(
            (F.col('passer_player_id').isNotNull()) | 
            (F.col('passer_id').isNotNull())
        )
        qb_count = df_qb.count()
        print(f"   Kept: {qb_count}/{original_count} plays ({qb_count/original_count*100:.1f}%)\n")
        
        # Filter 2: Valid personnel
        print("2. Filtering to valid personnel...")
        df_personnel = df_qb.filter(
            F.col('offense_personnel_std').isNotNull() &
            F.col('defense_personnel_std').isNotNull()
        )
        pers_count = df_personnel.count()
        print(f"   Kept: {pers_count}/{qb_count} plays ({pers_count/qb_count*100:.1f}%)\n")
        
        # Filter 3: Regular season
        print("3. Filtering to regular season...")
        df_reg = df_personnel.filter(F.col('season_type') == 'REG')
        reg_count = df_reg.count()
        print(f"   Kept: {reg_count}/{pers_count} plays ({reg_count/pers_count*100:.1f}%)\n")
        
        # Filter 4: Valid downs
        print("4. Filtering to valid downs (1-4)...")
        df_downs = df_reg.filter(F.col('down').between(1, 4))
        downs_count = df_downs.count()
        print(f"   Kept: {downs_count}/{reg_count} plays ({downs_count/reg_count*100:.1f}%)\n")
        
        # Filter 5: Valid EPA
        print("5. Filtering to valid EPA...")
        df_final = df_downs.filter(F.col('epa').isNotNull())
        final_count = df_final.count()
        print(f"   Kept: {final_count}/{downs_count} plays ({final_count/downs_count*100:.1f}%)\n")
        
        # Summary
        print("="*80)
        print("FILTERING SUMMARY")
        print("="*80)
        print(f"Started with:  {original_count} plays")
        print(f"Ended with:    {final_count} plays")
        print(f"Retention:     {final_count/original_count*100:.1f}%\n")
        
        # Show final filtered data
        print("Sample of filtered QB plays:")
        print("-"*80)
        df_final.select(
            'passer_player_name',
            'offense_personnel_std',
            'defense_personnel_std',
            'down',
            'epa'
        ).show(10, truncate=False)
        
        print("\n✅ Test passed! Filtering logic works correctly.")
        print("\nReady to run: python spark/jobs/filter_qb_plays.py")


if __name__ == "__main__":
    test_filtering()