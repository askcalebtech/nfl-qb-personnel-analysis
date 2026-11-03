"""Walk-forward backtest comparing today's season-total formula with the per-dropback formula.

Usage:
    python3 -m projections.backtest --seasons 2022 2023 2024 2025 --forward 2026 \\
        --out docs/projections/backtest-2026-11.md [--data-dir DIR]

Each season's nflverse files live in DATA_DIR/<season>/. That directory must stay outside the repo.
Betting lines are in games.csv but are never read into rows, fits or features.
"""
import argparse
import math
import os
from dataclasses import replace
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .constants import DB_PER_GAME, LEGACY_PARAMS, Params
from .data import download, load
from .game_model import compute_margin, home_rush_edge
from .ratings import build_ratings_legacy, build_ratings_rate, dropbacks, raw_values, unit_weight

FORMULAS = ('legacy', 'rate')
LEGACY_FIT_K = 800.0
LEGACY_FIT_REG = 0.8
GRID_K = (50, 75, 100, 150, 200, 400)
GRID_REG = (0.6, 0.7, 0.8, 0.9, 1.0)
GRID_SHRINK = (50, 100, 200, 400)
SPLITS = (('Early (Weeks 1-6)', 1, 6), ('Mid (Weeks 7-12)', 7, 12), ('Late (Weeks 13-18)', 13, 18))
DEFAULT_DATA_DIR = os.path.join(os.path.expanduser('~'), '.cache', 'nfl-qb-projections', 'backtest')
_ID_COLS = ['season', 'week', 'away', 'home', 'neutral', 'result']
_EVAL_COLS = ['off_home', 'off_n_home', 'def_home', 'def_n_home', 'off_away', 'off_n_away', 'def_away', 'def_n_away',
              'rush_edge', 'neutral']
_EPS = 1e-15


def _check_formula(formula):
    if formula not in FORMULAS:
        raise ValueError(f'unknown formula {formula!r}; expected one of {FORMULAS}')


def _season_dir(data_dir, season):
    return os.path.join(data_dir, str(season))


def _unshrunk_ratings(done, pbp, formula):
    """Ratings at reg=1 and no shrinkage, so a row's weight can be applied later for any REG or shrink_s."""
    params = replace(LEGACY_PARAMS, reg=1.0)
    if formula == 'legacy':
        return build_ratings_legacy(done, pbp, {}, params)
    return build_ratings_rate(done, pbp, {}, params, None)


def walk_forward_rows(season, data_dir, formula) -> pd.DataFrame:
    """One row per completed game, with ratings built only from games in strictly earlier weeks.

    off_*/def_* are on the prediction scale with weight 1; evaluate() applies the weight. Games with no result
    never reach `done` (see data.load), so they are neither rows nor inputs to later ratings."""
    _check_formula(formula)
    done, _, pbp = load(season, _season_dir(data_dir, season))
    if done.empty:
        raise ValueError(f'{season}: no completed games in {data_dir}')
    rows = []
    for week in sorted(done.week.unique()):
        prior = done[done.week < week]
        prior_pbp = pbp[pbp.game_id.isin(prior.game_id)]
        rs = _unshrunk_ratings(prior, prior_pbp, formula)
        raw = raw_values(dropbacks(prior_pbp))
        for g in done[done.week == week].itertuples():
            a, h = g.away_team, g.home_team
            rows.append(dict(season=season, week=int(week), game_id=g.game_id, away=a, home=h,
                             neutral=g.location == 'Neutral', result=float(g.result),
                             off_home=rs.off_pred[h], def_home=rs.def_pred[h],
                             off_away=rs.off_pred[a], def_away=rs.def_pred[a],
                             off_n_home=raw.off_n[h], def_n_home=raw.def_n[h],
                             off_n_away=raw.off_n[a], def_n_away=raw.def_n[a],
                             rush_edge=home_rush_edge(a, h, rs), starter_home=rs.starter[h], starter_away=rs.starter[a]))
    return pd.DataFrame(rows)


