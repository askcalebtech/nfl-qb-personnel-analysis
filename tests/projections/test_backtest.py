import math
import re
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from pytest import approx

from projections import backtest
from projections.backtest import (GRID_K, GRID_REG, GRID_SHRINK, check_db_per_game, evaluate, fit_params,
                                  forward_check, leave_one_season_out, mean_dropbacks_per_team_game, score,
                                  walk_forward_rows)
from projections.constants import DB_PER_GAME, LEGACY_PARAMS
from projections.game_model import compute_margin, predict
from projections.ratings import build_ratings_legacy, build_ratings_rate
from tests.projections.test_ratings import frame, play

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


def synth_rows(n=600, seed=1, season=2022, slope=0.02, hfa=2.0, k=800.0, reg=0.8, shrink=None, noise=1.0,
               spread=150.0, rush_scale=0.0):
    """Rows whose results come from known constants through the production margin function, plus noise."""
    rng = np.random.default_rng(seed)
    p = replace(LEGACY_PARAMS, k=k, reg=reg, slope=slope, hfa=hfa, sig=11.0)
    df = pd.DataFrame({c: rng.normal(0, spread, n) for c in ['off_home', 'def_home', 'off_away', 'def_away']})
    for c in ['off_n_home', 'def_n_home', 'off_n_away', 'def_n_away']:
        df[c] = rng.integers(10, 500, n)
    df['rush_edge'] = rng.normal(0, rush_scale, n) if rush_scale else 0.0
    df['season'] = season
    df['week'] = rng.integers(1, 19, n)
    df['away'] = 'BUF'
    df['home'] = 'NE'
    df['neutral'] = rng.random(n) < 0.1
    df['result'] = evaluate(df.assign(result=0.0), p, shrink).margin.values + rng.normal(0, noise, n)
    return df


# --- walk-forward rows -----------------------------------------------------------------------------------------

@pytest.mark.parametrize('formula', ['legacy', 'rate'])
def test_rows_use_only_earlier_weeks(tmp_path, formula):
    gs, plays = season_frames(2022)
    write_season(tmp_path / 'a', 2022, gs, plays)
    base = walk_forward_rows(2022, str(tmp_path / 'a'), formula)

    # Change what happened in Week 5: the final scores, and the plays of that week's home teams (BUF, NE)
    wk5 = {gid(2022, 5, h) for h, _ in SCHEDULE[4]}
    gs2 = [dict(g, result=g['result'] + 21.0) if g['week'] == 5 else g for g in gs]
    plays2 = [dict(p, passing_yards=p['passing_yards'] + 40.0, epa=p['epa'] + 2.0)
              if p['game_id'] in wk5 and p['posteam'] in ('BUF', 'NE') else p for p in plays]
    write_season(tmp_path / 'b', 2022, gs2, plays2)
    changed = walk_forward_rows(2022, str(tmp_path / 'b'), formula)

    earlier = base.week <= 5
    pd.testing.assert_frame_equal(base.loc[earlier, RATING_COLS], changed.loc[earlier, RATING_COLS])
    assert (base.loc[~earlier, 'off_home'] != changed.loc[~earlier, 'off_home']).all()
    assert (base.loc[~earlier, 'rush_edge'] != changed.loc[~earlier, 'rush_edge']).all()


def test_rows_week_one_has_no_information(tmp_path):
    gs, plays = season_frames(2022)
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path), 'rate')
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
    rows = walk_forward_rows(2022, str(tmp_path), 'rate')
    starter = {r.week: r.starter_home for r in rows[rows.home == 'BUF'].itertuples()}
    assert starter[1] is None
    assert starter[2] == 'A'
    assert starter[3] == 'B'
    assert starter[4] == 'C'


def test_game_with_no_result_is_skipped(tmp_path):
    gs, plays = season_frames(2022)
    gs = [dict(g, result=float('nan')) if g['week'] == 3 and g['home_team'] == 'BUF' else g for g in gs]
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path), 'rate')
    assert len(rows) == len(gs) - 1
    assert not ((rows.week == 3) & (rows.home == 'BUF')).any()
    assert rows.result.notna().all()
    # Its plays do not feed later ratings: BUF has 6 dropbacks per earlier game, Week 3 not counted
    assert rows[(rows.week == 4) & (rows.home == 'BUF')].off_n_home.iloc[0] == 12


