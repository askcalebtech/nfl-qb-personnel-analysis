"""ANY/A Value ratings, opponent adjustment, starting-QB adjustment and rushing EPA."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .constants import TEAMS


@dataclass
class Raw:
    off: dict
    def_: dict
    lg: float
    off_n: dict
    def_n: dict


@dataclass
class RatingSet:
    off_pred: dict
    def_pred: dict
    off_season: dict
    def_season: dict
    qb_adj_season: dict
    qb_adj_pred: dict
    starter: dict
    warnings: list = field(default_factory=list)
    ro: dict = field(default_factory=dict)
    rd: dict = field(default_factory=dict)


def dropbacks(pbp):
    db = pbp[(pbp.two_point_attempt != 1) & ((pbp.pass_attempt == 1) | (pbp.sack == 1))]
    yds = np.where(db.sack == 1, db.yards_gained, db.passing_yards.fillna(0))
    return db.assign(pts=yds + 20*db.pass_touchdown.fillna(0) - 45*db.interception.fillna(0))


def raw_values(db) -> Raw:
    lg = db.pts.mean() if len(db) else 0.0
    o = db.groupby('posteam').pts.agg(['size', 'sum'])
    d_ = db.groupby('defteam').pts.agg(['size', 'sum'])
    off = (o['sum'] - lg*o['size']).to_dict()
    def_ = (lg*d_['size'] - d_['sum']).to_dict()
    return Raw(off={t: off.get(t, 0) for t in TEAMS}, def_={t: def_.get(t, 0) for t in TEAMS}, lg=lg,
               off_n={t: int(o['size'].get(t, 0)) for t in TEAMS},
               def_n={t: int(d_['size'].get(t, 0)) for t in TEAMS})


def rush_epa(pbp):
    ru = pbp[(pbp.rush == 1) & pbp.epa.notna() & pbp.posteam.notna()]
    ix = {t: i for i, t in enumerate(TEAMS)}
    n = len(ru)
    X = np.zeros((n, 64))
    X[np.arange(n), ru.posteam.map(ix)] = 1
    X[np.arange(n), 32 + ru.defteam.map(ix)] = -1
    epa = ru.epa.astype(float)
    y = epa.values - epa.mean() if n else np.zeros(0)
    b = np.linalg.solve(X.T @ X + 50*np.eye(64), X.T @ y)
    return {t: b[ix[t]] for t in TEAMS}, {t: b[32 + ix[t]] for t in TEAMS}


def _last_game_ids(done):
    out = {}
    for t in TEAMS:
        tg = done[(done.home_team == t) | (done.away_team == t)]
        out[t] = tg.sort_values('week').game_id.iloc[-1] if len(tg) else None
    return out


def pick_starters(db, done, overrides) -> dict:
    """Override if given, else the QB with most dropbacks in the team's latest game; None if unknown."""
    last_gid = _last_game_ids(done)
    starter = {}
    for t in TEAMS:
        if t in overrides:
            starter[t] = overrides[t]
        elif last_gid[t] is None:
            starter[t] = None
        else:
            names = db[(db.game_id == last_gid[t]) & (db.posteam == t)].passer_player_name.value_counts()
            starter[t] = names.index[0] if len(names) else None
    return starter


def _opponent_adjust(done, raw):
    opps = {t: [] for t in TEAMS}
    for r in done.itertuples():
        opps[r.home_team].append(r.away_team)
        opps[r.away_team].append(r.home_team)
    played = [t for t in TEAMS if opps[t]]
    aO = {t: raw.off[t] if t in played else 0.0 for t in TEAMS}
    aD = {t: raw.def_[t] if t in played else 0.0 for t in TEAMS}
    for _ in range(50):
        nO = {t: raw.off[t] + np.mean([aD[x] for x in opps[t]]) for t in played}
        nD = {t: raw.def_[t] + np.mean([aO[x] for x in opps[t]]) for t in played}
        if not played:
            break
        mo, md = np.mean(list(nO.values())), np.mean(list(nD.values()))
        aO = {t: nO[t]-mo if t in played else 0.0 for t in TEAMS}
        aD = {t: nD[t]-md if t in played else 0.0 for t in TEAMS}
    return aO, aD


def build_ratings_legacy(done, pbp, overrides, params) -> RatingSet:
    db = dropbacks(pbp)
    raw = raw_values(db)
    lg = raw.lg
    aO, aD = _opponent_adjust(done, raw)

    # Each QB's ANY/A per dropback, shrunk toward a below-average prior; the team's offense moves by
    # (projected starter's rate - dropback-weighted rate of the QBs who actually played) x team dropbacks.
    q = db.groupby(['posteam', 'passer_player_name']).pts.agg(['size', 'mean']).reset_index()
    q['rate'] = (q['size']*q['mean'] + params.qb_k*(lg + params.qb_prior)) / (q['size'] + params.qb_k)
    qrate = {(r.posteam, r.passer_player_name): r.rate for r in q.itertuples()}
    qmix = {}
    for t in TEAMS:
        qt = q[q.posteam == t]
        qmix[t] = (qt['size']*qt.rate).sum() / qt['size'].sum() if len(qt) else 0.0
    starter = pick_starters(db, done, overrides)
    warnings, qb_adj = [], {}
    for t in TEAMS:
        if t in overrides and (t, starter[t]) not in qrate:
            warnings.append(f"{t}: starter {starter[t]} has no dropbacks for this team this season; using prior")
        if starter[t] is None or raw.off_n[t] == 0:
            qb_adj[t] = 0.0
            continue
        rate = qrate.get((t, starter[t]), lg + params.qb_prior)
        qb_adj[t] = (rate - qmix[t]) * raw.off_n[t]
        aO[t] += qb_adj[t]

    ro, rd = rush_epa(pbp)
    reg = params.reg
    return RatingSet(off_pred={t: aO[t]*reg for t in TEAMS}, def_pred={t: aD[t]*reg for t in TEAMS},
                     off_season=dict(aO), def_season=dict(aD),
                     qb_adj_season=qb_adj, qb_adj_pred={t: qb_adj[t]*reg for t in TEAMS},
                     starter=starter, warnings=warnings, ro=ro, rd=rd)
