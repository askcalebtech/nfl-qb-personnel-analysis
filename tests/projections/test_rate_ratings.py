import pytest
from pytest import approx

from projections.constants import DB_PER_GAME, LEGACY_PARAMS
from projections.game_model import predict
from projections.ratings import build_ratings_rate, dropbacks, raw_values
from tests.projections.test_ratings import frame, games, play


def _season(n_games, extra=0):
    """A and B each play a clone game n_games times at identical per-dropback rates (A: 30 yd, B: 10 yd)."""
    rows, g = [], []
    for i in range(n_games):
        gid = f'g{i}'
        g.append((gid, i + 1, 'BUF', 'NE', 3))
        rows += [play(game_id=gid, posteam='BUF', defteam='NE', passing_yards=30.0) for _ in range(3 + extra)]
        rows += [play(game_id=gid, posteam='NE', defteam='BUF', passing_yards=10.0,
                      passer_player_name='M.Jones') for _ in range(3 + extra)]
    return games(g), frame(rows)


def test_same_rate_different_game_counts_same_prediction_rating():
    d7, p7 = _season(7)
    d8, p8 = _season(8)
    a = build_ratings_rate(d7, p7, {}, LEGACY_PARAMS, None)
    b = build_ratings_rate(d8, p8, {}, LEGACY_PARAMS, None)
    assert a.off_pred['BUF'] == approx(b.off_pred['BUF'])
    assert a.def_pred['NE'] == approx(b.def_pred['NE'])


def test_prediction_rating_does_not_grow_with_season_length():
    d4, p4 = _season(4)
    d8, p8 = _season(8)
    a = build_ratings_rate(d4, p4, {}, LEGACY_PARAMS, None)
    b = build_ratings_rate(d8, p8, {}, LEGACY_PARAMS, None)
    assert b.off_pred['BUF'] == approx(a.off_pred['BUF'])
    assert b.off_season['BUF'] == approx(2 * a.off_season['BUF'])


def test_season_values_scale_with_dropbacks():
    done, pbp = _season(5)
    rs = build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, None)
    raw = raw_values(dropbacks(pbp))
    rate = rs.off_season['BUF'] / raw.off_n['BUF']
    assert rs.off_season['BUF'] == approx(rate * 15)
    assert rate > 0
    # two equal-sized units with opposite rates are symmetric
    assert rs.off_season['NE'] == approx(-rs.off_season['BUF'])


def test_raw_values_unchanged_by_rate_build():
    done, pbp = _season(3)
    before = raw_values(dropbacks(pbp))
    build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, 100.0)
    after = raw_values(dropbacks(pbp))
    assert before.off == after.off and before.def_ == after.def_ and before.lg == after.lg


def test_week_one_all_ratings_zero_margin_is_hfa():
    rs = build_ratings_rate(games([]), frame([]), {}, LEGACY_PARAMS, 100.0)
    assert all(v == 0 for v in rs.off_pred.values()) and all(v == 0 for v in rs.def_pred.values())
    assert predict('BUF', 'NE', False, rs, LEGACY_PARAMS).margin == approx(LEGACY_PARAMS.hfa)


def test_shrink_weight_rises_with_dropbacks():
    d2, p2 = _season(2)
    d8, p8 = _season(8)
    a = build_ratings_rate(d2, p2, {}, LEGACY_PARAMS, 100.0)
    b = build_ratings_rate(d8, p8, {}, LEGACY_PARAMS, 100.0)
    assert 0 < a.off_pred['BUF'] < b.off_pred['BUF']
    # weight n/(n+s) with n = 6 vs 24 dropbacks
    ratio = (24 / 124) / (6 / 106)
    assert b.off_pred['BUF'] / a.off_pred['BUF'] == approx(ratio)