def test_neutral_site_flag_from_location(tmp_path):
    gs, plays = season_frames(2022)
    gs = [dict(g, location='Neutral') if g['week'] == 2 and g['home_team'] == 'BUF' else g for g in gs]
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path), 'rate')
    assert rows.neutral.sum() == 1
    assert rows[(rows.week == 2) & (rows.home == 'BUF')].neutral.iloc[0]


def test_betting_lines_do_not_reach_the_rows(tmp_path):
    gs, plays = season_frames(2022)
    write_season(tmp_path / 'a', 2022, gs, plays)
    write_season(tmp_path / 'b', 2022, [dict(g, spread_line=-30.0, home_moneyline=900.0) for g in gs], plays)
    a = walk_forward_rows(2022, str(tmp_path / 'a'), 'rate')
    b = walk_forward_rows(2022, str(tmp_path / 'b'), 'rate')
    pd.testing.assert_frame_equal(a, b)
    assert not {c for c in a.columns if 'spread' in c or 'moneyline' in c}


def test_rows_reject_unknown_formula(tmp_path):
    gs, plays = season_frames(2022)
    write_season(tmp_path, 2022, gs, plays)
    with pytest.raises(ValueError):
        walk_forward_rows(2022, str(tmp_path), 'bogus')


# --- evaluate must equal predict -------------------------------------------------------------------------------

@pytest.mark.parametrize('formula,reg,shrink', [('legacy', 0.8, None), ('legacy', 0.6, None), ('rate', 0.7, None),
                                                ('rate', 1.0, 100.0), ('rate', 0.7, 400.0)])
def test_evaluate_equals_predict_on_rating_set(tmp_path, formula, reg, shrink):
    gs, plays = season_frames(2022)
    gs = [dict(g, location='Neutral') if g['week'] == 4 and g['home_team'] == 'BUF' else g for g in gs]
    write_season(tmp_path, 2022, gs, plays)
    rows = walk_forward_rows(2022, str(tmp_path), formula)
    # Small ratings scale and a wide window, so the rush nudge fires and is not capped everywhere
    params = replace(LEGACY_PARAMS, reg=reg, k=150.0, slope=0.031, hfa=1.3, sig=12.5, rush_window=6.0, rush_pts=0.2)
    preds = evaluate(rows, params, shrink)

    done = pd.DataFrame(gs)
    pbp = frame(plays)
    nudged = 0
    for r, pr in zip(rows.itertuples(), preds.itertuples()):
        prior = done[done.week < r.week]
        prior_pbp = pbp[pbp.game_id.isin(prior.game_id)]
        rs = (build_ratings_legacy(prior, prior_pbp, {}, params) if formula == 'legacy'
              else build_ratings_rate(prior, prior_pbp, {}, params, shrink))
        want = predict(r.away, r.home, r.neutral, rs, params)
        assert pr.margin == approx(want.margin, abs=1e-9)
        assert pr.p_home == approx(want.p_home, abs=1e-9)
        assert pr.nudge == approx(want.nudge, abs=1e-9)
        assert pr.home_matchup == approx(want.home_matchup, abs=1e-9)
        assert pr.away_matchup == approx(want.away_matchup, abs=1e-9)
        nudged += want.nudge != 0
    assert nudged > 0


def test_predict_and_compute_margin_agree():
    params = replace(LEGACY_PARAMS, k=100.0)
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
    params, shrink = fit_params(synth_rows(slope=0.02, hfa=2.0, noise=1.0), 'legacy')
    assert shrink is None
    assert params.k == 800.0 and params.reg == 0.8
    assert params.slope == approx(0.02, rel=0.05)
    assert params.hfa == approx(2.0, rel=0.05)
    assert params.sig == approx(1.0, rel=0.1)
    assert (params.qb_k, params.qb_prior) == (LEGACY_PARAMS.qb_k, LEGACY_PARAMS.qb_prior)
    assert (params.rush_window, params.rush_pts, params.rush_cap, params.rushes) == (
        LEGACY_PARAMS.rush_window, LEGACY_PARAMS.rush_pts, LEGACY_PARAMS.rush_cap, LEGACY_PARAMS.rushes)


def test_fit_has_no_free_intercept():
    # Neutral games carry a shift a free intercept would absorb; with no intercept, HFA stays near its true value
    rows = synth_rows(n=800, slope=0.02, hfa=2.0, noise=0.5)
    fit, _ = fit_params(rows, 'legacy')
    pre = evaluate(rows, replace(fit, slope=1.0), None)
    X = np.column_stack([pre.home_matchup - pre.away_matchup, 1.0 - rows.neutral.astype(float)])
    want = np.linalg.lstsq(X, rows.result.values, rcond=None)[0]
    assert fit.slope == approx(want[0]) and fit.hfa == approx(want[1])


