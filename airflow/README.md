# Airflow — NFL QB Personnel Pipeline

## Overview

A single DAG (`nfl_qb_pipeline`) that runs the full data pipeline in order:

```
extract_data → join_pbp_participation → standardize_personnel → filter_qb_plays → load_to_sqlite → dbt_run
```

Scheduled weekly. Each task uses `BashOperator` to invoke the existing Spark jobs and dbt directly.

---

## Local Setup (airflow standalone)

### 1. Install Airflow

```bash
pip install --break-system-packages "apache-airflow==2.9.3" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.9.txt"
```

### 2. Set AIRFLOW_HOME to this directory

```bash
export AIRFLOW_HOME=/Users/calebsherman/Documents/Projects/nfl-qb-personnell-analysis/airflow
```

Add this to your `~/.zshrc` to persist it across sessions.

### 3. Initialize and start

```bash
airflow standalone
```

`airflow standalone` initialises the database, creates an admin user, and starts the webserver + scheduler in a single process. The admin password is printed to stdout on first run.

Open [http://localhost:8080](http://localhost:8080) and log in with `admin` / `<printed password>`.

### 4. Enable the DAG

The DAG is paused by default. Toggle it on in the UI, or:

```bash
airflow dags unpause nfl_qb_pipeline
```

---

## Manual trigger

```bash
airflow dags trigger nfl_qb_pipeline
```

Or use the "Trigger DAG" button in the UI.

---

## Notes

- Spark tasks require Java 17 and Python 3.9. The DAG sets `JAVA_HOME`, `PYSPARK_PYTHON`, and `PYSPARK_DRIVER_PYTHON` automatically via the `BashOperator` command prefix — no shell configuration needed.
- The `airflow/config/` directory can hold `airflow.cfg` overrides if needed.
- `catchup=False` means only the most recent interval runs when the DAG is first enabled; historical backfill is skipped.
- `retries=1` with a 5-minute delay covers transient download failures in `extract_data`. Spark jobs are idempotent (output files are overwritten), so retries are safe.
