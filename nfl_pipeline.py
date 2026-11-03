"""Weekly 2026 NFL projection pipeline (ANY/A Value model).

Steps: download nflverse play-by-play + schedule -> ANY/A Value ratings -> opponent adjustment
-> rushing EPA tiebreaker -> win probability per remaining game -> 20,000-season Monte Carlo.
Writes markdown + JSON to OUT (default ./nfl_out).

Usage: python3 nfl_pipeline.py [OUT_DIR] [--starters '{"BAL":"J.Fagnano","CHI":"C.Williams"}']
  --starters: projected starting QB per team (nflverse passer name, e.g. "L.Jackson"). Teams not listed
  default to the QB with the most dropbacks in that team's most recent game.
"""
import sys, os, math, json, subprocess, argparse
import numpy as np, pandas as pd

SEASON = 2026
ap = argparse.ArgumentParser(); ap.add_argument('out', nargs='?', default='nfl_out')
ap.add_argument('--starters', default='{}'); args = ap.parse_args()
OUT = args.out; STARTER_OVERRIDES = json.loads(args.starters)
os.makedirs(OUT, exist_ok=True)
DATA = os.path.join(OUT, 'data'); os.makedirs(DATA, exist_ok=True)
URLS = {'pbp.parquet': f'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{SEASON}.parquet',
        'games.csv': 'https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv'}
for fn, url in URLS.items():
    subprocess.run(['curl', '-sSLf', '-o', os.path.join(DATA, fn), url], check=True)

# Model constants (calibrated on 2026 Weeks 6-8: 41 games, with QB adjustment)
REG, K, SLOPE, HFA, SIG = 0.8, 800.0, 0.0150, 1.7, 11.0   # regression, curve, pts/unit, home pts, sd
QB_K, QB_PRIOR = 150, -1.5   # QB shrinkage (dropbacks) and prior (ANY/A vs league) for QB rates
RUSH_WINDOW, RUSH_PTS_PER_EPA, RUSH_CAP, RUSHES = 3.0, 0.5, 1.0, 25
N_SIMS = 20000

NAMES = {'BUF':'Bills','NE':'Patriots','NYJ':'Jets','MIA':'Dolphins','PIT':'Steelers','CIN':'Bengals','CLE':'Browns',
 'BAL':'Ravens','JAX':'Jaguars','HOU':'Texans','IND':'Colts','TEN':'Titans','DEN':'Broncos','KC':'Chiefs','LV':'Raiders',
 'LAC':'Chargers','NYG':'Giants','DAL':'Cowboys','WAS':'Commanders','PHI':'Eagles','MIN':'Vikings','DET':'Lions',
 'CHI':'Bears','GB':'Packers','CAR':'Panthers','TB':'Buccaneers','ATL':'Falcons','NO':'Saints','SF':'49ers',
 'SEA':'Seahawks','LA':'Rams','ARI':'Cardinals'}
DIV = {'AFC East':['BUF','NE','NYJ','MIA'],'AFC North':['PIT','CIN','CLE','BAL'],'AFC South':['JAX','HOU','IND','TEN'],
 'AFC West':['DEN','KC','LV','LAC'],'NFC East':['NYG','DAL','WAS','PHI'],'NFC North':['MIN','DET','CHI','GB'],
 'NFC South':['CAR','TB','ATL','NO'],'NFC West':['SF','SEA','LA','ARI']}
TEAMS = [t for ts in DIV.values() for t in ts]
DOF = {t: d for d, ts in DIV.items() for t in ts}; CONF = {t: DOF[t][:3] for t in TEAMS}

# ---------- data ----------
g = pd.read_csv(os.path.join(DATA, 'games.csv'))
g = g[(g.season == SEASON) & (g.game_type == 'REG')]
done = g[g.result.notna()]; todo = g[g.result.isna()]
cols = ['game_id','season_type','posteam','defteam','pass_attempt','sack','passing_yards','yards_gained',
        'pass_touchdown','interception','two_point_attempt','rush','epa','passer_player_name']
pbp = pd.read_parquet(os.path.join(DATA, 'pbp.parquet'), columns=cols)
pbp = pbp[(pbp.season_type == 'REG') & pbp.game_id.isin(done.game_id)]
thru_week = int(done.week.max())

# ---------- 1. ANY/A Value ----------
db = pbp[(pbp.two_point_attempt != 1) & ((pbp.pass_attempt == 1) | (pbp.sack == 1))]
yds = np.where(db.sack == 1, db.yards_gained, db.passing_yards.fillna(0))
db = db.assign(pts=yds + 20*db.pass_touchdown.fillna(0) - 45*db.interception.fillna(0))
lg = db.pts.mean()
o = db.groupby('posteam').pts.agg(['size','sum']); d_ = db.groupby('defteam').pts.agg(['size','sum'])
OFF = (o['sum'] - lg*o['size']).to_dict(); DEF = (lg*d_['size'] - d_['sum']).to_dict()

# ---------- 2. opponent adjustment ----------
opps = {t: [] for t in TEAMS}
for r in done.itertuples():
    opps[r.home_team].append(r.away_team); opps[r.away_team].append(r.home_team)