def test_fit_regresses_pre_nudge_margin_and_sig_includes_nudge():
    rows = synth_rows(n=800, slope=0.01, hfa=1.0, noise=2.0, spread=60.0, rush_scale=0.5)
    fit, _ = fit_params(rows, 'legacy')
    pre = evaluate(rows, replace(fit, rush_pts=0.0), None)
    assert pre.nudge.abs().max() == 0
    X = np.column_stack([pre.home_matchup - pre.away_matchup, 1.0 - rows.neutral.astype(float)])
    want = np.linalg.lstsq(X, rows.result.values, rcond=None)[0]
    assert fit.slope == approx(want[0]) and fit.hfa == approx(want[1])

    final = evaluate(rows, fit, None)
    assert final.nudge.abs().max() > 0
    res = rows.result.values - final.margin.values
    assert fit.sig == approx(math.sqrt((res**2).sum() / (len(rows) - 2)))
    pre_res = rows.result.values - (pre.matchup_points + pre.hfa).values
    assert fit.sig != approx(math.sqrt((pre_res**2).sum() / (len(rows) - 2)), abs=1e-6)


def test_rate_fit_grid_prefers_flat_when_true_weights_are_flat():
    rows = synth_rows(n=500, slope=0.05, hfa=1.5, k=100.0, reg=1.0, noise=0.3)
    params, shrink = fit_params(rows, 'rate')
    assert shrink is None
    # Only K/REG is identified once SLOPE is refit
    assert params.k / params.reg == approx(100.0, rel=0.15)
    assert params.hfa == approx(1.5, rel=0.05)


def test_rate_fit_chooses_lowest_training_log_loss():
    rows = synth_rows(n=150, slope=0.05, hfa=1.5, k=100.0, reg=0.8, noise=8.0)
    chosen, chosen_s = fit_params(rows, 'rate')

    def loss(params, shrink_s):
        return score(evaluate(rows, params, shrink_s))['log_loss']

    combos = [(k, r, None) for k in GRID_K for r in GRID_REG] + [(k, 1.0, s) for k in GRID_K for s in GRID_SHRINK]
    all_losses = [loss(backtest._fit_one(rows, k, r, s), s) for k, r, s in combos]
    assert loss(chosen, chosen_s) == approx(min(all_losses), abs=1e-10)


def test_rate_fit_grid_chooses_true_shrinkage():
    rows = synth_rows(n=500, slope=0.05, hfa=1.5, k=200.0, shrink=100.0, noise=0.3)
    params, shrink = fit_params(rows, 'rate')
    assert shrink == 100.0
    assert params.k == 200.0


def test_rate_grid_values_are_verbatim():
    assert GRID_K == (50, 75, 100, 150, 200, 400)
    assert GRID_REG == (0.6, 0.7, 0.8, 0.9, 1.0)
    assert GRID_SHRINK == (50, 100, 200, 400)


def test_rate_fit_scores_every_grid_combo(monkeypatch):
    seen = []
    real = backtest._fit_one

    def spy(rows, k, reg, shrink_s):
        seen.append((k, reg, shrink_s))
        return real(rows, k, reg, shrink_s)

    monkeypatch.setattr(backtest, '_fit_one', spy)
    fit_params(synth_rows(n=60), 'rate')
    assert len(set(seen)) == 6 * (5 + 4)


def test_fit_rejects_unknown_formula():
    with pytest.raises(ValueError):
        fit_params(synth_rows(n=20), 'bogus')


# --- folds -----------------------------------------------------------------------------------------------------

def _four_seasons():
    return pd.concat([synth_rows(n=120, seed=s, season=s, noise=5.0) for s in (2022, 2023, 2024, 2025)],
                     ignore_index=True)


def test_holdout_season_absent_from_its_training_fold(monkeypatch):
    rows = _four_seasons()
    trained_on = []
    real = backtest.fit_params

    def spy(train, formula):
        trained_on.append(set(train.season))
        return real(train, formula)

    monkeypatch.setattr(backtest, 'fit_params', spy)
    preds, fits = leave_one_season_out(rows, 'legacy')
    assert trained_on == [{2023, 2024, 2025}, {2022, 2024, 2025}, {2022, 2023, 2025}, {2022, 2023, 2024}]
    assert sorted(fits) == [2022, 2023, 2024, 2025]
    assert len(preds) == len(rows)
    assert preds.groupby('season').size().to_dict() == {s: 120 for s in (2022, 2023, 2024, 2025)}


