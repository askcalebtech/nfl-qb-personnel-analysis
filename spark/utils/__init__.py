"""
Spark Utilities Package

Reusable utilities for NFL QB Personnel Analysis Spark jobs.
"""

from .spark_session import get_spark_session, stop_spark_session, SparkSessionManager
from .personnel_parser import (
    standardize_offensive_personnel,
    classify_defensive_personnel,
    parse_position_counts,
    standardize_personnel_batch
)
from .data_quality import (
    DataQualityChecker,
    validate_play_by_play,
    validate_participation
)

__all__ = [
    # Spark session
    'get_spark_session',
    'stop_spark_session',
    'SparkSessionManager',
    
    # Personnel parsing
    'standardize_offensive_personnel',
    'classify_defensive_personnel',
    'parse_position_counts',
    'standardize_personnel_batch',
    
    # Data quality
    'DataQualityChecker',
    'validate_play_by_play',
    'validate_participation',
]

__version__ = '0.1.0'