import copy
import json
import math

import pandas as pd
import pytest

from projections.constants import PARAMS, TEAMS
from projections.output import (build_games, build_payload, publish, validate, write_if_changed,
                                 write_snapshot)
from projections.ratings import build_ratings, dropbacks, raw_values
from projections.simulate import simulate
from tests.projections.test_ratings import frame, play

SEASON = 2026


def _done():
    rows = [('g1', 1, 'BUF', 'NE', 7), ('g2', 2, 'NYJ', 'MIA', -3), ('g3', 2, 'NE', 'BUF', 0)]
    return pd.DataFrame([dict(game_id=g, week=w, gameday=f'2026-09-{w:02d}', home_team=h, away_team=a, result=r)
                         for g, w, h, a, r in rows])


def _pbp(done):
    rows = []
    for r in done.itertuples():
        rows.append(play(game_id=r.game_id, posteam=r.home_team, defteam=r.away_team, passing_yards=30.0,
                         passer_player_name='H.QB'))
        rows.append(play(game_id=r.game_id, posteam=r.away_team, defteam=r.home_team, passing_yards=10.0,
                         passer_player_name='A.QB'))
        rows.append(play(game_id=r.game_id, posteam=r.home_team, defteam=r.away_team, pass_attempt=0, rush=1,
                         epa=0.1, passer_player_name=None))
    return frame(rows)


def _todo(ml=(-150, 130)):
    return pd.DataFrame([
        dict(game_id='t1', week=4, gameday='2026-09-27', home_team='BUF', away_team='MIA', location='Home',
             stadium='Highmark', spread_line=-3.5, home_moneyline=ml[0], away_moneyline=ml[1]),
        dict(game_id='t2', week=3, gameday='2026-09-20', home_team='NE', away_team='NYJ', location='Neutral',
             stadium=None, spread_line=float('nan'), home_moneyline=float('nan'), away_moneyline=float('nan')),
    ])


def make(done=None, todo=None, n_sims=50):
    done = _done() if done is None else done
    todo = _todo() if todo is None else todo
    pbp = _pbp(done) if len(done) else frame([])
    rs = build_ratings(done, pbp, {}, PARAMS)
    raw = raw_values(dropbacks(pbp))
    games = build_games(todo, rs, PARAMS)
    sim = simulate(done, games, n_sims=n_sims)
    payload = build_payload(SEASON, done, todo, rs, raw, games, sim)
    return payload, done, pbp, todo


def test_missing_market_and_spread_become_null():
    payload, *_ = make()
    out = json.loads(json.dumps(payload, allow_nan=False))
    g = [x for x in out['games'] if x['game_id'] == 't2'][0]
    assert g['mkt_home'] is None and g['spread'] is None and g['stadium'] is None
    assert [x for x in out['games'] if x['game_id'] == 't1'][0]['mkt_home'] is not None


def test_games_only_unplayed_sorted_and_components_sum():
    payload, *_ = make()
    assert [g['game_id'] for g in payload['games']] == ['t2', 't1']
    for g in payload['games']:
        c = g['components']
        assert c['matchup_points'] + c['hfa'] + c['nudge'] == pytest.approx(g['margin'], abs=1e-3)
        assert g['nudge'] == c['nudge']


def test_team_fields_and_records():
    payload, *_ = make()
    assert len(payload['teams']) == 32
    buf = [t for t in payload['teams'] if t['team'] == 'BUF'][0]
    assert buf['record'] == '1-0-1' and buf['conference'] == 'AFC' and buf['division'] == 'AFC East'
    assert 'def' in buf and 'adj_def' in buf and 'wins_p10' in buf and 'wins_p90' in buf
    assert payload['through_week'] == 2 and payload['season'] == SEASON


def test_nan_anywhere_fails_loudly():
    payload, done, pbp, _ = make()
    bad = copy.deepcopy(payload)
    bad['teams'][0]['adj_off'] = float('nan')
    with pytest.raises(ValueError):
        validate(bad, done, pbp)
    with pytest.raises(ValueError):
        json.dumps(bad, allow_nan=False)


def test_validate_accepts_good_payload():
    payload, done, pbp, _ = make()
    validate(payload, done, pbp)


def test_validate_rejects_31_teams():
    payload, done, pbp, _ = make()
    payload['teams'].pop()
    with pytest.raises(ValueError, match='32'):
        validate(payload, done, pbp)


def test_validate_rejects_probability_above_one():
    payload, done, pbp, _ = make()
    payload['games'][0]['p_home'] = 1.2
    with pytest.raises(ValueError):
        validate(payload, done, pbp)
    payload, done, pbp, _ = make()
    payload['teams'][0]['div'] = -0.1
    with pytest.raises(ValueError):
        validate(payload, done, pbp)


def test_validate_rejects_completed_game_missing_from_pbp():
    payload, done, pbp, _ = make()
    with pytest.raises(ValueError, match='play-by-play'):
        validate(payload, done, pbp[pbp.game_id != 'g2'])


