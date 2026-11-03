import numpy as np
import pandas as pd
import pytest

from projections.constants import PARAMS, TEAMS, Params
from projections.ratings import build_ratings, dropbacks, pick_starters, raw_values

# The constants in use before the 2026.1 refit. Kept for tests with hand-computed expected values.
OLD_PARAMS = Params(0.8, 800.0, 0.0150, 1.7, 11.0, 150, -1.5, 3.0, 0.5, 1.0, 25)

COLS = ['game_id', 'season_type', 'posteam', 'defteam', 'pass_attempt', 'sack', 'passing_yards',
        'yards_gained', 'pass_touchdown', 'interception', 'two_point_attempt', 'rush', 'epa',
        'passer_player_name']


def play(**kw):
    row = dict(game_id='g1', season_type='REG', posteam='BUF', defteam='NE', pass_attempt=1, sack=0,
               passing_yards=0.0, yards_gained=0.0, pass_touchdown=0.0, interception=0.0,
               two_point_attempt=0.0, rush=0, epa=0.0, passer_player_name='J.Allen')
    row.update(kw)
    return row


def frame(rows):
    return pd.DataFrame(rows, columns=COLS)


def games(rows):
    return pd.DataFrame(rows, columns=['game_id', 'week', 'home_team', 'away_team', 'result'])


def test_points_formula():
    db = dropbacks(frame([
        play(passing_yards=10.0, pass_touchdown=1.0),             # 10 yds + TD = 30
        play(passing_yards=0.0, interception=1.0),                # INT = -45
        play(pass_attempt=0, sack=1, yards_gained=-7.0),          # sack = -7
    ]))
    assert list(db.pts) == [30.0, -45.0, -7.0]


def test_two_point_tries_excluded():
    db = dropbacks(frame([play(two_point_attempt=1.0), play()]))
    assert len(db) == 1


def test_spikes_count_as_dropbacks():
    db = dropbacks(frame([play(pass_attempt=1, passing_yards=np.nan)]))
    assert len(db) == 1 and db.pts.iloc[0] == 0


def _two_team_pbp():
    return frame([
        play(posteam='BUF', defteam='NE', passing_yards=30.0),
        play(posteam='BUF', defteam='NE', passing_yards=10.0, pass_touchdown=1.0),
        play(posteam='NE', defteam='BUF', passing_yards=5.0, passer_player_name='M.Jones'),
        play(posteam='NE', defteam='BUF', interception=1.0, passer_player_name='M.Jones'),
    ])


def test_raw_values_sum_to_zero():
    raw = raw_values(dropbacks(_two_team_pbp()))
    assert sum(raw.off.values()) == pytest.approx(0, abs=1e-9)
    assert sum(raw.def_.values()) == pytest.approx(0, abs=1e-9)
    assert set(raw.off) == set(TEAMS) and raw.off['KC'] == 0 and raw.off_n['KC'] == 0


def test_raw_values_empty_league_has_no_nan():
    raw = raw_values(dropbacks(frame([])))
    assert raw.lg == 0
    assert all(v == 0 for v in raw.off.values()) and all(v == 0 for v in raw.def_.values())


def test_team_with_no_games_gets_zero_rating_and_no_crash():
    pbp = _two_team_pbp()
    done = games([('g1', 1, 'BUF', 'NE', 3)])
    rs = build_ratings(done, pbp, {}, OLD_PARAMS)
    assert rs.off_pred['KC'] == 0 and rs.def_pred['KC'] == 0
    assert rs.off_season['KC'] == 0 and rs.qb_adj_season['KC'] == 0
    assert rs.starter['KC'] is None
    assert not any(np.isnan(v) for v in rs.off_pred.values())
    assert set(rs.off_pred) == set(TEAMS)


def test_no_data_at_all_does_not_crash():
    rs = build_ratings(games([]), frame([]), {'KC': 'P.Mahomes'}, OLD_PARAMS)
    assert all(v == 0 for v in rs.off_pred.values())
    assert rs.starter['KC'] == 'P.Mahomes' and rs.starter['BUF'] is None


def test_pick_starters_override_and_none():
    pbp = _two_team_pbp()
    db = dropbacks(pbp)
    done = games([('g1', 1, 'BUF', 'NE', 3)])
    s = pick_starters(db, done, {'NE': 'X.Y'})
    assert s['BUF'] == 'J.Allen' and s['NE'] == 'X.Y' and s['KC'] is None
    assert pick_starters(db, done, {'KC': 'P.Mahomes'})['KC'] == 'P.Mahomes'


def test_unknown_starter_override_uses_prior_and_adds_warning():
    pbp = _two_team_pbp()
    done = games([('g1', 1, 'BUF', 'NE', 3)])
    base = build_ratings(done, pbp, {}, OLD_PARAMS)
    rs = build_ratings(done, pbp, {'BUF': 'Z.Nobody'}, OLD_PARAMS)
    assert any("Z.Nobody" in w for w in rs.warnings)
    assert base.warnings == []
    assert rs.starter['BUF'] == 'Z.Nobody'
    assert rs.qb_adj_season['BUF'] != base.qb_adj_season['BUF']


def test_raw_values_do_not_depend_on_params():
    pbp = _two_team_pbp()
    done = games([('g1', 1, 'BUF', 'NE', 3)])
    before = raw_values(dropbacks(pbp))
    for params in (OLD_PARAMS, PARAMS, Params(0.5, 100.0, 0.05, 3.0, 9.0, 50, -3.0, 1.0, 1.0, 2.0, 10)):
        build_ratings(done, pbp, {}, params)
        after = raw_values(dropbacks(pbp))
        assert after.off == before.off and after.def_ == before.def_ and after.lg == before.lg


def test_season_ratings_do_not_depend_on_params_but_prediction_ratings_scale_with_reg():
    pbp = _two_team_pbp()
    done = games([('g1', 1, 'BUF', 'NE', 3)])
    a = build_ratings(done, pbp, {}, OLD_PARAMS)
    b = build_ratings(done, pbp, {}, PARAMS)
    assert a.off_season == b.off_season and a.def_season == b.def_season
    assert a.off_pred == b.off_pred   # same REG in both
    c = build_ratings(done, pbp, {}, Params(0.4, 800.0, 0.01, 2.0, 13.0, 150, -1.5, 3.0, 0.5, 1.0, 25))
    assert c.off_season == a.off_season
    assert c.off_pred['BUF'] == pytest.approx(a.off_pred['BUF']/2)
