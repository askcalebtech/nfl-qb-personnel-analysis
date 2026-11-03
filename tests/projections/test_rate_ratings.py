from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from pytest import approx

from projections.constants import DB_PER_GAME, LEGACY_PARAMS, TEAMS
from projections.game_model import predict
from projections.ratings import (Raw, _opponent_adjust, _opponent_solve, _rate_values, build_ratings_legacy,
                                 build_ratings_rate, dropbacks, raw_values)
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


# --- direct solve of the opponent adjustment --------------------------------------------------------------------

def _random_schedule(weeks, seed):
    """Every team plays once a week against a random opponent."""
    rng = np.random.default_rng(seed)
    g = []
    for w in range(1, weeks + 1):
        order = list(rng.permutation(TEAMS))
        for j in range(16):
            g.append((f'w{w}_{j}', w, order[2*j], order[2*j + 1], 3))
    return games(g)


def _random_rates(seed):
    rng = np.random.default_rng(seed)
    return Raw(off={t: float(v) for t, v in zip(TEAMS, rng.normal(0, 1.5, 32))},
               def_={t: float(v) for t, v in zip(TEAMS, rng.normal(0, 1.5, 32))},
               lg=6.0, off_n={t: 300 for t in TEAMS}, def_n={t: 300 for t in TEAMS})


# Two separate 4-team cycles after two weeks. Each side's (dropbacks, yards) differ a lot by game, so dropback-weighted
# rates leave an imbalance the loop cannot settle: game id, home, away, home side, away side.
_SPARSE = [('w1_0', 1, 'BUF', 'NE', (60, 14.0), (10, 2.0)), ('w1_1', 1, 'NYJ', 'MIA', (10, 3.0), (60, 12.0)),
           ('w2_0', 2, 'BUF', 'MIA', (10, 0.0), (60, 3.0)), ('w2_1', 2, 'NYJ', 'NE', (60, 15.0), (10, 1.0)),
           ('w1_2', 1, 'PIT', 'CIN', (55, 13.0), (12, 4.0)), ('w1_3', 1, 'CLE', 'BAL', (12, 2.0), (55, 11.0)),
           ('w2_2', 2, 'PIT', 'BAL', (12, 1.0), (55, 4.0)), ('w2_3', 2, 'CLE', 'CIN', (55, 14.0), (12, 3.0))]


def _sparse_season():
    g, rows = [], []
    for gid_, week, home, away, (nh, yh), (na, ya) in _SPARSE:
        g.append((gid_, week, home, away, 3))
        rows += [play(game_id=gid_, posteam=home, defteam=away, passing_yards=yh, passer_player_name=f'{home}-QB')
                 for _ in range(nh)]
        rows += [play(game_id=gid_, posteam=away, defteam=home, passing_yards=ya, passer_player_name=f'{away}-QB')
                 for _ in range(na)]
    return games(g), frame(rows)


def _max_abs(*ds):
    return max(abs(v) for d in ds for v in d.values())


@pytest.mark.parametrize('weeks,seed', [(9, 1), (12, 2), (17, 3)])
def test_solve_matches_converged_loop_on_connected_schedule(weeks, seed):
    done = _random_schedule(weeks, seed)
    rates = _random_rates(seed)
    loop_o, loop_d = _opponent_adjust(done, rates)
    solve_o, solve_d = _opponent_solve(done, rates)
    assert max(abs(loop_o[t] - solve_o[t]) for t in TEAMS) < 1e-6
    assert max(abs(loop_d[t] - solve_d[t]) for t in TEAMS) < 1e-6


def test_solve_satisfies_fixed_point_with_mean_zero_units():
    done = _random_schedule(9, 4)
    rates = _random_rates(4)
    O, D = _opponent_solve(done, rates)
    assert np.mean(list(O.values())) == approx(0, abs=1e-9) and np.mean(list(D.values())) == approx(0, abs=1e-9)
    opps = {t: [] for t in TEAMS}
    for r in done.itertuples():
        opps[r.home_team].append(r.away_team)
        opps[r.away_team].append(r.home_team)
    nO = {t: rates.off[t] + np.mean([D[x] for x in opps[t]]) for t in TEAMS}
    nD = {t: rates.def_[t] + np.mean([O[x] for x in opps[t]]) for t in TEAMS}
    mo, md = np.mean(list(nO.values())), np.mean(list(nD.values()))
    assert all(O[t] == approx(nO[t] - mo, abs=1e-9) and D[t] == approx(nD[t] - md, abs=1e-9) for t in TEAMS)


def test_sparse_schedule_makes_loop_grow_but_solve_stays_bounded():
    done, pbp = _sparse_season()
    db = dropbacks(pbp)
    raw = raw_values(db)
    rates = _rate_values(db, raw)
    biggest_raw = _max_abs(rates.off, rates.def_)
    assert biggest_raw > 0

    # The loop runs away on this schedule, which is why the rate build must not use it
    assert _max_abs(*_opponent_adjust(done, rates)) > 3 * biggest_raw

    O, D = _opponent_solve(done, rates)
    assert np.isfinite(list(O.values()) + list(D.values())).all()
    assert _max_abs(O, D) <= 2 * biggest_raw

    # The rate build uses the solve. Every team has one QB, so season value / dropbacks is the adjusted rate.
    rs = build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, None)
    for t in TEAMS:
        assert rs.off_season[t] == approx(O[t] * raw.off_n[t])
        assert rs.def_season[t] == approx(D[t] * raw.def_n[t])


def test_solve_two_team_case_splits_the_gap_evenly():
    done, pbp = _season(3)     # BUF gains 30 a dropback and NE 10; offense and defense can't be told apart
    db = dropbacks(pbp)
    O, D = _opponent_solve(done, _rate_values(db, raw_values(db)))
    assert O['BUF'] == approx(5) and D['BUF'] == approx(5)
    assert O['NE'] == approx(-5) and D['NE'] == approx(-5)


def test_solve_teams_without_games_stay_zero():
    done, pbp = _sparse_season()
    db = dropbacks(pbp)
    O, D = _opponent_solve(done, _rate_values(db, raw_values(db)))
    assert O['KC'] == 0.0 and D['KC'] == 0.0
    empty = _opponent_solve(games([]), _random_rates(1))
    assert all(v == 0.0 for d in empty for v in d.values())


def test_solve_is_stable():
    done, pbp = _sparse_season()
    db = dropbacks(pbp)
    rates = _rate_values(db, raw_values(db))
    first = _opponent_solve(done, rates)
    assert _opponent_solve(done, rates) == first      # exact, not approximate
    assert _opponent_solve(done.iloc[::-1], rates) == first
    a = build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, 100.0)
    b = build_ratings_rate(done, pbp, {}, LEGACY_PARAMS, 100.0)
    assert a.off_pred == b.off_pred and a.def_pred == b.def_pred


def test_legacy_build_keeps_the_loop():
    done, pbp = _sparse_season()
    rs = build_ratings_legacy(done, pbp, {}, LEGACY_PARAMS)
    loop_o, loop_d = _opponent_adjust(done, raw_values(dropbacks(pbp)))
    assert rs.off_season == approx(loop_o)
    assert rs.def_season == approx(loop_d)