def test_through_week_regression_rejected():
    payload, done, pbp, _ = make()
    validate(payload, done, pbp, previous={'season': SEASON, 'through_week': 2})
    with pytest.raises(ValueError, match='through_week'):
        validate(payload, done, pbp, previous={'season': SEASON, 'through_week': 3})
    validate(payload, done, pbp, previous={'season': SEASON - 1, 'through_week': 18})


def test_rerun_with_only_generated_at_changed_writes_nothing(tmp_path):
    payload, *_ = make()
    path = str(tmp_path / 'out' / 'p.json')
    payload['generated_at'] = '2026-11-03T10:00:00Z'
    assert write_if_changed(payload, path) is True
    before = open(path).read()
    later = dict(payload, generated_at='2026-11-10T10:00:00Z')
    assert write_if_changed(later, path) is False
    assert open(path).read() == before
    changed = dict(later, through_week=3)
    assert write_if_changed(changed, path) is True


def test_nan_write_fails_and_leaves_file_untouched(tmp_path):
    payload, *_ = make()
    path = str(tmp_path / 'p.json')
    write_if_changed(payload, path)
    before = open(path).read()
    bad = dict(payload, league_anya=float('nan'))
    with pytest.raises(ValueError):
        write_if_changed(bad, path)
    assert open(path).read() == before


def test_snapshot_overwrites_same_week(tmp_path):
    payload, *_ = make()
    p1 = write_snapshot(payload, str(tmp_path))
    assert p1.endswith('2026-through-wk02.json')
    p2 = write_snapshot(dict(payload, league_anya=1.0), str(tmp_path))
    assert p1 == p2 and len(list(tmp_path.iterdir())) == 1
    assert json.load(open(p2))['league_anya'] == 1.0


def test_no_remaining_games_produces_valid_payload():
    payload, done, pbp, _ = make(todo=_todo().iloc[0:0])
    assert payload['games'] == []
    validate(payload, done, pbp)
    json.dumps(payload, allow_nan=False)


def test_no_games_played_yet():
    done = _done().iloc[0:0]
    payload, done, pbp, _ = make(done=done)
    assert payload['through_week'] == 0 and payload['league_anya'] is None
    validate(payload, done, pbp)
    json.dumps(payload, allow_nan=False)


def test_market_never_reaches_model():
    a, *_ = make(todo=_todo(ml=(-150, 130)))
    b, *_ = make(todo=_todo(ml=(-400, 320)))
    ga = {g['game_id']: g for g in a['games']}
    gb = {g['game_id']: g for g in b['games']}
    assert ga['t1']['mkt_home'] != gb['t1']['mkt_home']
    assert ga['t1']['margin'] == gb['t1']['margin'] and ga['t1']['p_home'] == gb['t1']['p_home']
    assert {t['team']: t['avg_wins'] for t in a['teams']} == {t['team']: t['avg_wins'] for t in b['teams']}


def test_vig_removed():
    payload, *_ = make(todo=_todo(ml=(-150, 130)))
    g = [x for x in payload['games'] if x['game_id'] == 't1'][0]
    ph, pa = 150/250, 100/230
    assert g['mkt_home'] == pytest.approx(ph/(ph+pa), abs=1e-4)


def test_publish_writes_missing_snapshot_when_output_current(tmp_path):
    payload, *_ = make()
    out, snaps = str(tmp_path / 'p.json'), str(tmp_path / 'snaps')
    write_if_changed(payload, out)  # output already current, snapshot never written
    before = open(out).read()
    assert publish(dict(payload, generated_at='later'), out, snaps) is False
    assert open(out).read() == before
    assert [p.name for p in (tmp_path / 'snaps').iterdir()] == ['2026-through-wk02.json']


def test_publish_leaves_existing_snapshot_alone_when_unchanged(tmp_path):
    payload, *_ = make()
    out, snaps = str(tmp_path / 'p.json'), str(tmp_path / 'snaps')
    assert publish(payload, out, snaps) is True
    snap = tmp_path / 'snaps' / '2026-through-wk02.json'
    snap.write_text('sentinel')
    assert publish(payload, out, snaps) is False
    assert snap.read_text() == 'sentinel'


def test_failed_write_leaves_no_tmp_and_snapshot_is_atomic(tmp_path, monkeypatch):
    import os
    payload, *_ = make()
    snaps = str(tmp_path / 'snaps')
    path = write_snapshot(payload, snaps)
    good = open(path).read()

    def boom(src, dst):
        raise OSError('disk')
    monkeypatch.setattr(os, 'replace', boom)
    with pytest.raises(OSError):
        write_snapshot(dict(payload, league_anya=9.0), snaps)
    assert open(path).read() == good
    assert [p.name for p in (tmp_path / 'snaps').iterdir()] == ['2026-through-wk02.json']
    with pytest.raises(OSError):
        write_if_changed(dict(payload, through_week=3), str(tmp_path / 'p.json'))
    assert not (tmp_path / 'p.json.tmp').exists()
