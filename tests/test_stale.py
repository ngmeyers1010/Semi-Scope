"""Stale prices: a missing last bar or two shouldn't drop a stock or repeat yesterday's move."""
import numpy as np
import pandas as pd

import data_health
import factors
import moves
import mystocks


def universe(n=200, k=6, seed=1):
    idx = pd.bdate_range("2025-01-01", periods=n)
    rng = np.random.default_rng(seed)
    return pd.DataFrame({f"T{i}": 100 * np.cumprod(1 + rng.normal(0.0005 * i, 0.02, n)) for i in range(k)}, index=idx)


def test_stale_days():
    s = pd.Series([1.0, 2.0, np.nan, np.nan])
    assert factors.stale_days(s) == 2 and factors.stale_days(pd.Series([1.0, 2.0])) == 0
    assert factors.stale_days(pd.Series([np.nan, np.nan])) == 2


def test_missing_last_bar_stays_ranked_with_flag():
    px = universe()
    px.iloc[-1, 0] = np.nan                                   # T0 missing today's bar
    ranked, _ = factors._score({}, px, px.index[-1], list(px.columns))
    assert "T0" in ranked.index and ranked.loc["T0", "stale_days"] == 1
    assert (ranked.drop("T0")["stale_days"] == 0).all()


def test_missing_more_than_limit_drops_it():
    px = universe()
    px.iloc[-(factors.STALE_MAX_DAYS + 1):, 0] = np.nan       # 4 days missing
    ranked, _ = factors._score({}, px, px.index[-1], list(px.columns))
    assert "T0" not in ranked.index


def test_fresh_data_unchanged():
    px = universe()
    ranked, _ = factors._score({}, px, px.index[-1], list(px.columns))
    assert (ranked["stale_days"] == 0).all()


def test_no_repeated_move_alert_when_stale():
    px = universe()
    px.iloc[-2, 1] = px.iloc[-3, 1] * 0.85                     # big drop yesterday...
    px.iloc[-1, 1] = np.nan                                    # ...and no price today
    m = moves.price_moves(px, ["T1"])
    assert m["T1"]["stale_days"] == 1
    assert moves.alerts_for(m, ["T1"], 2.5) == []
    fresh = universe()
    fresh.iloc[-1, 1] = fresh.iloc[-2, 1] * 0.85
    assert moves.alerts_for(moves.price_moves(fresh, ["T1"]), ["T1"], 2.5)   # fresh big drop still alerts


def test_unknown_vs_stale():
    px = universe()
    px.iloc[-2:, 2] = np.nan
    failures = {"ZZZZ": "price download failed"}
    assert mystocks.unknown(["T2", "ZZZZ"], failures) == ["ZZZZ"]
    assert mystocks.stale(["T2", "T3", "ZZZZ", "NOPE"], px, failures) == {"T2": 2}


def test_health_lists_stale():
    h = data_health.build({}, ["T0", "T1"], pd.DataFrame(), "2026-10-13", {}, stale_px={"T1": 2})
    assert h["summary"]["stale_price"] == ["T1"]
    row = next(r for r in h["rows"] if r["ticker"] == "T1")
    assert row["status"] == "warn" and "2 trading day" in row["flags"][0]
