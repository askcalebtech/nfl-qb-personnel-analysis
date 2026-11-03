import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from pytest import approx

from projections import backtest
from projections.backtest import evaluate, fit_params, leave_one_season_out, score, walk_forward_rows
from projections.constants import PARAMS
from projections.game_model import compute_margin, predict
from projections.ratings import build_ratings
from tests.projections.test_ratings import OLD_PARAMS, frame, play

RATING_COLS = ['off_home', 'def_home', 'off_away', 'def_away', 'off_n_home', 'def_n_home', 'off_n_away',
               'def_n_away', 'rush_edge']
QBS = {'BUF': 'J.Allen', 'NE': 'M.Jones', 'NYJ': 'Z.Wilson', 'MIA': 'T.Tua'}
# Round robin of four teams, played twice, so every team has a game every week
SCHEDULE = [[('BUF', 'NE'), ('NYJ', 'MIA')], [('BUF', 'NYJ'), ('NE', 'MIA')], [('BUF', 'MIA'), ('NE', 'NYJ')]] * 2


def gid(season, week, home):
    return f'{season}_{week:02d}_{home}'


def game_row(season, week, home, away, result, location='Home', spread=3.0):
    return dict(season=season, game_type='REG', game_id=gid(season, week, home), week=week, home_team=home,
                away_team=away, result=result, location=location, spread_line=spread, home_moneyline=-150.0,
                away_moneyline=130.0)


def team_plays(game_id, team, opp, seed, n=6, **kw):
    """n dropbacks and n rushes with varied values, so off, def and rush ratings are all non-zero."""
    rng = np.random.default_rng(seed)
    base = dict(game_id=game_id, posteam=team, defteam=opp, passer_player_name=QBS[team])
    base.update(kw)
    drop = [play(**{**base, 'passing_yards': float(y)}) for y in rng.integers(0, 25, n)]
    runs = [play(**{**base, 'pass_attempt': 0, 'rush': 1, 'epa': float(e), 'passer_player_name': None})
            for e in rng.normal(0, 1, n)]
    return drop + runs


def season_frames(season, seed=0, weeks=6):
    gs, plays = [], []
    for w, slate in enumerate(SCHEDULE[:weeks], start=1):
        for j, (home, away) in enumerate(slate):
            g = gid(season, w, home)
            gs.append(game_row(season, w, home, away, float((seed + w*5 + j*3) % 17 - 8)))
            plays += team_plays(g, home, away, seed*1000 + w*10 + j)
            plays += team_plays(g, away, home, seed*1000 + w*10 + j + 5)
    return gs, plays


def write_season(root, season, gs, plays):
    d = root / str(season)
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(gs).to_csv(d / 'games.csv', index=False)
    frame(plays).to_parquet(d / 'pbp.parquet')
    return root


def synth_rows(n=600, seed=1, season=2022, slope=0.02, hfa=2.0, k=800.0, reg=0.8, noise=1.0,
               spread=150.0, rush_scale=0.0):
    """Rows whose results come from known constants through the production margin function, plus noise."""
    rng = np.random.default_rng(seed)
    p = replace(OLD_PARAMS, k=k, reg=reg, slope=slope, hfa=hfa, sig=11.0)
    df = pd.DataFrame({c: rng.normal(0, spread, n) for c in ['off_home', 'def_home', 'off_away', 'def_away']})
    df['rush_edge'] = rng.normal(0, rush_scale, n) if rush_scale else 0.0
    df['season'] = season
    df['week'] = rng.integers(1, 19, n)
    df['away'] = 'BUF'
    df['home'] = 'NE'
    df['neutral'] = rng.random(n) < 0.1
    df['result'] = evaluate(df.assign(result=0.0), p).margin.values + rng.normal(0, noise, n)
    return df


# --- walk-forward rows -----------------------------------------------------------------------------------------

