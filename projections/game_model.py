"""Win probability for a single game from a RatingSet."""
import math
from dataclasses import dataclass


@dataclass
class Prediction:
    margin: float
    p_home: float
    nudge: float
    home_matchup: float
    away_matchup: float
    matchup_points: float
    hfa: float


def _phi(z):
    return 0.5*(1 + math.erf(z/math.sqrt(2)))


def predict(away, home, neutral, rs, params) -> Prediction:
    """Uses rs.off_pred/def_pred as already regressed; applies no regression of its own."""
    curve = lambda x: params.k*math.tanh(x/params.k)
    home_matchup = curve(rs.off_pred[home] - rs.def_pred[away])
    away_matchup = curve(rs.off_pred[away] - rs.def_pred[home])
    matchup_points = params.slope*(home_matchup - away_matchup)
    hfa = 0 if neutral else params.hfa
    m = matchup_points + hfa
    nudge = 0.0
    if abs(m) < params.rush_window:
        edge = params.rushes*((rs.ro[home] - rs.rd[away]) - (rs.ro[away] - rs.rd[home]))
        nudge = max(-params.rush_cap, min(params.rush_cap, params.rush_pts*edge))
    m += nudge
    return Prediction(margin=m, p_home=_phi(m/params.sig), nudge=nudge, home_matchup=home_matchup,
                      away_matchup=away_matchup, matchup_points=matchup_points, hfa=hfa)
