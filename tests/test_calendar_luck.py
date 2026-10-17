"""Round 56: calendar helpers that don't trust where an index starts, and start-date luck."""
from pathlib import Path

import pandas as pd
import pytest

import backtest
import rebalance
import robustness


def test_first_trading_days_ignores_a_mid_month_start():
    idx = pd.bdate_range("2026-12-16", "2027-04-10")
    assert backtest.first_trading_days(idx)[:2] == [pd.Timestamp("2027-01-01"), pd.Timestamp("2027-02-01")]
    assert backtest.rebalance_dates(idx, idx[0]) == [pd.Timestamp("2027-03-01")]      # NOT Dec 16
    assert robustness.month_starts(idx, idx[0])[0] == pd.Timestamp("2027-01-01")


def test_first_week_start_and_holidays_still_count():
    idx = pd.bdate_range("2026-01-02", "2026-03-31")                    # Jan 1 holiday: starts Jan 2
    assert backtest.first_trading_days(idx)[0] == pd.Timestamp("2026-01-02")
    gap = idx[idx != pd.Timestamp("2026-03-02")]                         # a closed first business day
    assert pd.Timestamp("2026-03-03") in backtest.rebalance_dates(gap, gap[0])
    assert backtest.rebalance_dates(idx, idx[0], months=[2]) == [pd.Timestamp("2026-02-02")]


def test_paper_and_preview_agree_on_the_calendar():
    assert rebalance.next_date("2026-12-15") == pd.Timestamp("2027-03-01")


def _run(cal, off, cagr, base=False):
    return {"calendar": cal, "offset_months": off, "start": "2012-03-01", "cagr": cagr, "sharpe": cagr * 4, "baseline": base}


def test_luck_read_at_both_extremes_and_middle():
    runs = [_run("A", i, 0.15 + 0.01 * i) for i in range(10)]
    top = robustness.summarize(runs + [_run("M", 0, 0.30, True)])
    assert "near the TOP" in top["read"] and "expect closer to" in top["read"]
    low = robustness.summarize(runs + [_run("M", 0, 0.10, True)])
    assert "near the BOTTOM" in low["read"]
    mid = robustness.summarize(runs + [_run("M", 0, 0.195, True)])
    assert "mid-pack" in mid["read"] and mid["n"] == 11 and mid["cagr_min"] == pytest.approx(0.10 + 0.05)
    assert robustness.summarize(runs[:2]) is None                      # too few starts to say anything


@pytest.mark.slow
def test_start_luck_on_small_synthetic_data():
    import config
    import demo_data
    import factors
    tickers = list(config.UNIVERSE)[:10]
    s, px, _, close, _ = demo_data.generate(tickers, list(config.BENCHMARKS), "2020-03-01", return_market=True)
    factors.MARKET["close"] = close
    try:
        out = robustness.start_luck(s, px, tickers, start="2020-03-01")
    finally:
        factors.MARKET["close"] = None
    assert out["n"] == 12 and sum(r["baseline"] for r in out["runs"]) == 1
    assert out["cagr_min"] <= out["cagr_median"] <= out["cagr_max"]
    starts = {(r["calendar"], r["offset_months"]): r["start"] for r in out["runs"]}
    assert starts[("Mar/Jun/Sep/Dec", 0)] == "2020-03-02" and starts[("Mar/Jun/Sep/Dec", 3)] == "2020-06-01"


def test_fast_mode_reuses_previous_result():
    src = (Path(__file__).resolve().parents[1] / "run.py").read_text()
    assert "luck = prev_luck if reuse and prev_luck else robustness.start_luck(" in src
