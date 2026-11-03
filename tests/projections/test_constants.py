from projections.constants import MODEL_VERSION, PARAMS


def test_fixed_constants():
    assert PARAMS.reg == 0.8
    assert PARAMS.k == 800.0


def test_model_version_is_set():
    assert isinstance(MODEL_VERSION, str) and MODEL_VERSION


def test_refit_constants_are_near_the_fold_values():
    assert 0.008 <= PARAMS.slope <= 0.011
    assert 1.8 <= PARAMS.hfa <= 2.7
    assert 12.5 <= PARAMS.sig <= 13.5


def test_constants_not_refit_keep_their_values():
    assert (PARAMS.qb_k, PARAMS.qb_prior) == (150, -1.5)
    assert (PARAMS.rush_window, PARAMS.rush_pts, PARAMS.rush_cap, PARAMS.rushes) == (3.0, 0.5, 1.0, 25)
