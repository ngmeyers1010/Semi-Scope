"""Sanity checks on SEC numbers (sanity.py): each rule on hand-made series."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sanity  # noqa: E402


def df(vals, start="2023-03-31"):
    ends = pd.date_range(start, periods=len(vals), freq="QE")
    return pd.DataFrame({"end": ends, "val": [float(v) if v is not None else np.nan for v in vals],
                         "filed": ends + pd.Timedelta(days=40)})


def test_units_error_is_dropped():
    drop, flags = sanity.check_series("revenue", df([100, 105, 110, 110_000, 115]))
    assert drop == [3] and flags[0]["hard"] and "1,000×" in flags[0]["text"] and "units error" in flags[0]["text"]
    assert flags[0]["text"].startswith("Q4 2023 revenue")


def test_small_unit_error_and_year_as_quarter():
    drop, flags = sanity.check_series("revenue", df([100, 105, 110, 0.11, 115]))
    assert drop == [3] and "about 1/950 of" in flags[0]["text"]
    drop, _ = sanity.check_series("cogs", df([50, 52, 51, 53, 450]))      # ~9x: a year tagged as a quarter
    assert drop == [4]


def test_normal_cycle_is_not_flagged():
    boom_bust = [100, 120, 150, 180, 140, 100, 80, 72, 75, 90, 130, 170]  # -60% over 4 quarters, then +130%
    assert sanity.check_series("revenue", df(boom_bust)) == ([], [])
    assert sanity.check_series("inventory", df([10, 30, 70, 75])) == ([], [])  # 7x over 2 quarters: allowed


def test_nonpositive_revenue():
    drop, flags = sanity.check_series("revenue", df([100, -5, 102, 0]))
    assert drop == [1, 3] and all(f["rule"] == "nonpositive" for f in flags)
    assert sanity.check_series("opinc", df([5, -3, -8, 2])) == ([], [])     # losses are normal


def test_repeat_is_soft():
    drop, flags = sanity.check_series("capex", df([7, 9, 9, 9, 9, 11]))
    assert drop == [] and len(flags) == 1 and not flags[0]["hard"] and "4+ quarters" in flags[0]["text"]
    assert sanity.check_series("capex", df([0, 0, 0, 0, 0])) == ([], [])   # zeros: "doesn't report it", not stale


def test_only_earlier_quarters_are_used():
    """The quarter before a units error must not be judged by it (no look-ahead)."""
    drop, _ = sanity.check_series("revenue", df([100, 101, 102, 103, 103_000]))
    assert drop == [4]
    drop, _ = sanity.check_series("revenue", df([100, 101, 102_000, 103, 104]))
    assert drop == [2]                                          # 103 is judged on 100/101 only (the bad one is dropped)


def test_margin_soft_flag():
    flags = sanity.check_margin(df([100, 100, 100]), df([40, 170, 45]))
    assert len(flags) == 1 and flags[0]["rule"] == "margin" and "-70%" in flags[0]["text"]


def test_clean_passes_good_stocks_through_untouched():
    good = {"revenue": df([100, 110, 120, 130]), "cogs": df([50, 55, 60, 65])}
    bad = {"revenue": df([100, 110, 120, 130_000]), "cogs": df([50, 55, 60, 65])}
    out, flags = sanity.clean({"GOOD": good, "BAD": bad, "NONE": None})
    assert out["GOOD"] is good and "GOOD" not in flags and out["NONE"] is None
    assert len(out["BAD"]["revenue"]) == 3 and out["BAD"]["cogs"] is bad["cogs"]
    assert len(bad["revenue"]) == 4                              # the original isn't modified
    assert flags["BAD"][0]["series"] == "revenue"


def test_demo_data_is_clean():
    import demo_data
    from config import BACKTEST_START, BENCHMARKS, UNIVERSE, WATCHLIST
    a, *_ = demo_data.generate(list(UNIVERSE) + list(WATCHLIST), list(BENCHMARKS), BACKTEST_START, return_market=True)
    out, flags = sanity.clean(a)
    assert flags == {} and all(out[t] is a[t] for t in a)
