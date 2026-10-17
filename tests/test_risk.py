"""Risk panel math on hand-made price series."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import risk  # noqa: E402

IDX = pd.bdate_range("2019-01-01", periods=800)


def prices(rets):
    return (1 + pd.DataFrame(rets, index=IDX)).cumprod() * 100


def test_identical_series_are_one_bet():
    r = np.random.default_rng(0).normal(0, 0.02, len(IDX))
    px = prices({"A": r, "B": r, "C": r})
    assert risk.corr_matrix(px, ["A", "B"]).loc["A", "B"] == pytest.approx(1.0)
    rr = px.pct_change().dropna()
    assert risk.effective_bets(rr, pd.Series({"A": 1, "B": 1, "C": 1})) == pytest.approx(1.0, abs=1e-6)


def test_independent_series_are_n_bets():
    rng = np.random.default_rng(1)
    px = prices({t: rng.normal(0, 0.02, len(IDX)) for t in "ABCDE"})
    rr = px.pct_change().dropna()
    assert risk.effective_bets(rr, pd.Series(1.0, index=list("ABCDE"))) == pytest.approx(5, rel=0.1)


def test_var_matches_hand_percentile():
    r = pd.Series(np.linspace(-0.10, 0.09, 20))        # 20 returns, evenly spaced
    assert risk.var_95(r) == pytest.approx(-np.percentile(r, 5))
    assert risk.var_95(r) > 0


def test_beta_of_spy_to_itself_is_one():
    r = pd.Series(np.random.default_rng(2).normal(0, 0.01, 300))
    assert risk.beta(r, r) == pytest.approx(1.0)
    assert risk.beta(2 * r, r) == pytest.approx(2.0)


def test_stress_windows_outside_history_are_skipped():
    px = prices({"A": np.zeros(len(IDX))})                 # history starts 2019
    out = risk.stress_tests(px, ["A"], pd.DataFrame(index=IDX))
    names = [o["name"] for o in out]
    assert "2018 Q4 selloff" not in names and "2020 COVID crash" in names
    assert out[0]["picks"] == pytest.approx(0.0)


def test_portfolio_risk_runs_end_to_end():
    rng = np.random.default_rng(3)
    px = prices({t: rng.normal(0, 0.02, len(IDX)) for t in "ABC"})
    bench = prices({"SPY": rng.normal(0, 0.01, len(IDX))})
    out = risk.portfolio_risk(px, {"A": 1, "B": 1, "C": 1, "ZZZ": 1}, bench)
    assert out["n"] == 3 and out["var95_dollars"] == pytest.approx(out["var95"] * 1000)
    assert len(out["corr"]["matrix"]) == 3 and out["worst_month"] < 0
