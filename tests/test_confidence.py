"""'Is the edge real?' statistics."""
import math

import numpy as np
import pytest

import confidence as cf


def test_t_stat_matches_hand_calculation():
    x = [0.02, -0.01, 0.03, 0.01, 0.00, 0.04]
    mean = sum(x) / 6
    sd = math.sqrt(sum((v - mean) ** 2 for v in x) / 5)
    r = cf.t_test(x)
    assert r["mean"] == pytest.approx(mean)
    assert r["sd"] == pytest.approx(sd)
    assert r["t"] == pytest.approx(mean / (sd / math.sqrt(6)))
    assert 0 < r["p"] < 0.5                          # positive mean -> one-sided p below 0.5


def test_bootstrap_deterministic_and_ci_contains_mean():
    x = np.random.default_rng(1).normal(0.01, 0.05, 40)
    a, b = cf.block_bootstrap(x), cf.block_bootstrap(x)
    assert np.array_equal(a, b)
    r = cf.analyze(x)
    lo, hi = r["ci90_q"]
    assert lo <= r["mean"] <= hi
    assert r["ci90_annual"][0] < r["ci90_annual"][1]
    assert 0 <= r["prob_positive"] <= 1
    assert cf.analyze(x) == r                        # whole result reproducible


def test_quarters_needed():
    # mean 1%, sd 5%: t = 0.01 / (0.05/sqrt(n)) = 2  ->  n = (2*5)^2 = 100
    assert cf.quarters_needed(0.01, 0.05) == 100
    assert cf.quarters_needed(-0.01, 0.05) is None
    assert cf.quarters_needed(0.0, 0.05) is None
    x = [0.01, 0.06, -0.04, 0.03, -0.01, 0.02]
    r = cf.analyze(x)
    n = r["quarters_needed"]
    assert r["mean"] / (r["sd"] / math.sqrt(n)) >= 2 > r["mean"] / (r["sd"] / math.sqrt(n - 1))
    assert r["more_quarters"] == max(0, n - 6)


def test_all_zero_and_tiny_inputs_dont_crash():
    r = cf.analyze([0.0] * 12)
    assert r["t"] is None and r["verdict"] == "Too early to tell"
    assert cf.analyze([])["n"] == 0
    assert cf.analyze([0.05])["t"] is None
    assert cf.build([], [])["paper"] is None


def test_build_uses_return_minus_spy():
    qs = [{"return": 0.05, "spy": 0.02}, {"return": 0.01, "spy": 0.03}, {"return": 0.04, "spy": float("nan")}]
    r = cf.build(qs)["backtest"]
    assert r["n"] == 2 and r["mean"] == pytest.approx(0.005)
