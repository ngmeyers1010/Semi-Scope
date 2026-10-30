"""Price nets (bands.py): the yardstick, each method, the scoring, and the promise of no look-ahead."""
import json
import math

import numpy as np
import pandas as pd
import pytest

import bands


# ----------------------------------------------------------------------------- helpers
def iid_market(T=1700, N=10, seed=1, sigma=0.015):
    rng = np.random.default_rng(seed)
    r = rng.normal(0, sigma, (T, N))
    return pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=pd.bdate_range("2014-01-01", periods=T),
                        columns=[f"S{i}" for i in range(N)])


def clustered_market(T=1800, N=12, seed=2):
    """Fat tails (t5) and volatility waves: a calm/stormy market mood times a per-stock GARCH."""
    rng = np.random.default_rng(seed)
    state = np.zeros(T, int)
    for t in range(1, T):
        stay = 0.985 if state[t - 1] == 0 else 0.95
        state[t] = state[t - 1] if rng.random() < stay else 1 - state[t - 1]
    mood = np.where(state == 1, 2.2, 1.0)
    h = rng.uniform(0.012, 0.025, N) ** 2
    r = np.zeros((T, N))
    for t in range(T):
        z = rng.standard_t(5, N) / np.sqrt(5 / 3)
        r[t] = np.sqrt(h) * mood[t] * z
        h = np.maximum(0.00001 + 0.08 * (r[t] / mood[t]) ** 2 + 0.88 * h, 1e-6)
    return pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=pd.bdate_range("2014-01-01", periods=T),
                        columns=[f"S{i}" for i in range(N)])


# ----------------------------------------------------------------------------- the yardstick
def test_kappa_is_the_normal_quantile_for_one_day_and_grows_with_horizon_and_level():
    assert bands.kappa(1, 0.9) == pytest.approx(1.6449, abs=1e-3)
    assert bands.kappa(1, 0.5) == pytest.approx(0.6745, abs=1e-3)
    assert bands.kappa(1, 0.9) < bands.kappa(5, 0.9) < bands.kappa(21, 0.9)
    assert bands.kappa(5, 0.5) < bands.kappa(5, 0.9)
    # a swing "at any point" is bigger than where you end up: sqrt(5) * the one-day value is a floor
    assert bands.kappa(5, 0.9) > math.sqrt(5) * bands.kappa(1, 0.9) * 0.95


def test_parkinson_recovers_volatility_from_high_low_ranges():
    rng = np.random.default_rng(5)
    sigma, days, steps = 0.02, 400, 200
    walks = np.cumsum(rng.normal(0, sigma / math.sqrt(steps), (days, steps)), axis=1)
    hi, lo = 100 * np.exp(walks.max(axis=1)), 100 * np.exp(np.minimum(walks.min(axis=1), 0))
    # the day also starts at 100 (the walk's start), so include it in the high/low
    hi = np.maximum(hi, 100.0)
    assert bands.parkinson_sigma(hi, lo) == pytest.approx(sigma, rel=0.12)
    assert math.isnan(bands.parkinson_sigma([101, 102], [99, 100]))          # too little data
    r = rng.normal(0, 0.01, 300)
    assert math.isnan(bands.net_range(r)[(5, 0.9)])                          # no sigma given: unavailable
    assert bands.net_range(r, sigma=0.02)[(1, 0.9)] == pytest.approx(0.02 * bands.kappa(1, 0.9))


# ----------------------------------------------------------------------------- the methods
@pytest.mark.parametrize("name", bands.METHODS)
def test_each_method_is_finite_ordered_and_scales_with_the_returns(name):
    r = np.random.default_rng(3).normal(0, 0.015, 900)
    a = bands.FUNCS[name](r)
    assert all(np.isfinite(v) and v > 0 for v in a.values())
    for h in bands.HORIZONS:
        assert a[(h, 0.5)] < a[(h, 0.9)]
    for l in bands.LEVELS:
        assert a[(1, l)] < a[(5, l)] < a[(21, l)]
    b = bands.FUNCS[name](2 * r)                                              # twice as wild -> twice the net
    for k in a:
        assert b[k] == pytest.approx(2 * a[k], rel=1e-6)


