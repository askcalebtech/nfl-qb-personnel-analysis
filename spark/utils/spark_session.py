"""
Spark Session Utility

Provides a reusable Spark session configuration for all processing jobs.
Ensures consistent settings across the pipeline.
"""

from pyspark.sql import SparkSession
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_spark_session(
    app_name: str = "NFL-QB-Personnel-Analysis",
    master: str = "local[*]",
    log_level: str = "WARN",
    additional_config: Optional[dict] = None
) -> SparkSession:
    """
    Create or get existing Spark session with standard configuration.
    
    Args:
        app_name: Name for the Spark application
        master: Spark master URL (default: local[*] uses all cores)
        log_level: Logging level (ERROR, WARN, INFO, DEBUG)
        additional_config: Optional dict of additional Spark configs
        
    Returns:
        Configured SparkSession
        
    Example:
        spark = get_spark_session(app_name="Join-PBP-Participation")
    """
    logger.info(f"Initializing Spark session: {app_name}")
    
    # Base configuration optimized for M1 Mac with 32GB RAM
    builder = SparkSession.builder \
        .appName(app_name) \
        .master(master) \
        .config("spark.sql.parquet.enableVectorizedReader", "true") \
        .config("spark.sql.shuffle.partitions", "8") \
        .config("spark.driver.memory", "8g") \
        .config("spark.executor.memory", "8g") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    # Add any additional configurations
    if additional_config:
        for key, value in additional_config.items():
            builder = builder.config(key, value)
    
    # Create session
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel(log_level)
    
    logger.info(f"Spark session created: {spark.version}")
    logger.info(f"Master: {spark.sparkContext.master}")
    
    return spark


def stop_spark_session(spark: SparkSession) -> None:
    """
    Gracefully stop the Spark session.
    
    Args:
        spark: SparkSession to stop
    """
    logger.info("Stopping Spark session...")
    spark.stop()
    logger.info("Spark session stopped")


# Context manager for automatic cleanup
class SparkSessionManager:
    """
    Context manager for Spark sessions with automatic cleanup.
    
    Usage:
        with SparkSessionManager("MyApp") as spark:
            df = spark.read.parquet("data.parquet")
            # ... do work ...
        # Session automatically stopped
    """
    
    def __init__(
        self,
        app_name: str = "NFL-QB-Personnel-Analysis",
        master: str = "local[*]",
        log_level: str = "WARN"
    ):
        self.app_name = app_name
        self.master = master
        self.log_level = log_level
        self.spark = None
    
    def __enter__(self) -> SparkSession:
        self.spark = get_spark_session(
            app_name=self.app_name,
            master=self.master,
            log_level=self.log_level
        )
        return self.spark
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.spark:
            stop_spark_session(self.spark)
        return False


if __name__ == "__main__":
    # Test the Spark session
    print("Testing Spark session creation...")
    
    with SparkSessionManager("Test-Session") as spark:
        print(f"✅ Spark {spark.version} session created successfully")
        print(f"Master: {spark.sparkContext.master}")
        
        # Create a simple test DataFrame
        test_data = [
            ("Josh Allen", "BUF", 0.35),
            ("Patrick Mahomes", "KC", 0.28),
            ("Lamar Jackson", "BAL", 0.32)
        ]
        df = spark.createDataFrame(test_data, ["qb", "team", "epa"])
        df.show()
    
    print("✅ Spark session stopped successfully")