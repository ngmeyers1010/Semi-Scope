"""Up/down capture (capture.py): known answers on hand-made curves."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import capture  # noqa: E402
import digest  # noqa: E402


def _curve(monthly_rets, start="2020-01-31"):
    """An equity curve with exactly these month-over-month returns (month-end points)."""
    idx = pd.date_range(start, periods=len(monthly_rets) + 1, freq="ME")
    return pd.Series(np.cumprod([1.0] + [1 + r for r in monthly_rets]), index=idx)


B = [0.05, -0.03, 0.02, -0.04, 0.06, 0.0, -0.02, 0.03]


def test_twice_the_benchmark_is_200_200():
    c = capture.capture(_curve([2 * r for r in B]), _curve(B))
    assert c["up"] == pytest.approx(2.0) and c["down"] == pytest.approx(2.0)
    assert c["up_months"] == 4 and c["down_months"] == 3 and c["months"] == 8   # the 0.0 month counts in neither
    assert c["beat_up"] == 1.0 and c["beat_down"] == 0.0


def test_flat_strategy_is_0_0():
    c = capture.capture(_curve([0.0] * len(B)), _curve(B))
    assert c["up"] == pytest.approx(0.0) and c["down"] == pytest.approx(0.0)
    assert c["beat_up"] == 0.0 and c["beat_down"] == 1.0


def test_flat_benchmark_months_are_excluded():
    s = [0.10, 0.0, 0.0, 0.0, 0.0, 0.0, -0.05]
    b = [0.05, 0.0, 0.0, 0.0, 0.0, 0.0, -0.05]                 # big strategy moves in flat months: ignored
    s[2], s[3] = 0.5, -0.5
    c = capture.capture(_curve(s), _curve(b))
    assert c["up"] == pytest.approx(2.0) and c["down"] == pytest.approx(1.0)


def test_daily_curves_resample_to_month_end():
    idx = pd.bdate_range("2021-01-01", "2021-12-31")
    bench = pd.Series(np.linspace(100, 130, len(idx)), index=idx)
    strat = bench / bench.iloc[0] * 1.0
    c = capture.capture(strat, bench)
    assert c["up"] == pytest.approx(1.0) and c["down"] is None   # no down months


def test_too_short_and_missing_benchmark():
    assert capture.capture(_curve(B[:4]), _curve(B[:4])) is None
    curves = {"strategy": _curve(B)}
    assert capture.build(curves, None) is None
    out = capture.build(curves, pd.DataFrame({"SPY": _curve(B)}))
    assert set(out["backtest"]) == {"SPY"} and out["paper"] is None and "at least 6" in out["paper_note"]
    assert capture.build({}, pd.DataFrame({"SPY": _curve(B)})) is None


def test_paper_used_once_it_has_six_months():
    bench = pd.DataFrame({"SOXX": _curve(B)})
    out = capture.build({"strategy": _curve(B)}, bench, paper_curve=_curve([1.5 * r for r in B]))
    assert out["paper"]["SOXX"]["up"] == pytest.approx(1.5) and out["paper_note"] is None


@pytest.mark.parametrize("up,down,word", [(1.2, 0.8, "more of the gains"), (1.2, 1.3, "leveraged"),
                                          (0.9, 0.7, "falling less"), (0.8, 1.1, "worst combination"),
                                          (1.3, 1.1, "more on the way up"), (0.7, 0.9, "lags on the way up")])
def test_reads(up, down, word):
    assert word in capture.read("SOXX", {"up": up, "down": down})


def test_digest_line():
    data = {"rankings": [], "capture": {"backtest": {"SOXX": {"read": "Catches 109% of SOXX's up months..."}}, "paper": None}}
    sec = next(s for s in digest.sections(data) if s["title"].startswith("Up/down capture"))
    assert sec["title"] == "Up/down capture (backtest)" and sec["items"][0].startswith("Catches 109%")
