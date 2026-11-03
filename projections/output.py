"""Build, validate and write the weekly projections JSON."""
import json
import math
import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from .constants import CONF, DOF, NAMES, TEAMS
from .game_model import predict


def _num(x, nd=4):
    """Rounded float, or None for missing."""
    if x is None or pd.isna(x):
        return None
    return round(float(x), nd)


def _txt(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else str(x)


def _ml_prob(ml):
    if ml is None or pd.isna(ml):
        return None
    return -ml/(-ml + 100) if ml < 0 else 100/(ml + 100)


def build_games(todo, rs, params) -> list:
    """Predictions for unplayed games. Betting lines are used only for the display fields mkt_home and spread."""
    games = []
    for r in todo.to_dict('records'):
        neutral = r.get('location') == 'Neutral'
        pr = predict(r['away_team'], r['home_team'], neutral, rs, params)
        pa, ph = _ml_prob(r.get('away_moneyline')), _ml_prob(r.get('home_moneyline'))
        mkt = ph/(pa + ph) if pa and ph else None
        games.append(dict(
            game_id=r['game_id'], week=int(r['week']), gameday=_txt(r.get('gameday')), away=r['away_team'],
            home=r['home_team'], neutral=neutral, stadium=_txt(r.get('stadium')), p_home=pr.p_home,
            margin=pr.margin, nudge=pr.nudge, mkt_home=mkt, spread=_num(r.get('spread_line')),
            components=dict(home_matchup=pr.home_matchup, away_matchup=pr.away_matchup,
                            matchup_points=pr.matchup_points, hfa=pr.hfa, nudge=pr.nudge,
                            home_qb_adj_pts=params.slope*rs.qb_adj_pred[r['home_team']],
                            away_qb_adj_pts=params.slope*rs.qb_adj_pred[r['away_team']])))
    return games


def _records(done):
    rec = {t: [0, 0, 0] for t in TEAMS}
    for r in done.itertuples():
        x = r.result
        rec[r.home_team][0 if x > 0 else (2 if x == 0 else 1)] += 1
        rec[r.away_team][0 if x < 0 else (2 if x == 0 else 1)] += 1
    return {t: f"{w}-{l}" + (f"-{ti}" if ti else "") for t, (w, l, ti) in rec.items()}


def _through_week(done, todo) -> int:
    """Last week in which every scheduled game has a result (0 if none)."""
    if not len(done):
        return 0
    weeks = done.week
    if len(todo):
        weeks = weeks[weeks < todo.week.min()]
    return int(weeks.max()) if len(weeks) else 0


def has_later_results(done, through_week) -> bool:
    """True once any game after through_week has been played (a partial week is under way)."""
    return bool(len(done) and (done.week > through_week).any())


def build_payload(season, done, todo, rs, raw, games, sim, model_version=None, generated_at=None) -> dict:
    from .constants import MODEL_VERSION
    record = _records(done)
    teams = []
    for t in TEAMS:
        s = sim[t]
        teams.append(dict(
            team=t, name=NAMES[t], conference=CONF[t], division=DOF[t], record=record[t],
            off=_num(raw.off[t], 2), **{'def': _num(raw.def_[t], 2)},
            adj_off=_num(rs.off_season[t], 2), adj_def=_num(rs.def_season[t], 2),
            starter=rs.starter[t], qb_adj=_num(rs.qb_adj_season[t], 2),
            rush_off=_num(rs.ro[t], 5), rush_def=_num(rs.rd[t], 5),
            avg_wins=_num(s['avg_wins'], 3), wins_p10=_num(s['p10'], 1), wins_p90=_num(s['p90'], 1),
            div=_num(s['div']), playoffs=_num(s['playoffs']), seed1=_num(s['seed1'])))
    out_games = []
    for g in sorted(games, key=lambda g: (g['week'], g['gameday'] or '', g['game_id'])):
        c = g['components']
        out_games.append(dict(
            game_id=g['game_id'], week=g['week'], gameday=g['gameday'], away=g['away'], home=g['home'],
            neutral=bool(g['neutral']), stadium=g['stadium'], p_home=_num(g['p_home']), margin=_num(g['margin']),
            nudge=_num(g['nudge']), mkt_home=_num(g['mkt_home']), spread=_num(g['spread']),
            components={k: _num(v) for k, v in c.items()}))
    through = _through_week(done, todo)
    last_result = _txt(done.gameday.max()) if len(done) and 'gameday' in done else None
    return dict(season=int(season), through_week=through, last_result_date=last_result,
                generated_at=generated_at or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                league_anya=_num(raw.lg, 4) if len(done) else None,
                model_version=model_version or MODEL_VERSION,
                warnings=list(rs.warnings), teams=teams, games=out_games)


def _walk(x, path="payload"):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, x


def validate(payload, done, pbp, previous: Optional[dict] = None) -> None:
    for path, v in _walk(payload):
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError(f"non-finite number at {path}")
    teams = payload.get('teams', [])
    if len(teams) != 32 or {t.get('team') for t in teams} != set(TEAMS):
        raise ValueError(f"expected 32 distinct teams, got {len(teams)}")
    probs = [(f"games[{i}].p_home", g.get('p_home')) for i, g in enumerate(payload.get('games', []))]
    probs += [(f"games[{i}].mkt_home", g.get('mkt_home')) for i, g in enumerate(payload.get('games', []))]
    for t in teams:
        probs += [(f"{t['team']}.{k}", t.get(k)) for k in ('div', 'playoffs', 'seed1')]
    for path, p in probs:
        if p is None and path.endswith('mkt_home'):
            continue
        if p is None or not (0 <= p <= 1):
            raise ValueError(f"probability out of range at {path}: {p}")
    missing = set(done.game_id) - set(pbp.game_id)
    if missing:
        raise ValueError(f"{len(missing)} completed games have no play-by-play rows: {sorted(missing)[:5]}")
    tw = payload.get('through_week')
    if not isinstance(tw, int) or not (0 <= tw <= 18):
        raise ValueError(f"through_week {tw} outside 0-18")
    if previous and previous.get('season') == payload.get('season') \
            and payload['through_week'] < previous.get('through_week', 0):
        raise ValueError(f"through_week {payload['through_week']} is lower than published "
                         f"{previous['through_week']}")


def _dumps(payload) -> str:
    return json.dumps(payload, indent=1, sort_keys=True, allow_nan=False) + "\n"


def write_if_changed(payload, path) -> bool:
    text = _dumps(payload)  # raises on NaN before anything on disk is touched
    strip = lambda d: {k: v for k, v in d.items() if k != 'generated_at'}
    if os.path.exists(path):
        try:
            with open(path) as f:
                if strip(json.load(f)) == strip(json.loads(text)):
                    return False
        except ValueError:
            pass
    _atomic_write(path, text)
    return True


def _atomic_write(path, text) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def snapshot_path(payload, dir) -> str:
    return os.path.join(dir, f"{payload['season']}-through-wk{payload['through_week']:02d}.json")


def write_snapshot(payload, dir, locked=False) -> str:
    """Write the snapshot for payload's through_week. When locked (a game after through_week has been played),
    an existing snapshot is kept so the pre-game predictions survive."""
    text = _dumps(payload)
    path = snapshot_path(payload, dir)
    if locked and os.path.exists(path):
        return path
    _atomic_write(path, text)
    return path


def publish(payload, out, snapshots, locked=False) -> bool:
    """Write the output if changed, and the snapshot if the output changed or this week's snapshot is missing.
    Returns whether the output changed. See write_snapshot for locked."""
    changed = write_if_changed(payload, out)
    if changed or not os.path.exists(snapshot_path(payload, snapshots)):
        write_snapshot(payload, snapshots, locked)
    return changed
