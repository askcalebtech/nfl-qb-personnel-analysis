"""
Data Quality Utility

Provides validation and quality check functions for the data pipeline.
Ensures data integrity at each processing stage.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataQualityChecker:
    """Performs data quality checks on Spark DataFrames."""
    
    def __init__(self, df: DataFrame, dataset_name: str = "Dataset"):
        """
        Initialize quality checker.
        
        Args:
            df: Spark DataFrame to check
            dataset_name: Name for logging/reporting
        """
        self.df = df
        self.dataset_name = dataset_name
        self.issues = []
    
    def check_row_count(self, min_rows: int = 1) -> bool:
        """
        Verify DataFrame has minimum number of rows.
        
        Args:
            min_rows: Minimum expected row count
            
        Returns:
            True if check passes
        """
        row_count = self.df.count()
        
        if row_count < min_rows:
            msg = f"❌ {self.dataset_name}: Only {row_count} rows (expected >= {min_rows})"
            logger.error(msg)
            self.issues.append(msg)
            return False
        
        logger.info(f"✅ {self.dataset_name}: {row_count:,} rows")
        return True
    
    def check_required_columns(self, required_columns: List[str]) -> bool:
        """
        Verify all required columns exist.
        
        Args:
            required_columns: List of column names that must exist
            
        Returns:
            True if all columns present
        """
        missing = set(required_columns) - set(self.df.columns)
        
        if missing:
            msg = f"❌ {self.dataset_name}: Missing columns: {missing}"
            logger.error(msg)
            self.issues.append(msg)
            return False
        
        logger.info(f"✅ {self.dataset_name}: All required columns present")
        return True
    
    def check_null_rates(
        self,
        columns: List[str],
        max_null_rate: float = 0.5
    ) -> Dict[str, float]:
        """
        Check null rates for specified columns.
        
        Args:
            columns: List of columns to check
            max_null_rate: Maximum acceptable null rate (0.0-1.0)
            
        Returns:
            Dict of column -> null_rate
        """
        null_rates = {}
        total_rows = self.df.count()
        
        for col in columns:
            if col not in self.df.columns:
                continue
                
            null_count = self.df.filter(F.col(col).isNull()).count()
            null_rate = null_count / total_rows if total_rows > 0 else 0
            null_rates[col] = null_rate
            
            if null_rate > max_null_rate:
                msg = f"⚠️  {self.dataset_name}.{col}: {null_rate:.1%} null (threshold: {max_null_rate:.1%})"
                logger.warning(msg)
                self.issues.append(msg)
            else:
                logger.info(f"✅ {self.dataset_name}.{col}: {null_rate:.1%} null")
        
        return null_rates
    
    def check_distinct_values(
        self,
        column: str,
        min_distinct: Optional[int] = None,
        max_distinct: Optional[int] = None
    ) -> int:
        """
        Check distinct value count for a column.
        
        Args:
            column: Column name
            min_distinct: Minimum expected distinct values
            max_distinct: Maximum expected distinct values
            
        Returns:
            Count of distinct values
        """
        distinct_count = self.df.select(column).distinct().count()
        
        if min_distinct and distinct_count < min_distinct:
            msg = f"❌ {self.dataset_name}.{column}: Only {distinct_count} distinct values (expected >= {min_distinct})"
            logger.error(msg)
            self.issues.append(msg)
        elif max_distinct and distinct_count > max_distinct:
            msg = f"⚠️  {self.dataset_name}.{column}: {distinct_count} distinct values (expected <= {max_distinct})"
            logger.warning(msg)
            self.issues.append(msg)
        else:
            logger.info(f"✅ {self.dataset_name}.{column}: {distinct_count} distinct values")
        
        return distinct_count
    
    def check_value_range(
        self,
        column: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> tuple:
        """
        Check numeric column is within expected range.
        
        Args:
            column: Column name
            min_value: Minimum expected value
            max_value: Maximum expected value
            
        Returns:
            Tuple of (actual_min, actual_max)
        """
        stats = self.df.agg(
            F.min(column).alias('min'),
            F.max(column).alias('max')
        ).collect()[0]
        
        actual_min = stats['min']
        actual_max = stats['max']
        
        if min_value is not None and actual_min < min_value:
            msg = f"⚠️  {self.dataset_name}.{column}: Min value {actual_min} < expected {min_value}"
            logger.warning(msg)
            self.issues.append(msg)
        
        if max_value is not None and actual_max > max_value:
            msg = f"⚠️  {self.dataset_name}.{column}: Max value {actual_max} > expected {max_value}"
            logger.warning(msg)
            self.issues.append(msg)
        
        logger.info(f"✅ {self.dataset_name}.{column}: Range [{actual_min}, {actual_max}]")
        return actual_min, actual_max
    
    def check_join_rate(
        self,
        left_count: int,
        joined_count: int,
        min_rate: float = 0.8
    ) -> float:
        """
        Check join success rate.
        
        Args:
            left_count: Count from left DataFrame
            joined_count: Count after join
            min_rate: Minimum acceptable join rate
            
        Returns:
            Join rate (0.0-1.0)
        """
        join_rate = joined_count / left_count if left_count > 0 else 0
        
        if join_rate < min_rate:
            msg = f"⚠️  {self.dataset_name}: Join rate {join_rate:.1%} < threshold {min_rate:.1%}"
            logger.warning(msg)
            self.issues.append(msg)
        else:
            logger.info(f"✅ {self.dataset_name}: Join rate {join_rate:.1%}")
        
        return join_rate
    
    def get_summary(self) -> Dict:
        """
        Get summary of all quality checks.
        
        Returns:
            Dict with summary statistics
        """
        return {
            'dataset': self.dataset_name,
            'row_count': self.df.count(),
            'column_count': len(self.df.columns),
            'issues': self.issues,
            'passed': len(self.issues) == 0
        }
    
    def print_summary(self):
        """Print formatted summary of quality checks."""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print(f"DATA QUALITY SUMMARY: {summary['dataset']}")
        print("="*60)
        print(f"Rows: {summary['row_count']:,}")
        print(f"Columns: {summary['column_count']}")
        print(f"Issues Found: {len(summary['issues'])}")
        
        if summary['issues']:
            print("\nIssues:")
            for issue in summary['issues']:
                print(f"  {issue}")
        
        status = "✅ PASSED" if summary['passed'] else "❌ FAILED"
        print(f"\nStatus: {status}")
        print("="*60 + "\n")


def validate_play_by_play(df: DataFrame) -> DataQualityChecker:
    """
    Run standard validation checks on play-by-play data.
    
    Args:
        df: Play-by-play DataFrame
        
    Returns:
        DataQualityChecker with results
    """
    checker = DataQualityChecker(df, "Play-by-Play")
    
    # Basic checks
    checker.check_row_count(min_rows=10000)
    checker.check_required_columns([
        'game_id', 'play_id', 'posteam', 'defteam',
        'epa', 'season', 'week'
    ])
    
    # Null rate checks
    checker.check_null_rates(['epa', 'play_type'], max_null_rate=0.1)
    
    # Value range checks
    checker.check_value_range('epa', min_value=-15, max_value=15)
    checker.check_value_range('season', min_value=2016, max_value=2030)
    
    # Distinct value checks
    checker.check_distinct_values('game_id', min_distinct=200)
    
    return checker


def validate_participation(df: DataFrame) -> DataQualityChecker:
    """
    Run standard validation checks on participation data.
    
    Args:
        df: Participation DataFrame
        
    Returns:
        DataQualityChecker with results
    """
    checker = DataQualityChecker(df, "Participation")
    
    # Basic checks
    checker.check_row_count(min_rows=10000)
    checker.check_required_columns([
        'old_game_id', 'play_id', 'offense_personnel', 'defense_personnel'
    ])
    
    # Null rate checks
    checker.check_null_rates(
        ['offense_personnel', 'defense_personnel'],
        max_null_rate=0.2
    )
    
    return checker


if __name__ == "__main__":
    print("Data Quality Utility - Test Mode")
    print("This module is designed to be imported by Spark jobs.")
    print("\nExample usage:")
    print("""
    from spark.utils.data_quality import validate_play_by_play
    
    # In your Spark job:
    df = spark.read.parquet("data/raw/play_by_play_2024.parquet")
    checker = validate_play_by_play(df)
    checker.print_summary()
    """)