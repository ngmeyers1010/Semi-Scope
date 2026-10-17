"""Next-rebalance preview: dates, drift, sell/buy/keep, turnover and cost."""
import pandas as pd
import pytest

import rebalance as rb

ENTRY = {"date": "2026-09-01", "picks": ["A", "B", "C", "D", "E"],
         "entry_prices": {t: 100.0 for t in "ABCDE"}}


def test_no_paper_portfolio_yet():
    assert rb.preview(None, {}, ["A"], "2026-10-13") is None
    assert rb.preview({"picks": []}, {}, ["A"], "2026-10-13") is None


def test_next_date_rule_including_year_end():
    assert rb.next_date("2026-10-13") == pd.Timestamp("2026-12-01")
    assert rb.next_date("2026-12-01") == pd.Timestamp("2027-03-01")      # rebalance day itself: next one
    assert rb.next_date("2026-12-15") == pd.Timestamp("2027-03-01")      # across the year end
    assert rb.next_date("2027-05-20") == pd.Timestamp("2027-06-01")
    assert rb.next_date("2025-11-20") == pd.Timestamp("2025-12-01")


def test_unchanged_picks_no_drift():
    p = rb.preview(ENTRY, {t: 100.0 for t in "ABCDE"}, list("ABCDEFG"), "2026-10-13")
    assert p["sell"] == [] and p["buy"] == [] and p["keep"] == list("ABCDE")
    assert p["replaced"] == 0 and p["cost"] == 0
    assert "no changes" in p["text"] and p["days"] == 49


def test_drift_sums_to_one_and_missing_price_is_flat():
    prices = {"A": 200.0, "B": 100.0, "C": 50.0, "D": 100.0}          # E has no price today
    w = rb.drift(ENTRY, prices)
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["A"] == pytest.approx(2 / 5.5) and w["E"] == pytest.approx(1 / 5.5)
    p = rb.preview(ENTRY, prices, list("ABCDE"), "2026-10-13")
    assert p["sell"] == [] and 0 < p["replaced"] < 0.2 and "trimmed back to equal weights" in p["text"]


def test_some_and_full_turnover():
    prices = {t: 100.0 for t in "ABCDE"}
    p = rb.preview(ENTRY, prices, list("ABCFG"), "2026-10-13")
    assert p["sell"] == ["D", "E"] and p["buy"] == ["F", "G"] and p["replaced"] == pytest.approx(0.4)
    assert p["cost"] == pytest.approx(0.8 * 10 / 1e4)
    assert "sell D, E; buy F, G; 2 of 5 change (40% of the portfolio" in p["text"]
    full = rb.preview(ENTRY, prices, list("VWXYZ"), "2026-10-13")
    assert full["replaced"] == pytest.approx(1.0) and len(full["sell"]) == 5