def evaluate(rows, params, shrink_s: Optional[float]) -> pd.DataFrame:
    """Predictions for rows at the given constants. Equal to game_model.predict on the matching RatingSet."""
    out = {k: [] for k in ('margin', 'p_home', 'nudge', 'home_matchup', 'away_matchup', 'matchup_points', 'hfa')}
    reg = params.reg
    for oh, noh, dh, ndh, oa, noa, da, nda, edge, neutral in zip(*(rows[c].tolist() for c in _EVAL_COLS)):
        p = compute_margin(oh*unit_weight(noh, reg, shrink_s), dh*unit_weight(ndh, reg, shrink_s),
                           oa*unit_weight(noa, reg, shrink_s), da*unit_weight(nda, reg, shrink_s),
                           edge, neutral, params)
        for k, v in out.items():
            v.append(getattr(p, k))
    return rows[_ID_COLS].assign(**out)


def _log_loss(result, p_home) -> float:
    decided = result != 0
    if not decided.any():
        return float('nan')
    p = np.clip(p_home[decided], _EPS, 1 - _EPS)
    won = result[decided] > 0
    return float(-np.mean(np.where(won, np.log(p), np.log(1 - p))))


def _calibration(result, p_home) -> list:
    decided = result != 0
    p, won = p_home[decided], result[decided] > 0
    idx = np.minimum((p*5).astype(int), 4)
    out = []
    for i in range(5):
        hit = idx == i
        n = int(hit.sum())
        out.append(dict(bin=f'{i/5:.1f}-{(i + 1)/5:.1f}', n=n,
                        mean_p=float(p[hit].mean()) if n else float('nan'),
                        actual=float(won[hit].mean()) if n else float('nan')))
    return out


def score(preds) -> dict:
    """Ties count toward RMSE only. A margin of exactly zero is no pick, so it earns half a winner."""
    result = preds.result.values.astype(float)
    margin = preds.margin.values.astype(float)
    p_home = preds.p_home.values.astype(float)
    n = len(preds)
    decided = result != 0
    if decided.any():
        credit = np.where(margin[decided] == 0, 0.5, (margin[decided] > 0) == (result[decided] > 0))
        winners = float(100*credit.mean())
    else:
        winners = float('nan')
    return dict(n=n, ties=int(n - decided.sum()),
                rmse=float(np.sqrt(np.mean((result - margin)**2))) if n else float('nan'),
                log_loss=_log_loss(result, p_home), winners_pct=winners,
                calibration=_calibration(result, p_home))


def _fit_one(rows, k, reg, shrink_s) -> Params:
    """margin ~ SLOPE*matchup difference + HFA*(not neutral), with no free intercept. The fit uses the pre-nudge
    margin; SIG is the residual SD of the final margin, nudge included, with 2 degrees of freedom removed."""
    base = replace(LEGACY_PARAMS, k=float(k), reg=float(reg), slope=1.0, hfa=0.0, sig=1.0)
    pre = evaluate(rows, base, shrink_s)
    X = np.column_stack([(pre.home_matchup - pre.away_matchup).values, 1.0 - rows.neutral.values.astype(float)])
    y = rows.result.values.astype(float)
    slope, hfa = np.linalg.lstsq(X, y, rcond=None)[0]
    fitted = replace(base, slope=float(slope), hfa=float(hfa))
    res = y - evaluate(rows, fitted, shrink_s).margin.values
    return replace(fitted, sig=float(np.sqrt((res**2).sum() / (len(y) - 2))))


def fit_params(rows, formula) -> Tuple[Params, Optional[float]]:
    """Fit on the given rows only. Returns (params, shrink_s); shrink_s None means flat REG won, and otherwise
    params.reg is unused. QB_K, QB_PRIOR and the rush constants stay at their current values."""
    _check_formula(formula)
    if formula == 'legacy':
        return _fit_one(rows, LEGACY_FIT_K, LEGACY_FIT_REG, None), None
    combos = [(float(k), reg, None) for k in GRID_K for reg in GRID_REG]
    combos += [(float(k), 1.0, float(s)) for k in GRID_K for s in GRID_SHRINK]
    y = rows.result.values.astype(float)
    best, best_ll = None, math.inf
    for k, reg, shrink_s in combos:
        params = _fit_one(rows, k, reg, shrink_s)
        ll = _log_loss(y, evaluate(rows, params, shrink_s).p_home.values)
        if ll < best_ll - 1e-12:     # float noise must not pick between combos that predict identically
            best, best_ll = (params, shrink_s), ll
    return best


