"""'Is the edge steady?': rolling 1-year excess, tracking error, information ratio."""
import math

import numpy as np
import pandas as pd
import pytest

import steady

IDX = pd.bdate_range("2018-01-01", periods=1000)


def curve(daily):
    return pd.Series(np.cumprod(1 + np.asarray(daily, dtype=float)), index=IDX[:len(daily)])


def test_identical_to_spy_has_no_ir_and_zero_excess():
    rng = np.random.default_rng(1)
    r = rng.normal(0.0004, 0.01, 1000)
    s = steady.analyze(curve(r), curve(r))
    assert s["available"] and s["info_ratio"] is None             # no divide-by-zero
    assert s["tracking_error"] == pytest.approx(0, abs=1e-12)
    assert s["excess_ann"] == pytest.approx(0, abs=1e-12)
    assert s["pct_windows_beat"] == 0.0 and s["median_1y"] == pytest.approx(0, abs=1e-12)


def test_constant_excess():
    rng = np.random.default_rng(2)
    b = rng.normal(0.0004, 0.01, 1000)
    exact = steady.analyze(curve(b + 0.0003), curve(b))
    assert exact["info_ratio"] is None or math.isfinite(exact["info_ratio"])   # TE ~ 0: handled
    noisy = steady.analyze(curve(b + 0.0003 + rng.normal(0, 1e-5, 1000)), curve(b))
    assert math.isfinite(noisy["info_ratio"]) and noisy["info_ratio"] > 10       # large and finite
    assert noisy["pct_windows_beat"] == 1.0
    assert "never trailed SPY" in noisy["read"]


def test_short_history_is_not_available():
    r = np.full(200, 0.001)
    s = steady.analyze(curve(r), curve(r * 0.5))
    assert not s["available"] and "200 days" in s["reason"]
    assert steady.analyze(None, curve(r))["available"] is False
    assert steady.read(s).startswith("Not enough history yet")


def test_worst_window_dates():
    # strategy = SPY except for a 252-day slump of -0.2%/day starting at day 400
    b = np.full(1000, 0.0003)
    s_r = b.copy()
    s_r[400:652] -= 0.002
    s = steady.analyze(curve(s_r), curve(b))
    w = s["worst"]
    # the window that contains exactly the slump: starts the day before it, ends on its last day
    assert w["start"] == IDX[399].strftime("%Y-%m-%d") and w["end"] == IDX[651].strftime("%Y-%m-%d")
    assert w["excess"] < -0.3
    assert "Expect at least one year like that." in s["read"]
    assert s["rolling"][-1][0] == IDX[999].strftime("%Y-%m-%d")         # last day always kept


def test_build_uses_spy_and_paper_only_when_long_enough():
    b = pd.DataFrame({"SPY": curve(np.full(1000, 0.0003))})
    strat = curve(np.full(1000, 0.0005))
    out = steady.build({"strategy": strat}, b, paper_curve=strat.iloc[:40])
    assert out["backtest"]["available"] and out["paper"] is None
    out = steady.build({"strategy": strat}, b, paper_curve=strat.iloc[:100])
    assert out["paper"] is not None and not out["paper"]["available"]      # 100 days < 1 year
    assert steady.build({}, None)["backtest"]["available"] is False
