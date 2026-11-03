import math

from pytest import approx

from projections.constants import LEGACY_PARAMS, TEAMS
from projections.game_model import compute_margin, predict
from projections.ratings import RatingSet


def make_rs(off=None, def_=None, ro=None, rd=None):
    z = {t: 0.0 for t in TEAMS}
    z.update({'A': 0.0, 'H': 0.0})
    def d(x):
        out = dict(z)
        out.update(x or {})
        return out
    return RatingSet(off_pred=d(off), def_pred=d(def_), off_season=d(off), def_season=d(def_),
                     qb_adj_season=dict(z), qb_adj_pred=dict(z), starter={}, warnings=[],
                     ro=d(ro), rd=d(rd))


def test_legacy_margin_known_value():
    rs = make_rs(off={'H': 80.0})
    p = predict('A', 'H', False, rs, LEGACY_PARAMS)
    assert p.margin == approx(2.896, abs=1e-3)
    assert p.p_home == approx(0.6038, abs=1e-3)


def test_neutral_site_removes_hfa():
    rs = make_rs()
    assert predict('A', 'H', False, rs, LEGACY_PARAMS).hfa == 1.7
    p = predict('A', 'H', True, rs, LEGACY_PARAMS)
    assert p.hfa == 0 and p.margin == approx(0.0)
    assert p.p_home == approx(0.5)


def test_rush_nudge_capped_at_one_point():
    rs = make_rs(ro={'H': 5.0})   # edge = 25*5 = 125 -> 62.5 pts uncapped
    p = predict('A', 'H', True, rs, LEGACY_PARAMS)
    assert p.nudge == 1.0
    rs = make_rs(rd={'H': 5.0})
    assert predict('A', 'H', True, rs, LEGACY_PARAMS).nudge == 1.0
    rs = make_rs(ro={'A': 5.0})
    assert predict('A', 'H', True, rs, LEGACY_PARAMS).nudge == -1.0


def test_rush_nudge_ignored_outside_three_point_window():
    rs = make_rs(off={'H': 800.0}, ro={'H': 5.0})   # big margin from ratings
    p = predict('A', 'H', False, rs, LEGACY_PARAMS)
    assert abs(p.margin) > 3 and p.nudge == 0.0


def test_margin_is_sum_of_components():
    rs = make_rs(off={'H': 30.0}, def_={'A': 10.0}, ro={'H': 0.01})
    p = predict('A', 'H', False, rs, LEGACY_PARAMS)
    assert p.margin == approx(p.matchup_points + p.hfa + p.nudge)


def test_each_offense_is_matched_against_the_opposing_defense():
    p = compute_margin(off_home=10.0, def_home=3.0, off_away=-4.0, def_away=40.0, rush_edge=0.0, neutral=True,
                       params=LEGACY_PARAMS)
    k = LEGACY_PARAMS.k
    assert p.home_matchup == approx(k*math.tanh((10.0 - 40.0)/k))
    assert p.away_matchup == approx(k*math.tanh((-4.0 - 3.0)/k))
