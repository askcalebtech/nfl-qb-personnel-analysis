"""
Test Join Script

Quick test to verify the join logic works before running the full job.
Uses a small sample to validate faster.
"""

import sys
from pathlib import Path
from pyspark.sql import functions as F

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spark.utils import SparkSessionManager


def test_join():
    """Test the join logic with a small sample."""
    
    print("Testing join logic with small sample...\n")
    
    with SparkSessionManager("Test-Join") as spark:
        
        # Load small samples
        print("Loading samples...")
        pbp = spark.read.parquet("data/raw/play_by_play_2024.parquet").limit(1000)
        part = spark.read.parquet("data/raw/participation_2024.parquet").limit(1000)
        
        print(f"PBP sample: {pbp.count()} rows")
        print(f"Participation sample: {part.count()} rows")
        
        # Check for join keys
        print("\nChecking join keys...")
        print(f"PBP has 'old_game_id': {'old_game_id' in pbp.columns}")
        print(f"PBP has 'play_id': {'play_id' in pbp.columns}")
        print(f"Part has 'old_game_id': {'old_game_id' in part.columns}")
        print(f"Part has 'play_id': {'play_id' in part.columns}")
        
        # Show sample values
        print("\nSample PBP join keys:")
        pbp.select('old_game_id', 'play_id').show(5, truncate=False)
        
        print("Sample Participation join keys:")
        part.select('old_game_id', 'play_id').show(5, truncate=False)
        
        # Attempt join
        print("\nAttempting join...")
        joined = pbp.join(part, on=['old_game_id', 'play_id'], how='inner')
        joined_count = joined.count()
        
        print(f"\n✅ Join successful!")
        print(f"Joined rows: {joined_count}")
        print(f"Join rate: {joined_count/pbp.count()*100:.1f}%")
        
        # Show sample joined data
        print("\nSample joined data:")
        joined.select(
            'old_game_id', 'play_id', 'passer_player_name', 'epa',
            'offense_personnel', 'defense_personnel'
        ).show(10, truncate=False)
        
        print("\n✅ Test passed! Ready to run full join.")


if __name__ == "__main__":
    test_join()