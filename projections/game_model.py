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


def compute_margin(off_home, def_home, off_away, def_away, rush_edge, neutral, params) -> Prediction:
    """The one margin formula, used by predict and by the backtest. Ratings are already regressed. rush_edge is
    the per-rush EPA edge for the home side: (home off - away def) - (away off - home def)."""
    curve = lambda x: params.k*math.tanh(x/params.k)
    home_matchup = curve(off_home - def_away)
    away_matchup = curve(off_away - def_home)
    matchup_points = params.slope*(home_matchup - away_matchup)
    hfa = 0 if neutral else params.hfa
    m = matchup_points + hfa
    nudge = 0.0
    if abs(m) < params.rush_window:
        edge = params.rushes*rush_edge
        nudge = max(-params.rush_cap, min(params.rush_cap, params.rush_pts*edge))
    m += nudge
    return Prediction(margin=m, p_home=_phi(m/params.sig), nudge=nudge, home_matchup=home_matchup,
                      away_matchup=away_matchup, matchup_points=matchup_points, hfa=hfa)


def home_rush_edge(away, home, rs) -> float:
    return (rs.ro[home] - rs.rd[away]) - (rs.ro[away] - rs.rd[home])


def predict(away, home, neutral, rs, params) -> Prediction:
    """Uses rs.off_pred/def_pred as already regressed; applies no regression of its own."""
    return compute_margin(rs.off_pred[home], rs.def_pred[home], rs.off_pred[away], rs.def_pred[away],
                          home_rush_edge(away, home, rs), neutral, params)
