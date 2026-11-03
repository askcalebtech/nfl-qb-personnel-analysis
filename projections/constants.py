"""League structure and model parameters."""
from dataclasses import dataclass

NAMES = {'BUF':'Bills','NE':'Patriots','NYJ':'Jets','MIA':'Dolphins','PIT':'Steelers','CIN':'Bengals','CLE':'Browns',
 'BAL':'Ravens','JAX':'Jaguars','HOU':'Texans','IND':'Colts','TEN':'Titans','DEN':'Broncos','KC':'Chiefs','LV':'Raiders',
 'LAC':'Chargers','NYG':'Giants','DAL':'Cowboys','WAS':'Commanders','PHI':'Eagles','MIN':'Vikings','DET':'Lions',
 'CHI':'Bears','GB':'Packers','CAR':'Panthers','TB':'Buccaneers','ATL':'Falcons','NO':'Saints','SF':'49ers',
 'SEA':'Seahawks','LA':'Rams','ARI':'Cardinals'}
DIV = {'AFC East':['BUF','NE','NYJ','MIA'],'AFC North':['PIT','CIN','CLE','BAL'],'AFC South':['JAX','HOU','IND','TEN'],
 'AFC West':['DEN','KC','LV','LAC'],'NFC East':['NYG','DAL','WAS','PHI'],'NFC North':['MIN','DET','CHI','GB'],
 'NFC South':['CAR','TB','ATL','NO'],'NFC West':['SF','SEA','LA','ARI']}
TEAMS = [t for ts in DIV.values() for t in ts]
DOF = {t: d for d, ts in DIV.items() for t in ts}
CONF = {t: DOF[t][:3] for t in TEAMS}


@dataclass(frozen=True)
class Params:
    reg: float          # regression of ratings toward zero
    k: float            # tanh curve scale
    slope: float        # points per rating unit
    hfa: float          # home-field points
    sig: float          # sd of margin
    qb_k: float         # QB shrinkage (dropbacks)
    qb_prior: float     # QB prior (ANY/A vs league)
    rush_window: float  # rush nudge applies when |margin| < window
    rush_pts: float     # points per unit of rush EPA edge
    rush_cap: float     # max absolute nudge
    rushes: int         # rushes per team per game


# SLOPE, HFA and SIG were refit on all completed games 2022-2026 (1,208 games) with K and REG held at 800 and 0.8.
# QB_K, QB_PRIOR and the rush constants come from the 2026 Weeks 6-8 calibration and were not refit.
# Refit by hand with `python3 -m projections.backtest --refit`; bump MODEL_VERSION whenever these change.
PARAMS = Params(reg=0.8, k=800.0, slope=0.00906, hfa=2.11, sig=13.06, qb_k=150, qb_prior=-1.5,
                rush_window=3.0, rush_pts=0.5, rush_cap=1.0, rushes=25)
MODEL_VERSION = "2026.1"
