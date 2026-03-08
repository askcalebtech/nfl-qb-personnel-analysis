# Environment Setup Guide

This guide walks through setting up your local environment to run the NFL QB Personnel
Analysis pipeline from scratch. Follow these steps in order before attempting to run
any pipeline commands.

---

## System Requirements

- **OS:** macOS (tested on M1/M2 Mac) or Linux
- **Python:** 3.9.x (3.9.13 recommended — see below for why)
- **Java:** 17 (required for PySpark)
- **Disk space:** ~5GB for raw data files
- **RAM:** 8GB minimum, 16GB+ recommended

---

## A Note on Python Commands

Depending on your system configuration, Python may be invoked as either `python` or
`python3`, and pip as either `pip` or `pip3`. Throughout this guide and the project
generally:

- If `python --version` returns Python 3.x, use `python` and `pip`
- If `python --version` returns Python 2.x or "command not found", use `python3` and `pip3`

To check which you have:

```bash
python --version
python3 --version
```

Use whichever returns a 3.x version. The rest of this guide uses `python` and `pip`
for brevity — substitute `python3` and `pip3` if needed on your system.

---

## Step 1 — Install pyenv

pyenv lets you install and switch between multiple Python versions without affecting
your system Python. This is the recommended approach for this project.

**macOS (using Homebrew):**

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install pyenv
brew install pyenv
```

**Add pyenv to your shell** (add these lines to `~/.zshrc` or `~/.bashrc`):

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

Then reload your shell:

```bash
source ~/.zshrc   # or source ~/.bashrc
```

Verify pyenv is installed:

```bash
pyenv --version
```

---

## Step 2 — Install Python 3.9.13

**Why 3.9.13 specifically?**

Several packages in `requirements.txt` have version constraints that conflict with
Python 3.10+. In particular:

- PySpark 3.5.0 has compatibility issues with Python 3.12+
- Some dbt-sqlite dependencies don't support Python 3.14
- Apache Airflow 2.9.3 requires Python 3.8–3.11

Python 3.9.13 is the version this project was developed and tested on. Using a
different 3.9.x patch version (e.g. 3.9.18) should also work, but 3.9.13 is
guaranteed compatible.

```bash
# Install Python 3.9.13
pyenv install 3.9.13

# Set it as the local version for this project
cd ~/path/to/nfl-qb-personnell-analysis
pyenv local 3.9.13

# Verify the correct version is active
python --version
# Should output: Python 3.9.13
```

The `pyenv local` command creates a `.python-version` file in the project directory.
Any time you `cd` into the project, pyenv will automatically use 3.9.13.

---

## Step 3 — Install Java 17

PySpark requires Java. Java 17 is the recommended version.

```bash
# macOS (using Homebrew)
brew install openjdk@17

# Add to your PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"

# Reload shell
source ~/.zshrc

# Verify
java -version
# Should output: openjdk version "17.x.x"
```

**Note for M1/M2 Mac users:** If Homebrew is installed at `/usr/local` instead of
`/opt/homebrew`, adjust the paths above accordingly. Run `brew --prefix openjdk@17`
to find the correct path on your machine.

---

## Step 4 — Clone the Repository

```bash
git clone https://github.com/askcalebtech/nfl-qb-personnell-analysis.git
cd nfl-qb-personnell-analysis

# Confirm Python version is correct
python --version
# Should output: Python 3.9.13
```

---

## Step 5 — Install Python Dependencies

This project does not use a virtual environment — packages are installed directly.
The `--break-system-packages` flag is required on some systems (particularly macOS
with Homebrew-managed Python).

```bash
pip install -r requirements.txt --break-system-packages
```

**If you see permission errors**, try:

```bash
pip install -r requirements.txt --user
```

**If specific packages fail**, the most common culprit is a Python version mismatch.
Double-check that `python --version` returns 3.9.13 before retrying.

**Verify key packages installed correctly:**

```bash
python -c "import pyspark; print(pyspark.__version__)"
# Should output: 3.5.0

python -c "import dbt; print(dbt.__version__)"
# Should output: 1.5.11 (or similar 1.5.x)