def test_bell_curve_is_right_on_bell_curve_data_and_wrong_on_fat_tails():
    rng = np.random.default_rng(8)
    thin = rng.normal(0, 0.015, 4000)
    fat = rng.standard_t(3, 4000) * 0.015
    for r in (thin, fat):
        m = np.abs(r)                                                          # h = 1: swing is just |r|
        for l in (0.5, 0.9):
            cov = (m <= bands.net_normal(r)[(1, l)]).mean()
            if r is thin:
                assert cov == pytest.approx(l, abs=0.03)
    # fat tails: sigma is inflated by rare giant moves, so the bell curve is too wide in the middle
    assert (np.abs(fat) <= bands.net_normal(fat)[(1, 0.5)]).mean() > 0.62
    assert (np.abs(fat) <= bands.net_quantile(fat)[(1, 0.5)]).mean() == pytest.approx(0.5, abs=0.03)


def test_ewma_reacts_to_a_volatility_jump_faster_than_the_year_long_bell_curve():
    rng = np.random.default_rng(4)
    r = np.concatenate([rng.normal(0, 0.01, 700), rng.normal(0, 0.04, 20)])
    assert bands.net_ewma(r)[(5, 0.9)] > 1.5 * bands.net_normal(r)[(5, 0.9)]


def test_too_little_history_gives_nan_not_a_guess():
    out = bands.nets_at(np.random.default_rng(0).normal(0, 0.01, bands.MIN_HISTORY - 1))
    assert all(math.isnan(v) for m in out.values() for v in m.values())


# ----------------------------------------------------------------------------- scoring
def test_pinball_loss_hand_checked_and_minimised_at_the_true_quantile():
    assert bands.pinball(np.array([3.0]), np.array([2.0]), 0.9)[0] == pytest.approx(0.9)   # escaped: costly
    assert bands.pinball(np.array([1.0]), np.array([2.0]), 0.9)[0] == pytest.approx(0.1)   # roomy: cheap
    y = np.abs(np.random.default_rng(1).normal(0, 1, 200_000))
    q = np.quantile(y, 0.9)
    best = bands.pinball(y, q, 0.9).mean()
    assert best < bands.pinball(y, 0.8 * q, 0.9).mean() and best < bands.pinball(y, 1.2 * q, 0.9).mean()


def test_forward_max_swing_by_hand_and_gaps_make_it_unknown():
    px = pd.DataFrame({"A": [100.0, 110.0, 99.0, 99.0, 120.0]})
    m = bands.forward_max_swing(px, 2)[:, 0]
    assert m[0] == pytest.approx(max(abs(math.log(1.10)), abs(math.log(0.99))))   # 110 then 99 from 100
    assert m[1] == pytest.approx(max(abs(math.log(99 / 110)), abs(math.log(99 / 110))))
    assert np.isnan(m[3]) and np.isnan(m[4])                                       # future not known yet
    gap = pd.DataFrame({"A": [100.0, np.nan, 99.0, 99.0, 120.0, 100.0]})
    assert np.isnan(bands.forward_max_swing(gap, 2)[0, 0])                         # a hole in the window


def test_blend_weights_equal_when_unsure_better_method_wins_and_shrink_dials_it():
    few = np.abs(np.random.default_rng(1).normal(1, 0.1, (5, 4)))
    assert np.allclose(bands.blend_weights(few), 0.25)                             # too few dates: equal
    loss = np.tile([1.0, 1.0, 1.0, 2.0], (60, 1)) * np.random.default_rng(2).uniform(0.95, 1.05, (60, 4))
    w = bands.blend_weights(loss, shrink=1.0)
    assert w.sum() == pytest.approx(1) and w[3] == w.min() and w[:3].min() > 2 * w[3]
    assert np.allclose(bands.blend_weights(loss, shrink=0.0), 0.25)                # shrink 0 = equal weights
    half = bands.blend_weights(loss)
    assert w[3] < half[3] < 0.25                                                   # shrunk halfway
    assert np.allclose(bands.blend_weights(np.full((60, 4), np.nan)), 0.25)        # nothing usable: equal


def test_market_mood_calm_then_stormy_after_a_spike_and_it_only_looks_backwards():
    px = iid_market(T=700, N=8, seed=6, sigma=0.01)
    rng = np.random.default_rng(9)
    r = np.log(px).diff().fillna(0).to_numpy().copy()
    r[-21:] = rng.normal(0, 0.05, (21, 8))                                          # a stormy month at the end
    px2 = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=px.index, columns=px.columns)
    mood = bands.market_mood(px2)
    assert mood.iloc[-1] == "stormy"
    assert (mood.iloc[300:600] == "stormy").mean() < 0.4          # by definition roughly a quarter of ordinary days
    # changing only the last month cannot change an earlier day's label
    assert (bands.market_mood(px).iloc[:600] == mood.iloc[:600]).all()