def test_holdout_predictions_ignore_their_own_results():
    rows = _four_seasons()
    base, fits = leave_one_season_out(rows, 'rate')
    # Scramble 2023 results. 2023 predictions and its fold's constants must not move; other folds must.
    rng = np.random.default_rng(9)
    changed = rows.copy()
    mask = changed.season == 2023
    changed.loc[mask, 'result'] = rng.normal(0, 30, mask.sum())
    after, fits2 = leave_one_season_out(changed, 'rate')
    assert fits2[2023] == fits[2023]
    assert (after[after.season == 2023].margin.values == base[base.season == 2023].margin.values).all()
    assert fits2[2022] != fits[2022]
    assert (after[after.season == 2022].margin.values != base[base.season == 2022].margin.values).any()


def test_forward_check_trains_on_past_seasons_only(monkeypatch):
    train = _four_seasons()
    fwd = synth_rows(n=50, seed=7, season=2026)
    trained_on = []
    real = backtest.fit_params

    def spy(tr, formula):
        trained_on.append(set(tr.season))
        return real(tr, formula)

    monkeypatch.setattr(backtest, 'fit_params', spy)
    preds, (params, shrink) = forward_check(train, fwd, 'legacy')
    assert trained_on == [{2022, 2023, 2024, 2025}]
    assert set(preds.season) == {2026} and len(preds) == 50
    assert params == real(train, 'legacy')[0]
    with pytest.raises(ValueError):
        forward_check(pd.concat([train, fwd]), fwd, 'legacy')


# --- DB_PER_GAME and the report --------------------------------------------------------------------------------

def test_mean_dropbacks_per_team_game(tmp_path):
    for s in (2022, 2023):
        gs, plays = season_frames(s, weeks=2)
        write_season(tmp_path, s, gs, plays)
    # 4 games a season, 2 teams a game, 6 dropbacks a team-game. Rushes and 2-point tries do not count.
    assert mean_dropbacks_per_team_game([2022, 2023], str(tmp_path)) == approx(6.0)


def test_check_db_per_game_fails_on_mismatch():
    check_db_per_game(36.4, 36)
    check_db_per_game(35.6, 36)
    with pytest.raises(SystemExit):
        check_db_per_game(36.6, 36)


def test_constant_is_a_whole_number():
    assert DB_PER_GAME == int(DB_PER_GAME)


def _write_report_data(root):
    for s in (2022, 2023):
        gs, plays = season_frames(s, seed=s)
        # Reaches the late-season split, so each split has games
        write_season(root, s, [dict(g, week=g['week'] + (8 if g['week'] > 3 else 0)) for g in gs],
                     plays)
    gs, plays = season_frames(2026, seed=5, weeks=3)
    write_season(root, 2026, gs, plays)


def _run_main(tmp_path, monkeypatch, db):
    _write_report_data(tmp_path / 'data')
    monkeypatch.setattr(backtest, 'DB_PER_GAME', db)
    out = tmp_path / 'sub' / 'report.md'
    backtest.main(['--seasons', '2022', '2023', '--forward', '2026', '--out', str(out),
                   '--data-dir', str(tmp_path / 'data')])
    return out


def test_main_writes_report(tmp_path, monkeypatch):
    out = _run_main(tmp_path, monkeypatch, 6)
    text = out.read_text()
    for needle in ['Version A', 'Version B', 'Version C', 'in-sample', 'Weeks 6-8', 'Early', 'Mid', 'Late',
                   'leave-one-season-out', 'no late-season games', 'DB_PER_GAME', 'Calibration', 'Forward check',
                   'Early season by week']:
        assert needle in text, needle
    assert not re.search(r'\bnan\b', text.lower())


def test_main_fails_before_writing_when_constant_differs(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        _run_main(tmp_path, monkeypatch, 40)
    assert not (tmp_path / 'sub' / 'report.md').exists()


def test_main_rejects_forward_season_in_training(tmp_path):
    with pytest.raises(SystemExit):
        backtest.main(['--seasons', '2022', '2026', '--forward', '2026', '--out', str(tmp_path / 'r.md'),
                       '--data-dir', str(tmp_path)])
