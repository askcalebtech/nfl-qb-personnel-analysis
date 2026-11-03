"""Monte Carlo season simulation with NFL tiebreakers."""
import numpy as np

from .constants import CONF, DIV, DOF, TEAMS

_pct = lambda rec: (rec[0]+.5*rec[2])/sum(rec) if sum(rec) else 0


def simulate(done, games, n_sims=20000, seed=7) -> dict:
    """done: completed-games frame (away_team, home_team, result); games: dicts with away, home, p_home."""
    past = [(r.away_team, r.home_team, r.result) for r in done.itertuples()]
    rng = np.random.default_rng(seed)
    U = rng.random((n_sims, len(games)))
    cnt = {k: {t: 0 for t in TEAMS} for k in ('div', 'po', 'seed1')}
    wins = {t: [] for t in TEAMS}
    for s in range(n_sims):
        res = past + [(gm['away'], gm['home'], 1 if U[s, i] < gm['p_home'] else -1) for i, gm in enumerate(games)]
        rec = {t: [0,0,0] for t in TEAMS}; dvr = {t: [0,0,0] for t in TEAMS}
        cfr = {t: [0,0,0] for t in TEAMS}; h2h = {}
        for a, h, x in res:
            for t, op, won in ((h, a, x > 0), (a, h, x < 0)):
                k = 0 if won else (2 if x == 0 else 1)
                rec[t][k] += 1
                if DOF[t] == DOF[op]: dvr[t][k] += 1
                if CONF[t] == CONF[op]: cfr[t][k] += 1
                h2h.setdefault((t, op), [0,0,0])[k] += 1

        def rank(group, division):
            def key(t, tied):
                hh = [sum(h2h.get((t, o_), [0,0,0])[i] for o_ in tied if o_ != t) for i in range(3)]
                return (_pct(hh), _pct(dvr[t]) if division else 0, _pct(cfr[t]), rng.random())
            srt = sorted(group, key=lambda t: -_pct(rec[t])); out = []; i = 0
            while i < len(srt):
                j = i
                while j < len(srt) and _pct(rec[srt[j]]) == _pct(rec[srt[i]]): j += 1
                tied = srt[i:j]; out += sorted(tied, key=lambda t: key(t, tied), reverse=True); i = j
            return out

        for t in TEAMS: wins[t].append(rec[t][0] + .5*rec[t][2])
        for conf in ('AFC', 'NFC'):
            winners = [rank(DIV[dv], True)[0] for dv in DIV if dv.startswith(conf)]
            wc = rank([t for t in TEAMS if CONF[t] == conf and t not in winners], False)[:3]
            for t in winners: cnt['div'][t] += 1
            for t in winners + wc: cnt['po'][t] += 1
            cnt['seed1'][rank(winners, False)[0]] += 1

    out = {}
    for t in TEAMS:
        lo, hi = np.percentile(wins[t], [10, 90])
        out[t] = dict(avg_wins=float(np.mean(wins[t])), p10=float(lo), p90=float(hi),
                      div=cnt['div'][t]/n_sims, playoffs=cnt['po'][t]/n_sims, seed1=cnt['seed1'][t]/n_sims)
    return out