aO, aD = dict(OFF), dict(DEF)
for _ in range(50):
    nO = {t: OFF[t] + np.mean([aD[x] for x in opps[t]]) for t in TEAMS}
    nD = {t: DEF[t] + np.mean([aO[x] for x in opps[t]]) for t in TEAMS}
    mo, md = np.mean(list(nO.values())), np.mean(list(nD.values()))
    aO = {t: nO[t]-mo for t in TEAMS}; aD = {t: nD[t]-md for t in TEAMS}

# ---------- 2b. starting QB adjustment ----------
# Each QB's ANY/A per dropback, shrunk toward a below-average prior; the team's offense moves by
# (projected starter's rate - dropback-weighted rate of the QBs who actually played) x team dropbacks.
NT = o['size'].to_dict()
q = db.groupby(['posteam', 'passer_player_name']).pts.agg(['size', 'mean']).reset_index()
q['rate'] = (q['size']*q['mean'] + QB_K*(lg + QB_PRIOR)) / (q['size'] + QB_K)
QRATE = {(r.posteam, r.passer_player_name): r.rate for r in q.itertuples()}
QMIX = {t: (q[q.posteam == t]['size']*q[q.posteam == t].rate).sum() / q[q.posteam == t]['size'].sum() for t in TEAMS}
last_gid = {t: done[(done.home_team == t) | (done.away_team == t)].sort_values('week').game_id.iloc[-1] for t in TEAMS}
STARTER, QB_ADJ = {}, {}
for t in TEAMS:
    lastg = db[(db.game_id == last_gid[t]) & (db.posteam == t)]
    STARTER[t] = STARTER_OVERRIDES.get(t, lastg.passer_player_name.value_counts().index[0])
    rate = QRATE.get((t, STARTER[t]), lg + QB_PRIOR)   # QB with no 2026 dropbacks for this team -> prior
    QB_ADJ[t] = (rate - QMIX[t]) * NT[t]
    aO[t] += QB_ADJ[t]

# ---------- 3. rushing EPA (opponent-adjusted, ridge) ----------
ru = pbp[(pbp.rush == 1) & pbp.epa.notna() & pbp.posteam.notna()]
ix = {t: i for i, t in enumerate(TEAMS)}; n = len(ru)
X = np.zeros((n, 64)); X[np.arange(n), ru.posteam.map(ix)] = 1; X[np.arange(n), 32 + ru.defteam.map(ix)] = -1
y = ru.epa.values - ru.epa.mean()
b = np.linalg.solve(X.T @ X + 50*np.eye(64), X.T @ y)
RO = {t: b[ix[t]] for t in TEAMS}; RD = {t: b[32+ix[t]] for t in TEAMS}

# ---------- 4. game model ----------
Phi = lambda z: 0.5*(1 + math.erf(z/math.sqrt(2)))
curve = lambda x: K*math.tanh(x/K)
def predict(away, home, neutral):
    m = SLOPE*(curve(aO[home]*REG - aD[away]*REG) - curve(aO[away]*REG - aD[home]*REG)) + (0 if neutral else HFA)
    nudge = 0.0
    if abs(m) < RUSH_WINDOW:
        edge = RUSHES*((RO[home]-RD[away]) - (RO[away]-RD[home]))
        nudge = max(-RUSH_CAP, min(RUSH_CAP, RUSH_PTS_PER_EPA*edge))
    m += nudge
    return m, Phi(m/SIG), nudge
def ml_prob(ml):
    if pd.isna(ml): return None
    return -ml/(-ml+100) if ml < 0 else 100/(ml+100)

games = []
for r in todo.itertuples():
    m, p, nu = predict(r.away_team, r.home_team, r.location == 'Neutral')
    pa, ph = ml_prob(r.away_moneyline), ml_prob(r.home_moneyline)
    mkt = ph/(pa+ph) if pa and ph else None
    games.append(dict(week=int(r.week), away=r.away_team, home=r.home_team, neutral=r.location == 'Neutral',
                      stadium=r.stadium, margin=m, p_home=p, nudge=nu, mkt_home=mkt, spread=r.spread_line))

# ---------- 5. Monte Carlo ----------
past = [(r.away_team, r.home_team, r.result) for r in done.itertuples()]
rng = np.random.default_rng(7); U = rng.random((N_SIMS, len(games)))
cnt = {k: {t: 0 for t in TEAMS} for k in ('div', 'po', 'seed1')}; wins = {t: [] for t in TEAMS}
pct = lambda rec: (rec[0]+.5*rec[2])/sum(rec) if sum(rec) else 0
for s in range(N_SIMS):
    res = past + [(gm['away'], gm['home'], 1 if U[s, i] < gm['p_home'] else -1) for i, gm in enumerate(games)]
    rec = {t: [0,0,0] for t in TEAMS}; dvr = {t: [0,0,0] for t in TEAMS}; cfr = {t: [0,0,0] for t in TEAMS}; h2h = {}
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
            return (pct(hh), pct(dvr[t]) if division else 0, pct(cfr[t]), rng.random())
        srt = sorted(group, key=lambda t: -pct(rec[t])); out = []; i = 0
        while i < len(srt):
            j = i
            while j < len(srt) and pct(rec[srt[j]]) == pct(rec[srt[i]]): j += 1
            tied = srt[i:j]; out += sorted(tied, key=lambda t: key(t, tied), reverse=True); i = j
        return out
    for t in TEAMS: wins[t].append(rec[t][0] + .5*rec[t][2])
    for conf in ('AFC', 'NFC'):
        winners = [rank(DIV[dv], True)[0] for dv in DIV if dv.startswith(conf)]
        wc = rank([t for t in TEAMS if CONF[t] == conf and t not in winners], False)[:3]
        for t in winners: cnt['div'][t] += 1
        for t in winners + wc: cnt['po'][t] += 1
        cnt['seed1'][rank(winners, False)[0]] += 1

