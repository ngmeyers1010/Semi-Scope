"""Signal decay (decay.py): known answers on hand-made prices, no lookahead, and the read."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import decay  # noqa: E402
import slim  # noqa: E402
import weekly  # noqa: E402


def _px(days=900, drift=None):
    """Business-day prices for A..D. `drift`: daily growth per ticker (default all flat)."""
    idx = pd.bdate_range("2020-01-01", periods=days)
    drift = drift or {}
    return pd.DataFrame({t: 100 * (1 + drift.get(t, 0.0)) ** np.arange(days) for t in "ABCD"}, index=idx)


def _schedule(px, picks=("A",)):
    import backtest
    return [(d, list(picks)) for d in backtest.rebalance_dates(px.index, px.index[0])]


def test_known_answer_constant_drift():
    px = _px(drift={"A": 0.001})                  # A grows 0.1%/day, the rest are flat
    obs = decay.observations(px, _schedule(px), list("ABCD"), horizons=(1, 3))
    o = next(o for o in obs if o["months"] == 1)
    d, e = pd.Timestamp(o["date"]), decay._end(px.index, pd.Timestamp(o["date"]), 1)
    n = px.index.get_loc(e) - px.index.get_loc(d)
    a = 1.001 ** n - 1
    assert o["pick"] == pytest.approx(a) and o["universe"] == pytest.approx(a / 4)
    assert o["excess"] == pytest.approx(a * 3 / 4)
    rows = decay.summarize(obs, horizons=(1, 3))
    assert [r["months"] for r in rows] == [1, 3] and all(r["hit"] == 1.0 for r in rows)
    assert rows[1]["mean"] > rows[0]["mean"] and rows[0]["per_month"] == pytest.approx(rows[0]["mean"])


def test_unfinished_horizons_are_skipped():
    px = _px(days=300)
    obs = decay.observations(px, _schedule(px), list("ABCD"), horizons=(1, 12))
    last = px.index[-1]
    for o in obs:
        assert pd.Timestamp(o["date"]) + pd.DateOffset(months=o["months"]) <= last
    assert not [o for o in obs if o["months"] == 12]          # 300 days < 12 months after any start


def test_no_lookahead():
    """Changing prices AFTER a date's 1-month window can't change that date's 1-month result."""
    px = _px(drift={"A": 0.002, "B": -0.001})
    sched = _schedule(px)
    d0 = pd.Timestamp(sched[0][0])
    end1 = decay._end(px.index, d0, 1)
    before = next(o for o in decay.observations(px, sched, list("ABCD"), horizons=(1,)) if o["date"] == d0.strftime("%Y-%m-%d"))
    px2 = px.copy()
    px2.loc[px2.index > end1, "A"] *= 0.1                       # crash A later on
    after = next(o for o in decay.observations(px2, sched, list("ABCD"), horizons=(1,)) if o["date"] == d0.strftime("%Y-%m-%d"))
    assert before == after


def test_missing_prices_and_bad_dates_dont_crash():
    px = _px()
    px.loc[px.index[:40], "C"] = np.nan                       # C not listed yet
    sched = _schedule(px) + [(pd.Timestamp("1999-01-04"), ["A"]), (px.index[5], [])]
    obs = decay.observations(px, sched, list("ABCD") + ["ZZZ"], horizons=(1,))
    assert obs and all(np.isfinite(o["excess"]) for o in obs)


def _rows(means, t=2.0):
    return [{"months": m, "n": 20, "mean": v, "per_month": v / m, "hit": 0.6, "t": t} for m, v in means.items()]


def test_read_cases():
    assert decay.read(_rows({1: 0.004, 3: 0.012, 6: 0.02, 12: -0.06}))[1] == "fits"
    assert "reverses" in decay.read(_rows({1: 0.004, 3: 0.012, 6: 0.02, 12: -0.06}))[0]
    assert decay.read(_rows({1: 0.03, 3: 0.02, 6: 0.01}))[1] == "faster"
    assert decay.read(_rows({1: 0.003, 3: 0.01, 6: 0.03, 12: 0.05}))[1] == "slower"
    assert decay.read(_rows({1: 0.003, 3: 0.01, 6: 0.03, 12: 0.05}, t=0.5))[1] == "fits"   # weak evidence
    assert decay.read(_rows({1: -0.01, 3: -0.02}))[1] == "none"
    assert decay.read([])[1] == "none"


def test_weekly_question_only_when_pace_looks_wrong():
    base = {"research": {"decay": {"read": "Most of the edge shows up in the first month.", "suggest": "faster"}}}
    q = weekly._decay(base)
    assert q and "more often" in q["q"] and q["link"] == "index.html#tab=res&card=decay-card"
    assert weekly._decay({"research": {"decay": {"read": "x", "suggest": "fits"}}}) is None
    assert weekly._decay({}) is None and weekly._decay({"research": None}) is None


def test_demo_data_json_has_decay():
    d = slim.unpack(json.loads((ROOT / "docs" / "data.json").read_text()))
    k = (d.get("research") or {}).get("decay")
    if not k:
        pytest.skip("data.json predates decay: run python run.py --demo")
    assert [r["months"] for r in k["rows"]] == list(decay.HORIZONS)
    assert k["suggest"] in ("fits", "faster", "slower", "none") and k["read"]
    assert all(0 <= r["hit"] <= 1 and r["n"] >= decay.MIN_OBS for r in k["rows"])
