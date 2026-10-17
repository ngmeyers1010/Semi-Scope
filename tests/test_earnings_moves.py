"""Earnings reactions: reaction day, no look-ahead, ratio math, heads-up note."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import earnings_moves as em
import orders
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)


def prices(rets, start="2024-01-01"):
    idx = pd.bdate_range(start, periods=len(rets) + 1)
    return pd.Series(100 * np.cumprod(np.r_[1.0, 1 + np.asarray(rets)]), index=idx)


def test_reaction_day_is_first_trading_day_after_filing():
    idx = pd.bdate_range("2025-01-01", periods=20)
    assert em.reaction_day(idx, "2025-01-03") == pd.Timestamp("2025-01-06")   # Fri filing -> Mon
    assert em.reaction_day(idx, "2025-01-04") == pd.Timestamp("2025-01-06")   # Sat filing -> Mon
    assert em.reaction_day(idx, "2025-01-07") == pd.Timestamp("2025-01-08")   # never the filing day itself
    assert em.reaction_day(idx, idx[-1]) is None


def test_ratio_math_on_known_jumps():
    r = np.full(400, 0.0)
    r[::2], r[1::2] = 0.01, -0.01                      # every normal day moves exactly 1%
    p = prices(r)
    filed = [p.index[100], p.index[200], p.index[300]]
    for f, jump in zip(filed, (0.05, -0.05, 0.05)):
        i = p.index.get_loc(f) + 1                     # the reaction day
        r[i - 1] = jump                                # r[k] is the return INTO day k+1
    p = prices(r)
    m = em.one(p, filed, p.index[-1])
    assert m["n"] == 3
    assert [e["day"] for e in m["events"]] == [p.index[i + 1].strftime("%Y-%m-%d") for i in (100, 200, 300)]
    assert m["avg_abs"] == pytest.approx(0.05)
    assert m["normal_abs"] == pytest.approx(0.01)
    assert m["ratio"] == pytest.approx(5.0)
    assert m["pct_up"] == pytest.approx(2 / 3)
    assert "up 2 of 3 times" in em.summary(m)


def test_no_look_ahead():
    p = prices(np.random.default_rng(3).normal(0, 0.02, 400))
    filed = [p.index[150], p.index[300], p.index[-1]]   # the last one has no reaction day yet
    m = em.one(p, filed, p.index[-1])
    assert m["n"] == 2
    asof = p.index[300]                                  # filed that day, reaction is tomorrow
    m2 = em.one(p, filed, asof)
    assert m2["n"] == 1
    # results as of a date ignore prices after it
    p_future = p.copy(); p_future.iloc[302:] *= 3
    assert em.one(p_future, filed, asof) == m2


def test_earnings_note():
    assert orders.earnings_note(None, 0.05) == ""
    assert orders.earnings_note(8, 0.05) == ""
    assert orders.earnings_note(-1, 0.05) == ""
    assert orders.earnings_note(0, None) == "reports today"
    assert orders.earnings_note(1, 0.061) == "reports in ~1 day; typical earnings move ±6.1%"
    assert orders.earnings_note(3, 0.05) == "reports in ~3 days; typical earnings move ±5.0%"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_earnings_note_javascript_matches_python():
    html = page_source()
    fn = re.search(r"function earningsNote\(.*?\n\}", html, re.S).group(0)
    cases = [[None, 0.05], [8, 0.05], [-1, 0.05], [0, None], [1, 0.061], [3, 0.05], [7, 0.1234]]
    js = fn + "\nconsole.log(JSON.stringify(%s.map(c=>earningsNote(c[0],c[1],7))));" % json.dumps(cases)
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out == [orders.earnings_note(d, m) for d, m in cases]