# ---------- 6. output ----------
cur = {t: [0,0,0] for t in TEAMS}
for a, h, x in past:
    for t, won in ((h, x > 0), (a, x < 0)): cur[t][0 if won else (2 if x == 0 else 1)] += 1
recstr = lambda r: f"{r[0]}-{r[1]}" + (f"-{r[2]}" if r[2] else "")
pc = lambda x: '<1%' if 0 < x < .005 else f"{x:.0%}"

md = [f"Ratings and results through Week {thru_week} ({len(done)} games). League ANY/A {lg:.2f}.", ""]
md += ["### Season outlook (20,000 simulations)", "",
       "| Team | Record | Avg wins | 80% range | Division | Playoffs | #1 seed |", "|---|---|---|---|---|---|---|"]
for dv, ts in DIV.items():
    md.append(f"| **{dv}** | | | | | | |")
    for t in sorted(ts, key=lambda t: -np.mean(wins[t])):
        lo, hi = np.percentile(wins[t], [10, 90])
        md.append(f"| {NAMES[t]} | {recstr(cur[t])} | {np.mean(wins[t]):.1f} | {lo:.0f}–{hi:.0f} | "
                  f"{pc(cnt['div'][t]/N_SIMS)} | {pc(cnt['po'][t]/N_SIMS)} | {pc(cnt['seed1'][t]/N_SIMS)} |")
weeks = sorted({gm['week'] for gm in games})
for w in weeks:
    md += ["", f"### Week {w}", "",
           "| Game | Away win % | Home win % | Projected | Rush nudge (pts to favorite) | Market (favorite) |",
           "|---|---|---|---|---|---|"]
    for gm in [x for x in games if x['week'] == w]:
        a, h, p, m = gm['away'], gm['home'], gm['p_home'], gm['margin']
        fav = h if m >= 0 else a
        nu = gm['nudge'] if fav == h else -gm['nudge']
        site = f" ({gm['stadium']})" if gm['neutral'] else ""
        mk = '—'
        if gm['mkt_home'] is not None:
            mfav = h if gm['mkt_home'] >= .5 else a
            mk = f"{NAMES[mfav]} {max(gm['mkt_home'], 1-gm['mkt_home']):.0%}"
        md.append(f"| {NAMES[a]} @ {NAMES[h]}{site} | {1-p:.0%} | {p:.0%} | {NAMES[fav]} by {abs(m):.1f} | "
                  f"{'%+.1f' % nu if abs(nu) >= .05 else '—'} | {mk} |")
md += ["", "### ANY/A Value ratings", "",
       "Off/Def/Total are the raw ANY/A Values. Adj Off and Adj Def are opponent-adjusted; Adj Off also includes the starting-QB adjustment.", "",
       "| Rank | Team | Off | Def | Total | Projected QB | QB adj | Adj Off | Adj Def |", "|---|---|---|---|---|---|---|---|---|"]
for i, t in enumerate(sorted(TEAMS, key=lambda t: -(OFF[t]+DEF[t])), 1):
    md.append(f"| {i} | {NAMES[t]} | {OFF[t]:.1f} | {DEF[t]:.1f} | {OFF[t]+DEF[t]:.1f} | {STARTER[t]} | "
              f"{QB_ADJ[t]:+.1f} | {aO[t]:.1f} | {aD[t]:.1f} |")
open(os.path.join(OUT, 'report.md'), 'w').write("\n".join(md))
json.dump({'through_week': thru_week, 'league_anya': lg,
           'ratings': {t: dict(off=OFF[t], def_=DEF[t], adj_off=aO[t], adj_def=aD[t], rush_off=RO[t], rush_def=RD[t],
                               starter=STARTER[t], qb_adj=QB_ADJ[t]) for t in TEAMS},
           'games': games,
           'sim': {t: dict(avg_wins=float(np.mean(wins[t])), div=cnt['div'][t]/N_SIMS, playoffs=cnt['po'][t]/N_SIMS,
                           seed1=cnt['seed1'][t]/N_SIMS) for t in TEAMS}},
          open(os.path.join(OUT, 'results.json'), 'w'), indent=1, default=float)
print(f"OK: through week {thru_week}, {len(games)} games remaining -> {OUT}/report.md")