def test_rows_use_only_earlier_weeks(tmp_path):
    gs, plays = season_frames(2022)
    write_season(tmp_path / 'a', 2022, gs, plays)
    base = walk_forward_rows(2022, str(tmp_path / 'a'))

    # Change what happened in Week 5: the final scores, and the plays of that week's home teams (BUF, NE)
    wk5 = {gid(2022, 5, h) for h, _ in SCHEDULE[4]}
    gs2 = [dict(g, result=g['result'] + 21.0) if g['week'] == 5 else g for g in gs]
    plays2 = [dict(p, passing_yards=p['passing_yards'] + 40.0, epa=p['epa'] + 2.0)
              if p['game_id'] in wk5 and p['posteam'] in ('BUF', 'NE') else p for p in plays]
    write_season(tmp_path / 'b', 2022, gs2, plays2)
    changed = walk_forward_rows(2022, str(tmp_path / 'b'))

    earlier = base.week <= 5
    pd.testing.assert_frame_equal(base.loc[earlier, RATING_COLS], changed.loc[earlier, RATING_COLS])
    assert (base.loc[~earlier, 'off_home'] != changed.loc[~earlier, 'off_home']).all()
    assert (base.loc[~earlier, 'rush_edge'] != changed.loc[~earlier, 'rush_edge']).all()


def test_rows_week_one_has_no_information(tmp_path):
    gs, plays = season_frames(2022)
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path))
    wk1 = rows[rows.week == 1]
    assert (wk1[RATING_COLS] == 0).all().all()
    assert (rows[rows.week == 2].off_n_home == 6).all()   # exactly the Week 1 dropbacks


def test_starter_comes_from_previous_game_not_hindsight(tmp_path):
    # BUF: A throws most in Week 1, B in Week 2, C in every later week (C is the full-season leader)
    leader = {1: 'A', 2: 'B'}
    gs, plays = season_frames(2022)
    plays = [dict(p, passer_player_name=leader.get(int(p['game_id'][5:7]), 'C'))
             if p['posteam'] == 'BUF' and p['pass_attempt'] == 1 else p for p in plays]
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path))
    starter = {r.week: r.starter_home for r in rows[rows.home == 'BUF'].itertuples()}
    assert starter[1] is None
    assert starter[2] == 'A'
    assert starter[3] == 'B'
    assert starter[4] == 'C'


def test_game_with_no_result_is_skipped(tmp_path):
    gs, plays = season_frames(2022)
    gs = [dict(g, result=float('nan')) if g['week'] == 3 and g['home_team'] == 'BUF' else g for g in gs]
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path))
    assert len(rows) == len(gs) - 1
    assert not ((rows.week == 3) & (rows.home == 'BUF')).any()
    assert rows.result.notna().all()
    # Its plays do not feed later ratings: BUF has 6 dropbacks per earlier game, Week 3 not counted
    assert rows[(rows.week == 4) & (rows.home == 'BUF')].off_n_home.iloc[0] == 12


def test_neutral_site_flag_from_location(tmp_path):
    gs, plays = season_frames(2022)
    gs = [dict(g, location='Neutral') if g['week'] == 2 and g['home_team'] == 'BUF' else g for g in gs]
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path))
    assert rows.neutral.sum() == 1
    assert rows[(rows.week == 2) & (rows.home == 'BUF')].neutral.iloc[0]


def test_betting_lines_do_not_reach_the_rows(tmp_path):
    gs, plays = season_frames(2022)
    write_season(tmp_path / 'a', 2022, gs, plays)
    write_season(tmp_path / 'b', 2022, [dict(g, spread_line=-30.0, home_moneyline=900.0) for g in gs], plays)
    a = walk_forward_rows(2022, str(tmp_path / 'a'))
    b = walk_forward_rows(2022, str(tmp_path / 'b'))
    pd.testing.assert_frame_equal(a, b)
    assert not {c for c in a.columns if 'spread' in c or 'moneyline' in c}


# --- evaluate must equal predict -------------------------------------------------------------------------------

@pytest.mark.parametrize('reg', [0.8, 0.6])
def test_evaluate_equals_predict_on_rating_set(tmp_path, reg):
    gs, plays = season_frames(2022)
    gs = [dict(g, location='Neutral') if g['week'] == 4 and g['home_team'] == 'BUF' else g for g in gs]
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path))
    # Small ratings scale and a wide window, so the rush nudge fires and is not capped everywhere
    params = replace(OLD_PARAMS, reg=reg, k=150.0, slope=0.031, hfa=1.3, sig=12.5, rush_window=6.0, rush_pts=0.2)
    preds = evaluate(rows, params)

    done = pd.DataFrame(gs)
    pbp = frame(plays)
    nudged = 0
    for r, pr in zip(rows.itertuples(), preds.itertuples()):
        prior = done[done.week < r.week]
        prior_pbp = pbp[pbp.game_id.isin(prior.game_id)]
        rs = build_ratings(prior, prior_pbp, {}, params)
        want = predict(r.away, r.home, r.neutral, rs, params)
        assert pr.margin == approx(want.margin, abs=1e-9)
        assert pr.p_home == approx(want.p_home, abs=1e-9)
        assert pr.nudge == approx(want.nudge, abs=1e-9)
        assert pr.home_matchup == approx(want.home_matchup, abs=1e-9)
        assert pr.away_matchup == approx(want.away_matchup, abs=1e-9)
        nudged += want.nudge != 0
    assert nudged > 0


