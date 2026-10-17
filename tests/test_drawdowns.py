"""Drawdown episodes (drawdowns.py): known answers on hand-made curves."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import backtest  # noqa: E402
import digest  # noqa: E402
import drawdowns as dd  # noqa: E402
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)


def curve(values, start="2020-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def test_one_dip_and_full_recovery():
    c = curve([100, 110, 99, 88, 95, 110, 120])
    (e,) = dd.episodes(c)
    assert (e["peak"], e["trough"], e["recovery"]) == ("2020-01-02", "2020-01-04", "2020-01-06")
    assert e["depth"] == pytest.approx(88 / 110 - 1)
    assert (e["days_down"], e["days_up"], e["days_total"], e["recovered"]) == (2, 2, 4, True)


def test_still_underwater_at_the_end():
    (e,) = dd.episodes(curve([100, 120, 90, 80, 100]))
    assert e["recovery"] is None and e["days_up"] is None and not e["recovered"]
    assert e["days_total"] == 3 and e["depth"] == pytest.approx(80 / 120 - 1)
    s = dd.summary(curve([100, 120, 90, 80, 100]))
    assert s["now"] == pytest.approx(100 / 120 - 1)
    assert "still underwater" in dd.read(s, None)


def test_two_separate_episodes_and_small_wiggles_ignored():
    c = curve([100, 90, 101, 100.5, 101.2, 130, 100, 131])        # −10%, then a −0.7% wiggle, then −23%
    eps = dd.episodes(c)
    assert [round(e["depth"], 3) for e in eps] == [-0.1, round(100 / 130 - 1, 3)]
    s = dd.summary(c)
    assert s["top"][0]["depth"] == pytest.approx(100 / 130 - 1) and s["n"] == 2
    assert dd.episodes(c, min_depth=0.0)[1]["depth"] == pytest.approx(100.5 / 101 - 1)


def test_flat_and_rising_curves_have_none():
    assert dd.episodes(curve([100] * 10)) == [] and dd.episodes(curve(range(1, 20))) == []
    s = dd.summary(curve([100] * 10))
    assert s["top"] == [] and s["max_depth"] == 0 and s["share_underwater"] == 0
    assert dd.read(s, None) == "No drawdowns deeper than 2%."
    assert dd.summary(curve([100])) is None and dd.episodes(pd.Series(dtype=float)) == []


def test_depth_matches_backtest_max_drawdown():
    rng = np.random.default_rng(3)
    c = pd.Series(np.cumprod(1 + rng.normal(0.0005, 0.02, 1500)), index=pd.bdate_range("2015-01-01", periods=1500))
    s = dd.summary(c)
    assert s["max_depth"] == pytest.approx(backtest.stats(c)["max_drawdown"])
    assert s["top"][0]["depth"] == pytest.approx(s["max_depth"])
    days = [e["days_total"] for e in dd.episodes(c)]
    assert s["longest"]["days_total"] == max(days)


def test_build_chart_and_benchmark_overlap():
    idx = pd.bdate_range("2020-01-01", periods=400)
    strat = pd.Series(np.r_[np.linspace(1, 1.5, 100), np.linspace(1.5, 1.0, 50), np.linspace(1.0, 2.0, 250)], index=idx)
    soxx = pd.Series(np.r_[np.linspace(1, 1.5, 100), np.linspace(1.5, 0.75, 100), np.linspace(0.75, 1.6, 200)], index=idx)
    out = dd.build({"strategy": strat}, pd.DataFrame({"SOXX": soxx}))
    assert "chart" not in out                       # drawn from backtest.curves in the browser
    assert "SOXX fell 50% in the same stretch" in out["read"]
    assert dd.build({}, None) is None
    assert dd.build({"strategy": strat}, None)["bench"] is None


def test_digest_line():
    data = {"rankings": [], "drawdowns": {"read": "The worst drop (−49%, ...)."}}
    sec = next(s for s in digest.sections(data) if s["title"].startswith("Drawdowns"))
    assert sec["items"] == ["The worst drop (−49%, ...)."]


@pytest.mark.skipif(__import__("shutil").which("node") is None, reason="node not installed")
def test_js_underwater_matches_python():
    import json
    import re
    import subprocess
    html = page_source()
    block = re.search(r"// ---- underwater ----.*?// ---- end underwater ----", html, re.S).group(0)
    vals = [1.0, 1.2, 0.9, None, 1.1, 1.3, 1.25, 0.65, 1.4]
    pts = [[f"2020-01-{i + 1:02d}", v] for i, v in enumerate(vals)]
    js = block + f"\nconsole.log(JSON.stringify(underwaterPts({json.dumps(pts)})));"
    got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    s = pd.Series([v for v in vals if v is not None], index=[p[0] for p in pts if p[1] is not None])
    want = dd.underwater(s)
    assert [g[0] for g in got] == list(want.index)
    assert [g[1] for g in got] == pytest.approx(list(want.values))
