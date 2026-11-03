"""Download and load nflverse play-by-play and schedule data."""
import os
import urllib.request

import pandas as pd

BASE = 'https://github.com/nflverse/nflverse-data/releases/download'
PBP_COLS = ['game_id', 'season_type', 'posteam', 'defteam', 'pass_attempt', 'sack', 'passing_yards',
            'yards_gained', 'pass_touchdown', 'interception', 'two_point_attempt', 'rush', 'epa',
            'passer_player_name']


def _urls(season):
    return {'pbp.parquet': f'{BASE}/pbp/play_by_play_{season}.parquet',
            'games.csv': f'{BASE}/schedules/games.csv'}


def download(season: int, data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    for fn, url in _urls(season).items():
        dest = os.path.join(data_dir, fn)
        tmp = dest + '.part'
        with urllib.request.urlopen(url, timeout=120) as resp, open(tmp, 'wb') as f:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(tmp, dest)


def load(season: int, data_dir: str):
    """Return (done, todo, pbp) for regular-season games of `season`."""
    g = pd.read_csv(os.path.join(data_dir, 'games.csv'))
    g = g[(g.season == season) & (g.game_type == 'REG')]
    done = g[g.result.notna()]
    todo = g[g.result.isna()]
    pbp = pd.read_parquet(os.path.join(data_dir, 'pbp.parquet'), columns=PBP_COLS)
    pbp = pbp[(pbp.season_type == 'REG') & pbp.game_id.isin(done.game_id)]
    return done, todo, pbp
