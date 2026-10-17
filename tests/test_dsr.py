"""Deflated Sharpe Ratio (multiple-testing haircut)."""
import math
from statistics import NormalDist

import numpy as np
import pytest

import confidence as cf

N = NormalDist()


def rets(seed=0, n=2000, mu=0.0006, sd=0.012):
    return np.random.default_rng(seed).normal(mu, sd, n).tolist()


def test_psr_hand_calculation():
    # SR 0.1/period, 101 obs, normal returns: z = 0.1*sqrt(100)/sqrt(1 + 0.5*0.01)
    z = 0.1 * 10 / math.sqrt(1 + 2 / 4 * 0.01)
    assert cf.psr(0.1, 0.0, 101, 0.0, 3.0) == pytest.approx(N.cdf(z))


def test_expected_max_sharpe_hand_calculation():
    g = 0.5772156649
    want = (1 - g) * N.inv_cdf(1 - 1 / 10) + g * N.inv_cdf(1 - 1 / (10 * math.e))
    assert cf.expected_max_sharpe(10, 1.0) == pytest.approx(want, rel=1e-6)
    assert cf.expected_max_sharpe(1, 1.0) == 0.0
    assert cf.norm_ppf(0.975) == pytest.approx(1.959964, abs=1e-5)


def test_one_trial_reduces_to_psr():
    r = rets()
    d = cf.deflated_sharpe(r, [0.8])
    assert d["n_trials"] == 1 and d["sr0"] == 0
    assert d["dsr"] == pytest.approx(d["psr"])


def test_dsr_falls_as_trials_rise():
    r = rets()
    rng = np.random.default_rng(5)
    vals = []
    for n in (2, 5, 15, 50, 200):
        trials = (0.8 + rng.normal(0, 0.3, n)).tolist()
        vals.append(cf.deflated_sharpe(r, trials)["dsr"])
    # same spread of trial Sharpes, more trials -> higher luck bar -> lower DSR
    fixed = [cf.deflated_sharpe(r, [0.5, 1.1] * (n // 2))["dsr"] for n in (2, 10, 50, 200)]
    assert all(a > b for a, b in zip(fixed, fixed[1:]))
    assert vals[0] > vals[-1]


def test_degenerate_inputs_dont_crash():
    assert cf.deflated_sharpe([0.0] * 100, [0.5, 0.6]) is None
    assert cf.deflated_sharpe([0.01] * 5, [0.5]) is None
    d = cf.deflated_sharpe(rets(), [0.7, 0.7, 0.7])        # zero variance across trials
    assert d["sr0"] == 0 and d["dsr"] == pytest.approx(d["psr"])
    assert "versions" in d["explain"]
