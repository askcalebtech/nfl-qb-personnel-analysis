from dataclasses import replace

import pandas as pd
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


FOUR = ['BUF', 'NE', 'NYJ', 'MIA']
ROUND_ROBIN = [[('BUF', 'NE'), ('NYJ', 'MIA')], [('BUF', 'NYJ'), ('NE', 'MIA')], [('BUF', 'MIA'), ('NE', 'NYJ')]]


def _round_robin(off_yards=None, def_yards=None, base=10.0, counts=None, counts_against=None):
    """Four teams, one game each. A team's yards per dropback are off_yards if set, else def_yards of the defense
    if set, else base. Three dropbacks a side unless counts (by offense) or counts_against (by defense) say so.
    A schedule that isn't a single pairing, so the opponent adjustment converges."""
    off_yards, def_yards, counts, counts_against = (x or {} for x in (off_yards, def_yards, counts, counts_against))
    rows, g = [], []
    for w, slate in enumerate(ROUND_ROBIN, start=1):
        for j, (home, away) in enumerate(slate):
            gid_ = f'w{w}_{j}'
            g.append((gid_, w, home, away, 3))
            for off, de in ((home, away), (away, home)):
                yards = off_yards.get(off, def_yards.get(de, base))
                n = counts.get(off, counts_against.get(de, 3))
                rows += [play(game_id=gid_, posteam=off, defteam=de, passing_yards=yards,
                              passer_player_name=f'{off}-QB') for _ in range(n)]
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
    # BUF gains 30 a dropback and everyone else 10, whichever defense they face. League mean is 15.
    done, pbp = _round_robin(off_yards={'BUF': 30.0}, base=10.0)
    rs = build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, None)
    assert rs.off_season['BUF'] == approx((30 - 15) * 9)    # 3 games x 3 dropbacks
    assert rs.off_season['NE'] == approx((10 - 15) * 9)
    assert rs.off_pred['BUF'] == approx((30 - 15) * DB_PER_GAME * LEGACY_PARAMS.reg)
    # No defense differs once the schedule is accounted for
    assert all(rs.def_season[t] == approx(0, abs=1e-6) for t in FOUR)


def test_defense_sign():
    # Every offense gains 5 against BUF, 15 against NE and 10 against the rest
    done, pbp = _round_robin(def_yards={'BUF': 5.0, 'NE': 15.0}, base=10.0)
    rs = build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, None)
    assert rs.def_pred['BUF'] > 0 and rs.def_season['BUF'] > 0
    assert rs.def_pred['NE'] < 0 and rs.def_season['NE'] < 0
    assert rs.def_pred['BUF'] == approx(5 * DB_PER_GAME * LEGACY_PARAMS.reg)
    assert rs.def_pred['NE'] == approx(-5 * DB_PER_GAME * LEGACY_PARAMS.reg)
    assert rs.def_season['BUF'] == approx(5 * 9)
    assert rs.def_pred['NYJ'] == approx(0, abs=1e-6)


def test_each_unit_weight_uses_its_own_dropbacks():
    # BUF throws 6 a game and faces 2 a game, so its offense has 18 dropbacks and its defense 6
    done, pbp = _round_robin(off_yards={'BUF': 30.0}, def_yards={'BUF': 4.0}, base=10.0, counts={'BUF': 6},
                             counts_against={'BUF': 2})
    raw = raw_values(dropbacks(pbp))
    assert (raw.off_n['BUF'], raw.def_n['BUF']) == (18, 6)
    s = 100.0
    unit = replace(LEGACY_PARAMS, reg=1.0)
    full = build_ratings_rate(done, pbp, {}, unit, None)
    shrunk = build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, s)
    assert full.off_pred['BUF'] != approx(0, abs=1e-6) and full.def_pred['BUF'] != approx(0, abs=1e-6)
    assert shrunk.off_pred['BUF'] == approx(full.off_pred['BUF'] * 18 / (18 + s))
    assert shrunk.def_pred['BUF'] == approx(full.def_pred['BUF'] * 6 / (6 + s))
    # Season values also scale by each unit's own count
    assert full.off_season['BUF'] == approx(full.off_pred['BUF'] / DB_PER_GAME * 18)
    assert full.def_season['BUF'] == approx(full.def_pred['BUF'] / DB_PER_GAME * 6)


@pytest.mark.parametrize('shrink_s', [None, 100.0])
def test_qb_switch_adjustment(shrink_s):
    # BUF: A throws 6 at 30 yards in Weeks 1-2, B throws 3 at 0 yards in Week 3, so B starts next
    done, pbp = _round_robin(base=10.0)
    pbp = pbp[pbp.posteam != 'BUF']
    extra = []
    for gid_, opp, qb, yds in (('w1_0', 'NE', 'A', 30.0), ('w2_0', 'NYJ', 'A', 30.0), ('w3_0', 'MIA', 'B', 0.0)):
        extra += [play(game_id=gid_, posteam='BUF', defteam=opp, passing_yards=yds, passer_player_name=qb)
                  for _ in range(3)]
    pbp = pd.concat([pbp, frame(extra)], ignore_index=True)
    p = LEGACY_PARAMS
    rs = build_ratings_rate(done, pbp, {}, p, shrink_s)
    assert rs.starter['BUF'] == 'B'

    # Independently: each QB's rate is shrunk toward the league mean plus the prior, then compared with the mix
    lg = dropbacks(pbp).pts.mean()
    rate_a = (6*30.0 + p.qb_k*(lg + p.qb_prior)) / (6 + p.qb_k)
    rate_b = (3*0.0 + p.qb_k*(lg + p.qb_prior)) / (3 + p.qb_k)
    qb_rate = rate_b - (6*rate_a + 3*rate_b) / 9
    off_n = raw_values(dropbacks(pbp)).off_n['BUF']
    assert off_n == 9
    w_off = p.reg if shrink_s is None else off_n / (off_n + shrink_s)
    assert qb_rate < 0
    assert rs.qb_adj_season['BUF'] == approx(qb_rate * off_n)
    assert rs.qb_adj_pred['BUF'] == approx(rs.qb_adj_season['BUF'] / off_n * DB_PER_GAME * w_off)
    assert rs.qb_adj_pred['BUF'] == approx(qb_rate * DB_PER_GAME * w_off)

    # off_pred includes it: starting A instead moves off_pred by exactly the change in qb_adj_pred
    with_a = build_ratings_rate(done, pbp, {'BUF': 'A'}, p, shrink_s)
    assert with_a.qb_adj_pred['BUF'] > 0 > rs.qb_adj_pred['BUF']
    assert rs.off_pred['BUF'] - with_a.off_pred['BUF'] == approx(rs.qb_adj_pred['BUF'] - with_a.qb_adj_pred['BUF'])
    assert rs.off_season['BUF'] - with_a.off_season['BUF'] == approx(
        rs.qb_adj_season['BUF'] - with_a.qb_adj_season['BUF'])
    # A team that did not switch has no adjustment
    assert rs.qb_adj_pred['NE'] == approx(0)


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