def test_predict_and_compute_margin_agree():
    params = replace(OLD_PARAMS, k=100.0)
    from tests.projections.test_game_model import make_rs
    rs = make_rs(off={'H': 30.0, 'A': -5.0}, def_={'H': 4.0, 'A': 8.0}, ro={'H': 0.02}, rd={'A': -0.01})
    edge = (0.02 - -0.01) - (0.0 - 0.0)
    assert predict('A', 'H', False, rs, params) == compute_margin(30.0, 4.0, -5.0, 8.0, edge, False, params)


# --- score -----------------------------------------------------------------------------------------------------

def _preds(rows):
    return pd.DataFrame(rows, columns=['margin', 'p_home', 'result'])


FOUR = [(3.0, 0.6, 7.0), (-2.0, 0.4, -3.0), (1.0, 0.55, -4.0), (-5.0, 0.3, 5.0)]


def test_score_known_values():
    # errors 4, 1, 5, 10 -> sqrt(142/4); -[ln .6 + ln .6 + ln .45 + ln .3]/4; 2 of 4 winners
    s = score(_preds(FOUR))
    assert s['n'] == 4
    assert s['rmse'] == approx(5.958188, abs=1e-5)
    assert s['log_loss'] == approx(0.756033, abs=1e-5)
    assert s['winners_pct'] == approx(50.0)


def test_tie_excluded_from_winners_and_log_loss_but_in_rmse():
    s = score(_preds(FOUR + [(2.0, 0.6, 0.0)]))
    assert s['n'] == 5
    assert s['ties'] == 1
    assert s['rmse'] == approx(math.sqrt((142 + 4) / 5), abs=1e-9)
    assert s['log_loss'] == approx(0.756033, abs=1e-5)
    assert s['winners_pct'] == approx(50.0)


def test_score_calibration_five_bins():
    s = score(_preds([(0, 0.1, -3.0), (0, 0.5, 3.0), (0, 0.55, -3.0), (0, 0.9, 3.0), (0, 1.0, 3.0), (0, 0.5, 0.0)]))
    cal = s['calibration']
    assert [b['bin'] for b in cal] == ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']
    assert [b['n'] for b in cal] == [1, 0, 2, 0, 2]    # the tie is not counted; p=1.0 lands in the top bin
    assert cal[2]['mean_p'] == approx(0.525)
    assert cal[2]['actual'] == approx(0.5)
    assert cal[4]['actual'] == approx(1.0)
    assert math.isnan(cal[1]['mean_p'])


def test_score_coin_flip_gets_half_credit_for_a_winner():
    assert score(_preds([(0.0, 0.5, 3.0), (2.0, 0.6, 3.0)]))['winners_pct'] == approx(75.0)


def test_score_certain_wrong_probability_is_finite():
    assert math.isfinite(score(_preds([(40.0, 1.0, -3.0)]))['log_loss'])


def test_score_empty_split():
    s = score(_preds([]))
    assert s['n'] == 0 and math.isnan(s['rmse']) and math.isnan(s['log_loss']) and math.isnan(s['winners_pct'])


# --- fit -------------------------------------------------------------------------------------------------------

def test_fit_recovers_known_slope_and_hfa():
    params = fit_params(synth_rows(slope=0.02, hfa=2.0, noise=1.0))
    assert params.k == 800.0 and params.reg == 0.8
    assert params.slope == approx(0.02, rel=0.05)
    assert params.hfa == approx(2.0, rel=0.05)
    assert params.sig == approx(1.0, rel=0.1)
    assert (params.qb_k, params.qb_prior) == (PARAMS.qb_k, PARAMS.qb_prior)
    assert (params.rush_window, params.rush_pts, params.rush_cap, params.rushes) == (
        PARAMS.rush_window, PARAMS.rush_pts, PARAMS.rush_cap, PARAMS.rushes)


