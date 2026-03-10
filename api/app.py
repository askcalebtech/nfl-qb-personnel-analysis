"""
NFL QB Personnel Analysis API

Serves data from the dbt-built SQLite tables:
  - dim_qbs               — QB dimension (one row per QB, career aggregates)
  - fct_qb_personnel_stats — QB stats by season + personnel matchup
  - fct_league_trends      — League-wide trends by season + matchup
"""

import math
import os
import sqlite3
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
DB_PATH = Path(os.getenv("DATABASE_URL", str(BASE_DIR / "data" / "analytics" / "nfl_qb_analysis.db")))


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# App + CORS
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NFL QB Personnel Analysis",
    description="Analyze QB performance across offensive/defensive personnel matchups (2022-2025).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class QB(BaseModel):
    qb_id: str
    qb_name: Optional[str] = None
    first_season: Optional[int] = None
    last_season: Optional[int] = None
    seasons_played: Optional[int] = None
    career_plays: Optional[int] = None
    career_pass_attempts: Optional[int] = None
    career_sacks: Optional[int] = None
    career_scrambles: Optional[int] = None
    career_qb_rushes: Optional[int] = None
    career_epa_per_play: Optional[float] = None
    career_success_rate: Optional[float] = None
    career_total_epa: Optional[float] = None
    career_total_yards: Optional[float] = None
    unique_matchups_faced: Optional[int] = None
    unique_offense_personnel: Optional[int] = None
    unique_defense_personnel: Optional[int] = None
    best_matchup_epa: Optional[float] = None
    career_epa_percentile: Optional[float] = None
    plays_rank: Optional[int] = None
    is_starter: Optional[bool] = None


class QBStats(BaseModel):
    qb_id: str
    qb_name: Optional[str] = None
    season: Optional[str] = None
    team: Optional[str] = None
    offense_personnel: Optional[str] = None
    defense_personnel: Optional[str] = None
    personnel_matchup: Optional[str] = None
    play_count: Optional[int] = None
    pass_attempts: Optional[int] = None
    sacks: Optional[int] = None
    scrambles: Optional[int] = None
    qb_rushes: Optional[int] = None
    epa_per_play: Optional[float] = None
    total_epa: Optional[float] = None
    success_rate: Optional[float] = None
    avg_yards: Optional[float] = None
    total_yards: Optional[float] = None
    avg_cpoe: Optional[float] = None
    avg_air_epa: Optional[float] = None
    avg_yac_epa: Optional[float] = None
    avg_wpa: Optional[float] = None
    meets_min_threshold: Optional[bool] = None
    meets_starter_threshold: Optional[bool] = None


class LeagueTrend(BaseModel):
    season: Optional[str] = None
    offense_personnel: Optional[str] = None
    defense_personnel: Optional[str] = None
    personnel_matchup: Optional[str] = None
    league_play_count: Optional[int] = None
    qbs_used_matchup: Optional[int] = None
    league_epa_per_play: Optional[float] = None
    league_epa_std_dev: Optional[float] = None
    league_success_rate: Optional[float] = None
    league_pass_rate: Optional[float] = None
    league_pass_plays: Optional[int] = None
    league_run_plays: Optional[int] = None
    league_avg_yards: Optional[float] = None
    league_avg_cpoe: Optional[float] = None
    usage_pct: Optional[float] = None
    usage_rank: Optional[int] = None
    usage_pct_change_yoy: Optional[float] = None
    epa_change_yoy: Optional[float] = None


class LeaderboardEntry(BaseModel):
    qb_id: str
    qb_name: Optional[str] = None
    season: Optional[str] = None
    team: Optional[str] = None
    play_count: Optional[int] = None
    epa_per_play: Optional[float] = None
    success_rate: Optional[float] = None
    pass_attempts: Optional[int] = None
    sacks: Optional[int] = None
    scrambles: Optional[int] = None
    avg_cpoe: Optional[float] = None
    rank: int
    min_plays_threshold: int


class QBRanking(BaseModel):
    qb_id: str
    qb_name: Optional[str] = None
    season: str
    total_plays: Optional[int] = None
    epa_per_play: Optional[float] = None
    success_rate: Optional[float] = None
    pass_attempts: Optional[int] = None
    is_starter: Optional[bool] = None


class HealthResponse(BaseModel):
    status: str
    db_path: str
    db_reachable: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health():
    """Liveness + DB reachability check."""
    try:
        conn = get_db()
        conn.execute("SELECT 1 FROM dim_qbs LIMIT 1").fetchone()
        conn.close()
        return HealthResponse(status="ok", db_path=str(DB_PATH), db_reachable=True)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB unavailable: {exc}")