def leave_one_season_out(rows, formula):
    """Each season is scored with constants fit on the others. Returns (predictions, {season: (params, shrink_s)})."""
    preds, fits = [], {}
    for season in sorted(rows.season.unique()):
        season = int(season)
        params, shrink_s = fit_params(rows[rows.season != season], formula)
        fits[season] = (params, shrink_s)
        preds.append(evaluate(rows[rows.season == season], params, shrink_s))
    return pd.concat(preds, ignore_index=True), fits


def forward_check(train_rows, forward_rows, formula):
    """Score forward seasons with constants fit on the training seasons only. Returns (predictions, fit)."""
    if set(train_rows.season) & set(forward_rows.season):
        raise ValueError('forward season appears in the training rows')
    params, shrink_s = fit_params(train_rows, formula)
    return evaluate(forward_rows, params, shrink_s), (params, shrink_s)


def mean_dropbacks_per_team_game(seasons, data_dir) -> float:
    total, team_games = 0, 0
    for season in seasons:
        done, _, pbp = load(season, _season_dir(data_dir, season))
        total += len(dropbacks(pbp))
        team_games += 2*len(done)
    return total / team_games


def check_db_per_game(computed, constant) -> None:
    if round(computed) != constant:
        raise SystemExit(f'DB_PER_GAME is {constant} but the data gives {computed:.2f}, which rounds to '
                         f'{round(computed)}. Update projections/constants.py and rerun.')


def _ensure_data(season, data_dir):
    d = _season_dir(data_dir, season)
    if not all(os.path.exists(os.path.join(d, f)) for f in ('games.csv', 'pbp.parquet')):
        download(season, d)


def _num(x, places):
    return '-' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:.{places}f}'


def _score_row(label, version, preds):
    s = score(preds)
    if not s['n']:
        return f'| {version} | {label} | 0 | no games | no games | no games |'
    return (f"| {version} | {label} | {s['n']} | {_num(s['rmse'], 2)} | {_num(s['log_loss'], 4)} "
            f"| {_num(s['winners_pct'], 1)} |")


def _results_table(by_version) -> list:
    lines = ['| Version | Split | Games | RMSE | Log loss | Winners % |', '|---|---|---:|---:|---:|---:|']
    for version, preds in by_version.items():
        lines.append(_score_row('All', version, preds))
        for label, lo, hi in SPLITS:
            lines.append(_score_row(label, version, preds[preds.week.between(lo, hi)]))
    return lines


def _season_table(by_version) -> list:
    lines = ['| Version | Season | Games | RMSE | Log loss | Winners % |', '|---|---|---:|---:|---:|---:|']
    for version, preds in by_version.items():
        for season in sorted(preds.season.unique()):
            lines.append(_score_row(str(season), version, preds[preds.season == season]))
    return lines


def _week_table(by_version, weeks) -> list:
    lines = ['| Version | Week | Games | RMSE | Log loss | Winners % |', '|---|---|---:|---:|---:|---:|']
    for version, preds in by_version.items():
        for week in weeks:
            lines.append(_score_row(str(week), version, preds[preds.week == week]))
    return lines


def _calibration_table(by_version) -> list:
    lines = ['| Version | Predicted home win | Games | Mean predicted | Actual |', '|---|---|---:|---:|---:|']
    for version, preds in by_version.items():
        for b in score(preds)['calibration']:
            lines.append(f"| {version} | {b['bin']} | {b['n']} | {_num(b['mean_p'], 3)} | {_num(b['actual'], 3)} |")
    return lines


def _constants_table(fits) -> list:
    lines = ['| Version | Fit on | K | Weighting | SLOPE | HFA | SIG |', '|---|---|---:|---|---:|---:|---:|']
    for version, label, (p, shrink_s) in fits:
        weighting = f'flat REG={p.reg:.1f}' if shrink_s is None else f'shrinkage s={shrink_s:.0f}'
        lines.append(f'| {version} | {label} | {p.k:.0f} | {weighting} | {p.slope:.5f} | {p.hfa:.3f} | {p.sig:.3f} |')
    return lines


