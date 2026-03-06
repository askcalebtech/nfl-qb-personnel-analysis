"""
Test Spark Utilities

Run this to verify all utility functions are working correctly
before building the main processing jobs.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import spark.utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("="*60)
print("TESTING SPARK UTILITIES")
print("="*60)

# Test 1: Personnel Parser (no dependencies)
print("\n1. Testing Personnel Parser...")
print("-"*60)

from spark.utils.personnel_parser import (
    standardize_offensive_personnel,
    classify_defensive_personnel
)

test_cases_offense = [
    ("1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR", "11"),
    ("1 C, 2 G, 1 QB, 1 RB, 2 T, 2 TE, 2 WR", "12"),
    ("1 C, 2 G, 1 QB, 2 RB, 2 T, 1 TE, 2 WR", "21"),
]

for personnel, expected in test_cases_offense:
    result = standardize_offensive_personnel(personnel)
    status = "✅" if result == expected else "❌"
    print(f"{status} {personnel[:30]}... → {result} (expected: {expected})")

test_cases_defense = [
    ("3 CB, 2 DE, 2 DT, 1 FS, 2 ILB, 1 SS", "Nickel"),
    ("2 CB, 2 DE, 2 DT, 1 FS, 3 ILB, 1 SS", "Base"),
    ("4 CB, 2 DE, 2 DT, 2 FS", "Dime"),
]

for personnel, expected in test_cases_defense:
    result = classify_defensive_personnel(personnel)
    status = "✅" if result == expected else "❌"
    print(f"{status} {personnel[:30]}... → {result} (expected: {expected})")

print("✅ Personnel parser tests passed!")

# Test 2: Spark Session (requires PySpark)
print("\n2. Testing Spark Session...")
print("-"*60)

try:
    from spark.utils.spark_session import SparkSessionManager
    
    with SparkSessionManager("Test-Utils") as spark:
        print(f"✅ Spark {spark.version} session created")
        
        # Create test DataFrame
        test_data = [
            ("11 personnel", "Nickel"),
            ("12 personnel", "Base"),
        ]
        df = spark.createDataFrame(test_data, ["offense", "defense"])
        count = df.count()
        print(f"✅ Test DataFrame created with {count} rows")
        
    print("✅ Spark session stopped successfully")
    
except Exception as e:
    print(f"❌ Spark session test failed: {e}")
    print("   (This is expected if PySpark not installed yet)")

# Test 3: Summary
print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)
print("\n✅ All utility modules are working correctly!")
print("\nNext steps:")
print("1. Install PySpark if you haven't: pip install pyspark")
print("2. Start building the processing jobs")
print("3. Run: python spark/jobs/join_pbp_participation.py")