@app.get("/qbs", response_model=List[QB], tags=["qbs"])
def list_qbs():
    """Return all QBs from dim_qbs, ordered by career play volume."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM dim_qbs WHERE qb_id IS NOT NULL AND qb_id != '' ORDER BY career_plays DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/qbs/{qb_id}/stats", response_model=List[QBStats], tags=["qbs"])
def qb_stats(
    qb_id: str,
    season: Optional[str] = Query(None, description="Filter by season, e.g. 2024"),
    min_plays: Optional[int] = Query(None, description="Minimum play count threshold"),
):
    """Return a QB's stats broken down by personnel matchup.

    Raises 404 if the QB ID is not found in dim_qbs.
    """
    conn = get_db()

    exists = conn.execute(
        "SELECT 1 FROM dim_qbs WHERE qb_id = ?", (qb_id,)
    ).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail=f"QB '{qb_id}' not found")

    sql = "SELECT * FROM fct_qb_personnel_stats WHERE qb_id = ?"
    params: list = [qb_id]

    if season is not None:
        sql += " AND season = ?"
        params.append(season)
    if min_plays is not None:
        sql += " AND play_count >= ?"
        params.append(min_plays)

    sql += " ORDER BY season DESC, play_count DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/trends", response_model=List[LeagueTrend], tags=["trends"])
def trends(
    season: Optional[str] = Query(None, description="Filter by season, e.g. 2024"),
):
    """Return league-wide personnel usage and performance trends."""
    conn = get_db()

    sql = "SELECT * FROM fct_league_trends"
    params: list = []

    if season is not None:
        sql += " WHERE season = ?"
        params.append(season)

    sql += " ORDER BY season DESC, league_play_count DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/rankings", response_model=List[QBRanking], tags=["qbs"])
def rankings(
    season: str = Query(..., description="Season to rank QBs for, e.g. 2024"),
    min_plays: int = Query(20, description="Minimum total plays to qualify"),
):
    """Return all QBs ranked by EPA/play for a given season.

    Aggregates fct_qb_personnel_stats across all matchups using weighted averages.
    Only QBs meeting min_plays threshold are included.
    """
    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            f.qb_id,
            f.qb_name,
            f.season,
            SUM(f.play_count)                                         AS total_plays,
            SUM(f.epa_per_play * f.play_count) / SUM(f.play_count)   AS epa_per_play,
            SUM(f.success_rate * f.play_count) / SUM(f.play_count)   AS success_rate,
            SUM(f.pass_attempts)                                      AS pass_attempts,
            d.is_starter
        FROM fct_qb_personnel_stats f
        LEFT JOIN dim_qbs d ON f.qb_id = d.qb_id
        WHERE f.season = ?
          AND f.qb_id IS NOT NULL
          AND f.qb_id != ''
        GROUP BY f.qb_id, f.qb_name, f.season, d.is_starter
        HAVING SUM(f.play_count) >= ?
        ORDER BY epa_per_play DESC
        """,
        (season, min_plays),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/leaderboard", response_model=List[LeaderboardEntry], tags=["leaderboard"])
def leaderboard(
    season: str = Query(..., description="Season, e.g. 2024"),
    matchup: str = Query(..., description="Personnel matchup with underscores, e.g. 11_vs_Nickel"),
):
    """Return QB leaderboard for a specific season and personnel matchup.

    The minimum plays threshold is the 40th percentile of play_count for that
    matchup/season. Only QBs at or above the threshold are included.
    Each row includes rank (1-indexed, ordered by EPA/play desc) and the threshold value.
    """
    matchup_str = matchup.replace("_", " ")
    conn = get_db()

    all_rows = conn.execute(
        """
        SELECT qb_id, qb_name, season, team,
               play_count, epa_per_play, success_rate, pass_attempts,
               sacks, scrambles, avg_cpoe
        FROM fct_qb_personnel_stats
        WHERE season = ?
          AND personnel_matchup = ?
          AND qb_id IS NOT NULL
          AND qb_id != ''
        """,
        (season, matchup_str),
    ).fetchall()
    conn.close()

    if not all_rows:
        return []

    play_counts = sorted(r["play_count"] for r in all_rows if r["play_count"] is not None)
    if not play_counts:
        return []

    # 40th percentile (ceiling index, 1-based → 0-based)
    threshold_idx = max(0, math.ceil(len(play_counts) * 0.4) - 1)
    threshold = play_counts[threshold_idx]

    qualified = sorted(
        [r for r in all_rows if (r["play_count"] or 0) >= threshold],
        key=lambda r: r["epa_per_play"] if r["epa_per_play"] is not None else -999,
        reverse=True,
    )

    return [
        {**dict(r), "rank": i + 1, "min_plays_threshold": threshold}
        for i, r in enumerate(qualified)
    ]


@app.get("/matchup/{matchup}", response_model=List[QBStats], tags=["matchup"])
def matchup_stats(
    matchup: str,
    season: Optional[str] = Query(None, description="Filter by season, e.g. 2024"),
):
    """Return all QB stats for a specific personnel matchup.

    Pass the matchup with underscores in place of spaces, e.g. `11_vs_Nickel`.
    Raises 404 if the matchup string is not found.
    """
    # Convert URL-safe underscores → DB format spaces: "11_vs_Nickel" → "11 vs Nickel"
    matchup_str = matchup.replace("_", " ")

    conn = get_db()

    sql = "SELECT * FROM fct_qb_personnel_stats WHERE personnel_matchup = ? AND qb_id IS NOT NULL AND qb_id != ''"
    params: list = [matchup_str]

    if season is not None:
        sql += " AND season = ?"
        params.append(season)

    sql += " ORDER BY epa_per_play DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Matchup '{matchup_str}' not found. "
            "Use underscores for spaces, e.g. 11_vs_Nickel.",
        )

    return [dict(r) for r in rows]