python -c "import fastapi; print(fastapi.__version__)"
# Should output: 0.135.1 (or similar)
```

---

## Step 6 — Configure dbt

dbt needs to know where your SQLite database lives. The connection is configured via
`profiles.yml`, which is gitignored (it contains an absolute path specific to your
machine).

```bash
# Copy the example file
cp dbt_project/profiles.yml.example dbt_project/profiles.yml
```

Open `dbt_project/profiles.yml` and replace the placeholder path with the absolute
path to your project:

```yaml
# Replace this:
schemas_and_paths:
  main: '/absolute/path/to/nfl-qb-personnell-analysis/data/analytics/nfl_qb_analysis.db'
schema_directory: '/absolute/path/to/nfl-qb-personnell-analysis/data/analytics'

# With your actual path, e.g.:
schemas_and_paths:
  main: '/Users/yourname/Documents/Projects/nfl-qb-personnell-analysis/data/analytics/nfl_qb_analysis.db'
schema_directory: '/Users/yourname/Documents/Projects/nfl-qb-personnell-analysis/data/analytics'
```

To find your absolute path:

```bash
pwd
# Copy the output and append /data/analytics/nfl_qb_analysis.db
```

Test the dbt connection:

```bash
cd dbt_project
dbt debug --profiles-dir .
cd ..
```

You should see `All checks passed!`. If you see a connection error, double-check the
paths in `profiles.yml`.

---

## Step 7 — Verify Spark Works

Before running the full pipeline, confirm Spark can start on your machine:

```bash
python spark/utils/test_utils.py
```

You should see:

```
✅ Spark 3.5.x session created
✅ Test DataFrame created with 2 rows
✅ Spark session stopped successfully
```

**Common Spark issues:**

- `JAVA_HOME not set` — Java isn't in your PATH. Re-run Step 3 and reload your shell.
- `py4j` errors — usually a Python/PySpark version mismatch. Confirm Python is 3.9.13.
- Memory errors — the default config uses 8GB. If your machine has less RAM, edit
  `spark/utils/spark_session.py` and reduce `spark.driver.memory` and
  `spark.executor.memory` to `4g`.

---

## Step 8 — Run the Pipeline

Once all the above is verified, you're ready to run the full pipeline:

```bash
# 1. Download raw data (~5 min)
python spark/jobs/extract_nflfastr.py

# 2. Join datasets (~2-3 min)
python spark/jobs/join_pbp_participation.py

# 3. Standardize personnel notation (~1-2 min)
python spark/jobs/standardize_personnel.py

# 4. Filter to QB plays (~1 min)
python spark/jobs/filter_qb_plays.py

# 5. Load to SQLite (~30 sec)
python load_to_sqlite.py

# 6. Run dbt
cd dbt_project && dbt run --profiles-dir . && cd ..

# 7. Verify with dbt tests
cd dbt_project && dbt test --profiles-dir . && cd ..
```

---

## Step 9 — Run the API

```bash
pip install -r api/requirements.txt --break-system-packages
uvicorn api.app:app --reload
```

Visit `http://localhost:8000/health` — you should see:

```json
{"status": "ok", "db_reachable": true}
```

---

## Step 10 — Run the Frontend (Optional)

The frontend requires Node.js 18+.

```bash
# Check Node version
node --version
# Should be v18.x.x or higher

# If not installed, use Homebrew:
brew install node

# Install frontend dependencies
cd frontend
npm install

# Start dev server (requires API to be running)
npm run dev
```

Visit `http://localhost:3000/dashboard`.

**Note:** The API must be running at `http://localhost:8000` for the frontend to
load data. Start the API in a separate terminal tab before launching the frontend.

---

## Troubleshooting Quick Reference

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `python: command not found` | System uses `python3` | Use `python3` and `pip3` instead |
| `ModuleNotFoundError` after install | Wrong Python version active | Run `python --version`, confirm 3.9.13 |
| PySpark won't start | Java not found | Verify `java -version` works, check `JAVA_HOME` |
| `dbt debug` fails | Wrong path in `profiles.yml` | Re-check absolute path with `pwd` |
| Low join rate (<85%) | Incomplete participation data | Check nflfastR releases for updated file |
| `pip install` permission error | System Python conflict | Add `--user` flag or `--break-system-packages` |
| Port 8000 already in use | Another process running | Kill it with `lsof -ti:8000 \| xargs kill` |
| Port 3000 already in use | Another process running | Kill it with `lsof -ti:3000 \| xargs kill` |
