"""Hand-entered foreign fundamentals (foreign.py): shape, no look-ahead, bad lines."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import foreign  # noqa: E402
from factors import fundamental_factors  # noqa: E402

HEADER = ("ticker,quarter_end,reported,revenue,cost_of_sales,inventory,operating_income,"
          "rd,op_cash_flow,capex,units,source\n")
# TSMC, NT$ billions, from its quarterly management reports
TSM = """\
TSM,2024-12-31,2025-01-16,868.46,356.08,287.86,425.71,57.23,620.21,361.95,TWD bn,4Q25 report
TSM,2025-03-31,2025-04-17,839.25,345.85,293.39,407.08,56.55,625.57,330.83,TWD bn,1Q26 report
TSM,2025-06-30,2025-07-17,933.79,386.42,304.19,463.42,61.28,497.07,297.22,TWD bn,2Q26 report
TSM,2025-09-30,2025-10-16,989.92,401.38,288.69,500.69,63.74,426.83,287.45,TWD bn,3Q26 report
TSM,2025-12-31,2026-01-15,1046.09,394.10,288.11,564.90,64.86,725.51,356.91,TWD bn,4Q25 report
TSM,2026-03-31,2026-04-16,1134.10,382.80,311.45,658.97,67.76,698.97,350.76,TWD bn,1Q26 report
TSM,2026-06-30,2026-07-16,1270.38,410.07,385.53,766.60,73.14,783.36,496.00,TWD bn,2Q26 report
TSM,2026-09-30,2026-10-15,1494.24,501.86,427.75,876.45,88.98,919.77,443.21,TWD bn,3Q26 report
"""


def write(tmp_path, body):
    p = tmp_path / "foreign.csv"
    p.write_text(HEADER + body)
    return p


def test_shape_matches_build_series(tmp_path):
    s, problems = foreign.load(write(tmp_path, TSM))
    assert problems == []
    assert set(s["TSM"]) == {"revenue", "cogs", "inventory", "opinc", "rd", "cfo", "capex"}
    rev = s["TSM"]["revenue"]
    assert list(rev.columns) == ["end", "val", "filed"] and len(rev) == 8
    assert rev["end"].is_monotonic_increasing


def test_factors_match_the_report(tmp_path):
    s, _ = foreign.load(write(tmp_path, TSM))
    f = fundamental_factors(s["TSM"], pd.Timestamp("2026-10-20"))
    assert f["latest_quarter"] == "2026-09-30"
    assert f["rev_growth"] == pytest.approx(1494.24 / 989.92 - 1)       # 50.9% in the 3Q26 report
    assert f["gross_margin"] == pytest.approx(0.664, abs=0.001)          # 66.4% in the 3Q26 report
    assert np.isfinite(f["fcf_margin"]) and np.isfinite(f["inv_days_change"])
    assert np.isnan(f["sales_yield"])                                     # no share counts -> blank


def test_results_are_invisible_until_the_day_after_release(tmp_path):
    s, _ = foreign.load(write(tmp_path, TSM))
    on_the_day = fundamental_factors(s["TSM"], pd.Timestamp("2026-10-15"))
    next_day = fundamental_factors(s["TSM"], pd.Timestamp("2026-10-16"))
    assert on_the_day["latest_quarter"] == "2026-06-30"
    assert next_day["latest_quarter"] == "2026-09-30"


def test_needs_six_quarters(tmp_path):
    s, _ = foreign.load(write(tmp_path, TSM))
    five = fundamental_factors(s["TSM"], pd.Timestamp("2026-02-01"))     # 4Q24..4Q25 known
    six = fundamental_factors(s["TSM"], pd.Timestamp("2026-04-20"))      # + 1Q26
    assert np.isnan(five["rev_growth"])
    assert six["rev_growth"] == pytest.approx(1134.10 / 839.25 - 1)


def test_statement_style_numbers(tmp_path):
    body = 'ASML,2026-09-27,2026-10-14,"11,662.0",(4962.2),,,,"(2,185.6)",(413.3),,\n'
    s, problems = foreign.load(write(tmp_path, body))
    a = s["ASML"]
    assert problems == []
    assert a["revenue"]["val"][0] == 11662.0
    assert a["cogs"]["val"][0] == 4962.2 and a["capex"]["val"][0] == 413.3   # costs stored positive
    assert a["cfo"]["val"][0] == -2185.6                                      # cash flow keeps its sign
    assert a["inventory"].empty


def test_bad_lines_are_reported_not_fatal(tmp_path):
    body = TSM + (
        "TSM,2026-09-30,2026-10-15,1,1,1,1,1,1,1,,typed twice\n"
        "ASML,2026-13-01,2026-10-14,5,1,,,,,,,bad date\n"
        "ASML,2026-09-27,2026-09-01,5,1,,,,,,,reported before quarter end\n"
        "ASML,2026-06-28,2026-07-15,,1,,,,,,,no revenue\n"
        "# a note to self\n"
        "ASML,2026-03-29,2026-04-15,8766.9,abc,,,,,,,junk cost\n")
    s, problems = foreign.load(write(tmp_path, body))
    assert len(problems) == 5, problems
    assert s["TSM"]["revenue"]["val"].iloc[-1] == 1494.24                   # first copy kept
    assert list(s["ASML"]["revenue"]["val"]) == [8766.9] and s["ASML"]["cogs"].empty


def test_missing_quarter_is_flagged(tmp_path):
    lines = TSM.splitlines(True)
    _, problems = foreign.load(write(tmp_path, "".join(lines[:3] + lines[4:])))
    assert len(problems) == 1 and "may be missing" in problems[0]


def test_bad_header_and_missing_file(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("symbol,date,revenue\nTSM,2026-09-30,1\n")
    s, problems = foreign.load(p)
    assert s == {} and "Header is missing" in problems[0]
    assert foreign.load(tmp_path / "nope.csv") == ({}, [])


def test_the_real_file_loads_clean():
    """Catches typos in state/foreign_fundamentals.csv itself."""
    if not foreign.PATH.exists():
        pytest.skip("no state/foreign_fundamentals.csv yet")
    s, problems = foreign.load()
    assert problems == []
    for t, series in s.items():
        assert len(series["revenue"]) >= 6, f"{t} needs at least 6 quarters to be scored"
