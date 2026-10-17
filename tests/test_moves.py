"""Price-move alerts: z-moves, 52-week flags, 'biggest since'."""
import math

import numpy as np
import pandas as pd

import moves


def series(rets, start=100.0):
    idx = pd.bdate_range("2024-01-01", periods=len(rets) + 1)
    return pd.Series(start * np.cumprod(np.r_[1.0, 1 + np.asarray(rets)]), index=idx)


def calm(n=300, seed=1):
    return np.random.default_rng(seed).normal(0, 0.01, n)


def test_z_move_math_on_known_spike():
    r = np.r_[calm(), -0.08]
    p = series(r)
    m = moves.one(p)
    sigma = pd.Series(r[:-1][-252:]).std()        # past year, excluding today
    assert math.isclose(m["sigma_daily"], sigma, rel_tol=1e-9)
    assert math.isclose(m["r_1d"], -0.08, rel_tol=1e-9)
    assert math.isclose(m["z_1d"], -0.08 / sigma, rel_tol=1e-9)
    assert m["z_1d"] < -5                          # 8% on a ~1% stock is huge
    five = p.iloc[-1] / p.iloc[-6] - 1
    assert math.isclose(m["z_5d"], five / (sigma * math.sqrt(5)), rel_tol=1e-9)


def test_new_52w_high_flag_on_its_exact_day():
    r = np.r_[np.full(260, -0.001), np.full(3, 0.0)]
    r[-1] = 0.5                                     # jumps above everything
    m = moves.one(series(r))
    assert m["new_52w_high"] and not m["new_52w_low"]
    assert m["dist_52w_high"] == 0.0
    # the next (flat) day is not a NEW high any more
    m2 = moves.one(series(np.r_[r, 0.0]))
    assert not m2["new_52w_high"]


def test_biggest_since_picks_right_date():
    r = calm()
    r[100], r[200] = -0.06, -0.04
    p = series(np.r_[r, -0.05])
    m = moves.one(p)
    assert m["biggest_since"] == p.index[101].strftime("%Y-%m-%d")   # the -6% day, not the -4%
    p2 = series(np.r_[r, -0.09])
    assert moves.one(p2)["biggest_since"] is None
    assert "biggest drop on record" in moves.alert_text("X", moves.one(p2))


def test_no_alert_below_threshold_and_alert_above():
    quiet = moves.price_moves(pd.DataFrame({"A": series(np.r_[calm(), 0.001])}), ["A"])
    quiet["A"]["new_52w_high"] = quiet["A"]["new_52w_low"] = False
    assert moves.alerts_for(quiet, ["A"], 2.5) == []
    loud = moves.price_moves(pd.DataFrame({"A": series(np.r_[calm(), -0.07])}), ["A"])
    a = moves.alerts_for(loud, ["A"], 2.5)
    assert len(a) == 1 and a[0]["kind"] == "move" and a[0]["level"] == "warning"


def test_alert_text_keeps_date_dashes():
    r = calm()
    r[50] = -0.06
    m = moves.one(series(np.r_[r, -0.05]))
    txt = moves.alert_text("X", m)
    assert txt.startswith("X −5.0% today")
    assert m["biggest_since"] in txt and m["biggest_since"].count("-") == 2


def test_short_history_skipped():
    assert moves.one(series(np.full(10, 0.01))) is None