def build_report(seasons, forward, legacy_train, rate_train, legacy_fwd, rate_fwd, db_mean) -> str:
    train_label = ', '.join(str(s) for s in seasons)
    a_train = evaluate(legacy_train, LEGACY_PARAMS, None)
    a_fwd = evaluate(legacy_fwd, LEGACY_PARAMS, None)
    b_train, b_fits = leave_one_season_out(legacy_train, 'legacy')
    c_train, c_fits = leave_one_season_out(rate_train, 'rate')
    b_fwd, b_fit = forward_check(legacy_train, legacy_fwd, 'legacy')
    c_fwd, c_fit = forward_check(rate_train, rate_fwd, 'rate')
    train = {'A': a_train, 'B': b_train, 'C': c_train}
    fwd = {'A': a_fwd, 'B': b_fwd, 'C': c_fwd}

    lines = ['# Model backtest', '',
             f'Walk-forward backtest over {train_label}, with {forward} as a forward check. Every prediction uses '
             'only games from strictly earlier weeks of the same season, including the rule that the starter is '
             'the QB who threw most in the team\'s previous game. Week 1 ratings are all zero, so Week 1 margins '
             'are home-field advantage alone. Betting lines are not used anywhere.', '',
             '## Versions', '',
             f'- **Version A**: today\'s model with its current constants. Those constants were calibrated on '
             f'{forward} Weeks 6-8, so only A\'s constants are in-sample on those weeks. Its ratings are walk-forward. '
             'Nothing is fit here.',
             f'- **Version B**: today\'s formula, with SLOPE, HFA and SIG refit at K={LEGACY_FIT_K:.0f}, '
             f'REG={LEGACY_FIT_REG}, scored leave-one-season-out.',
             '- **Version C**: the per-dropback formula, with K, REG or shrinkage chosen by lowest training log '
             'loss and SLOPE, HFA and SIG refit, scored leave-one-season-out.', '',
             'Forward-check constants for B and C are fit on all training seasons and never see '
             f'{forward}. QB_K, QB_PRIOR and the rush constants are held at their current values in every version. '
             f'Version B\'s K and REG are fixed at values from the {forward} Weeks 6-8 calibration.',
             '', '## Data', '', '| Season | Completed games | Ties | Last week |', '|---|---:|---:|---:|']
    for rows in (legacy_train, legacy_fwd):
        for season in sorted(rows.season.unique()):
            r = rows[rows.season == season]
            lines.append(f'| {season} | {len(r)} | {int((r.result == 0).sum())} | {int(r.week.max())} |')
    lines += ['', f'DB_PER_GAME: computed {db_mean:.2f} dropbacks per team-game over {train_label}, which rounds to '
              f'{round(db_mean)}. The constant is {DB_PER_GAME}.', '',
              f'## Results: leave-one-season-out, {train_label}', '',
              'Version A uses its fixed constants on the same games.', ''] + _results_table(train)
    lines += ['', '### By held-out season', ''] + _season_table(train)
    lines += ['', '### Early season by week', ''] + _week_table(train, range(1, 7))
    lines += ['', f'## Forward check: {forward}', '',
              f'Constants fit on {train_label} only. Version A\'s constants were fit on {forward} Weeks 6-8, but its ratings '
              'are walk-forward.', '']
    if not (legacy_fwd.week >= 13).any():
        lines += [f'{forward} has no late-season games, so this check cannot test late-season behavior.', '']
    lines += _results_table(fwd)
    w68 = a_fwd[a_fwd.week.between(6, 8)]
    zero_rmse = f'{np.sqrt(np.mean(w68.result.values.astype(float)**2)):.2f}' if len(w68) else 'not available'
    lines += ['', f'### Version A on {forward} Weeks 6-8 (constants fit here, ratings walk-forward)', '',
              '| Version | Split | Games | RMSE | Log loss | Winners % |', '|---|---|---:|---:|---:|---:|',
              _score_row('Weeks 6-8', 'A', w68), '',
              f'The previously documented figure for A, RMSE about 10.9 with 27 of 41 winners, used ratings that '
              f'included the games being scored (look-ahead). Reproduced on 42 games, ratings through Week 8 give '
              f'RMSE 10.78 and 27 of 42 winners (measured on this data on 2026-11-03, not recomputed by this '
              f'script). The walk-forward row above is the honest comparison, and predicting a margin of 0 gives '
              f'RMSE {zero_rmse}.']
    lines += ['', f'## Calibration: {train_label}', '',
              'Ties are excluded. Bins are by predicted home-win probability.', ''] + _calibration_table(train)
    lines += ['', f'## Calibration: {forward}', ''] + _calibration_table(fwd)
    fits = [('B', f'all but {s}', f) for s, f in b_fits.items()] + [('B', train_label, b_fit)]
    fits += [('C', f'all but {s}', f) for s, f in c_fits.items()] + [('C', train_label, c_fit)]
    lines += ['', '## Chosen constants', '', f'Version A: {LEGACY_PARAMS}', ''] + _constants_table(fits)
    wins = [f[1] is None for f in list(c_fits.values()) + [c_fit]]
    lines += ['', f'Flat vs. shrinkage for Version C: flat REG won {sum(wins)} of {len(wins)} fits, shrinkage won '
              f'{len(wins) - sum(wins)}. Version B is fixed at flat K=800 and REG=0.8 while C searches a grid, so this line '
              'compares weightings within C only and does not show that shrinkage beats flat weighting for '
              'today\'s formula. The chosen K also varied widely by fold, from 50 to 400.', '',
              '## Limits', '',
              f'- QB_K, QB_PRIOR and the rush constants date from the {forward} Weeks 6-8 calibration, so they are '
              f'not independent of the {forward} forward check. Version B\'s fixed K={LEGACY_FIT_K:.0f} and '
              f'REG={LEGACY_FIT_REG} come from the same calibration, which could favor B slightly in the forward '
              'check.',
              '- Scoring rules: ties count in RMSE only. A zero margin gets half credit for winners. The Games '
              'column includes ties, while Winners % and Log loss exclude them.',
              '- The direct solve for Version C was adopted after the 2022-2025 by-week results had been seen, and '
              'the change did not improve C.',
              f'- DB_PER_GAME is computed over all of {train_label}, including each held-out season. It is one '
              'rounded scale factor that SLOPE rescales against, so the effect is small.',
              '- Version C uses a direct solve of the opponent adjustment because the original 50-iteration loop does '
              'not converge on sparse early-season schedules. Versions A and B keep the loop as-is, as it is part '
              'of today\'s formula. The two methods agree once the schedule is connected and the loop has settled, '
              'to within 1e-6 from about Week 8 on 2022-2025 data.',
              '- The direct solve changes early values but does not make them reliable. After one game each it '
              'splits a gap evenly between offense and defense. The loop keeps the full gap in both units, so on one '
              'pairing with a raw +10/+10 the loop gives +10/+10 and the solve gives +5/+5, and the loop counts the '
              'gap twice in offense minus defense. Week 3 '
              'ratings can still be large, because two weeks of games leave long cycles that barely separate '
              'offense from defense. See the by-week table.',
              '- With flat weights, K and REG only act through K/REG once SLOPE is refit, so grid pairs with the same '
              'ratio predict identically. The first such pair in the grid is reported.', '']
    return '\n'.join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--seasons', type=int, nargs='+', required=True, help='seasons for leave-one-season-out')
    ap.add_argument('--forward', type=int, required=True, help='forward-check season')
    ap.add_argument('--out', required=True, help='report path')
    ap.add_argument('--data-dir', default=DEFAULT_DATA_DIR, help='download directory; keep it outside the repo')
    args = ap.parse_args(argv)
    if args.forward in args.seasons:
        ap.error('--forward season must not be in --seasons')

    for season in args.seasons + [args.forward]:
        _ensure_data(season, args.data_dir)
    db_mean = mean_dropbacks_per_team_game(args.seasons, args.data_dir)
    check_db_per_game(db_mean, DB_PER_GAME)

    def rows_for(seasons, formula):
        return pd.concat([walk_forward_rows(s, args.data_dir, formula) for s in seasons], ignore_index=True)

    text = build_report(args.seasons, args.forward,
                        rows_for(args.seasons, 'legacy'), rows_for(args.seasons, 'rate'),
                        rows_for([args.forward], 'legacy'), rows_for([args.forward], 'rate'), db_mean)
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, 'w') as f:
        f.write(text)
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