# ----------------------------------------------------------------------------- the study
def test_study_is_calibrated_on_bell_curve_data():
    ev = bands.evaluate(iid_market(), step=10, max_dates=70)
    rows = {r["m"]: r for r in ev["table"][(5, 0.9)]}
    for name in bands.METHODS + ("equal", "perf", "regime"):
        assert rows[name]["cov"] == pytest.approx(0.9, abs=0.045), name
        assert rows[name]["n"] > 600


def test_on_messy_data_blending_beats_the_typical_single_method_and_bell_curve_is_too_wide():
    ev = bands.evaluate(clustered_market(), step=10, max_dates=90)
    rows = {r["m"]: r for r in ev["table"][(21, 0.9)]}
    singles = [rows[m]["loss"] for m in bands.METHODS]
    assert rows["perf"]["loss"] < np.mean(singles)                  # a blend should beat the typical single method
    assert rows["equal"]["loss"] < np.mean(singles)
    mid = {r["m"]: r for r in ev["table"][(5, 0.5)]}
    assert mid["normal"]["cov"] > 0.58                                # bell curve too wide in the middle on fat tails
    assert abs(mid["quantile"]["cov"] - 0.5) < abs(mid["normal"]["cov"] - 0.5)


def test_nothing_in_the_forecasts_or_the_blend_can_see_the_future():
    px = clustered_market(T=1500, N=6, seed=4)
    a = bands.evaluate(px, step=10, max_dates=None)
    cut_pos = int(a["_series"][(5, 0.9)]["pos"][40])                 # the 41st evaluation date
    px2 = px.copy()
    rng = np.random.default_rng(0)
    px2.iloc[cut_pos + 1:] = px2.iloc[cut_pos + 1:].values * np.exp(rng.normal(0, 0.5, px2.iloc[cut_pos + 1:].shape))
    b = bands.evaluate(px2, step=10, max_dates=None)
    for key in a["_series"]:
        sa, sb = a["_series"][key], b["_series"][key]
        for name in ("equal", "perf", "regime"):
            assert np.allclose(sa[name][:41], sb[name][:41], equal_nan=True), (key, name)
        assert np.allclose(sa["stack"][:, :41], sb["stack"][:, :41], equal_nan=True), key


# ----------------------------------------------------------------------------- the report
def test_build_report_shape_size_prices_and_the_fast_path():
    px = clustered_market(T=1200, N=8, seed=7)
    close = px.iloc[-1]
    tickers = list(px.columns[:5])
    out = bands.build(px, close, tickers)
    assert out["available"] and out["horizons"] == [1, 5, 21] and out["levels"] == [0.5, 0.9]
    assert set(out["table"]) == {f"{h}|{l}" for h in bands.HORIZONS for l in bands.LEVELS}
    assert {r["m"] for r in out["table"]["5|0.9"]} == set(bands.METHODS) | {"equal", "perf", "regime"}
    assert set(out["current"]) == set(tickers)
    c = out["current"][tickers[0]]["5|0.9"]
    assert c["low"] < close[tickers[0]] < c["high"] and c["lo_pct"] <= c["pct"] <= c["hi_pct"]
    assert out["current"][tickers[0]]["1|0.5"]["pct"] < out["current"][tickers[0]]["21|0.9"]["pct"]
    assert len(json.dumps(out)) < 16_000                              # small enough to ship in data.json
    json.loads(json.dumps(out))                                       # plain JSON, no numpy types
    assert out["read"].startswith("For a 5-day, 90% net")
    # --fast: reuse the comparison, recompute only today's nets
    fast = bands.build(px, close, tickers, prev=out, fast=True)
    assert fast["table"] == out["table"] and fast["weights"] == out["weights"] and fast["study_asof"] == out["study_asof"]
    assert fast["current"] == out["current"]                          # same prices, same nets


def test_build_says_so_when_there_are_not_enough_prices():
    out = bands.build(iid_market(T=200, N=3), None, ["S0"])
    assert out["available"] is False and "prices" in out["reason"]
