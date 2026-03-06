"""
NFL QB Personnel Analysis Pipeline DAG

Runs the full data pipeline weekly:
  extract_data → join_pbp_participation → standardize_personnel
      → filter_qb_plays → load_to_sqlite → dbt_run

All Spark jobs use Python 3.9 and Java 17 (required by PySpark).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/Users/calebsherman/Documents/Projects/nfl-qb-personnell-analysis"
PYTHON = "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9"
DBT = "/Users/calebsherman/Library/Python/3.9/bin/dbt"

# Environment variables required by PySpark on this machine (M1, Java 17)
SPARK_ENV = (
    "JAVA_HOME=/opt/homebrew/opt/openjdk@17 "
    "PYSPARK_PYTHON={python} "
    "PYSPARK_DRIVER_PYTHON={python} "
).format(python=PYTHON)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="nfl_qb_pipeline",
    default_args=default_args,
    description="Full NFL QB personnel analysis pipeline: extract → transform → dbt",
    schedule_interval="@weekly",
    catchup=False,
    tags=["nfl", "qb", "personnel"],
) as dag:

    extract_data = BashOperator(
        task_id="extract_data",
        bash_command=(
            f"{SPARK_ENV} {PYTHON} {PROJECT_DIR}/spark/jobs/extract_nflfastr.py"
        ),
    )

    join_pbp_participation = BashOperator(
        task_id="join_pbp_participation",
        bash_command=(
            f"{SPARK_ENV} {PYTHON} {PROJECT_DIR}/spark/jobs/join_pbp_participation.py"
        ),
    )

    standardize_personnel = BashOperator(
        task_id="standardize_personnel",
        bash_command=(
            f"{SPARK_ENV} {PYTHON} {PROJECT_DIR}/spark/jobs/standardize_personnel.py"
        ),
    )

    filter_qb_plays = BashOperator(
        task_id="filter_qb_plays",
        bash_command=(
            f"{SPARK_ENV} {PYTHON} {PROJECT_DIR}/spark/jobs/filter_qb_plays.py"
        ),
    )

    load_to_sqlite = BashOperator(
        task_id="load_to_sqlite",
        bash_command=(
            f"{PYTHON} {PROJECT_DIR}/load_to_sqlite.py"
        ),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {PROJECT_DIR}/dbt_project && {DBT} run --profiles-dir ."
        ),
    )

    (
        extract_data
        >> join_pbp_participation
        >> standardize_personnel
        >> filter_qb_plays
        >> load_to_sqlite
        >> dbt_run
    )