def test_fit_has_no_free_intercept():
    # Neutral games carry a shift a free intercept would absorb; with no intercept, HFA stays near its true value
    rows = synth_rows(n=800, slope=0.02, hfa=2.0, noise=0.5)
    fit = fit_params(rows)
    pre = evaluate(rows, replace(fit, slope=1.0))
    X = np.column_stack([pre.home_matchup - pre.away_matchup, 1.0 - rows.neutral.astype(float)])
    want = np.linalg.lstsq(X, rows.result.values, rcond=None)[0]
    assert fit.slope == approx(want[0]) and fit.hfa == approx(want[1])


def test_fit_regresses_pre_nudge_margin_and_sig_includes_nudge():
    rows = synth_rows(n=800, slope=0.01, hfa=1.0, noise=2.0, spread=60.0, rush_scale=0.5)
    fit = fit_params(rows)
    pre = evaluate(rows, replace(fit, rush_pts=0.0))
    assert pre.nudge.abs().max() == 0
    X = np.column_stack([pre.home_matchup - pre.away_matchup, 1.0 - rows.neutral.astype(float)])
    want = np.linalg.lstsq(X, rows.result.values, rcond=None)[0]
    assert fit.slope == approx(want[0]) and fit.hfa == approx(want[1])

    final = evaluate(rows, fit)
    assert final.nudge.abs().max() > 0
    res = rows.result.values - final.margin.values
    assert fit.sig == approx(math.sqrt((res**2).sum() / (len(rows) - 2)))
    pre_res = rows.result.values - (pre.matchup_points + pre.hfa).values
    assert fit.sig != approx(math.sqrt((pre_res**2).sum() / (len(rows) - 2)), abs=1e-6)


# --- folds -----------------------------------------------------------------------------------------------------

def _four_seasons():
    return pd.concat([synth_rows(n=120, seed=s, season=s, noise=5.0) for s in (2022, 2023, 2024, 2025)],
                     ignore_index=True)


def test_holdout_season_absent_from_its_training_fold(monkeypatch):
    rows = _four_seasons()
    trained_on = []
    real = backtest.fit_params

    def spy(train):
        trained_on.append(set(train.season))
        return real(train)

    monkeypatch.setattr(backtest, 'fit_params', spy)
    preds, fits = leave_one_season_out(rows)
    assert trained_on == [{2023, 2024, 2025}, {2022, 2024, 2025}, {2022, 2023, 2025}, {2022, 2023, 2024}]
    assert sorted(fits) == [2022, 2023, 2024, 2025]
    assert len(preds) == len(rows)
    assert preds.groupby('season').size().to_dict() == {s: 120 for s in (2022, 2023, 2024, 2025)}


def test_holdout_predictions_ignore_their_own_results():
    rows = _four_seasons()
    base, fits = leave_one_season_out(rows)
    # Scramble 2023 results. 2023 predictions and its fold's constants must not move; other folds must.
    rng = np.random.default_rng(9)
    changed = rows.copy()
    mask = changed.season == 2023
    changed.loc[mask, 'result'] = rng.normal(0, 30, mask.sum())
    after, fits2 = leave_one_season_out(changed)
    assert fits2[2023] == fits[2023]
    assert (after[after.season == 2023].margin.values == base[base.season == 2023].margin.values).all()
    assert fits2[2022] != fits[2022]
    assert (after[after.season == 2022].margin.values != base[base.season == 2022].margin.values).any()


# --- main ------------------------------------------------------------------------------------------------------

def _write_main_data(root):
    for s in (2022, 2023):
        gs, plays = season_frames(s, seed=s)
        write_season(root, s, gs, plays)


def test_main_refit_prints_constants_to_paste(tmp_path, capsys):
    _write_main_data(tmp_path)
    backtest.main(['--refit', '--seasons', '2022', '2023', '--data-dir', str(tmp_path)])
    out = capsys.readouterr().out
    rows = pd.concat([walk_forward_rows(s, str(tmp_path)) for s in (2022, 2023)], ignore_index=True)
    p = fit_params(rows)
    assert f'slope={p.slope:.5f}, hfa={p.hfa:.2f}, sig={p.sig:.2f}' in out
    assert 'MODEL_VERSION' in out


def test_main_without_refit_prints_scores(tmp_path, capsys):
    _write_main_data(tmp_path)
    backtest.main(['--seasons', '2022', '2023', '--data-dir', str(tmp_path)])
    out = capsys.readouterr().out
    assert 'Leave-one-season-out' in out and 'RMSE' in out and 'Early' in out
