"""The fast numpy path and the score() memo must give exactly the same answers."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import demo_data  # noqa: E402
import factors  # noqa: E402
from factors import _known, _val  # noqa: E402  (the original, slow pandas helpers)

T = [f"T{i}" for i in range(10)]


def slow_reference(series, asof):
    """The original pandas implementation of a few factors, kept as the yardstick."""
    rev, cogs, inv = (_known(series.get(k), asof) for k in ("revenue", "cogs", "inventory"))
    if rev is None or len(rev) < 6 or (asof - rev["end"].iloc[-1]).days > factors.STALE_DAYS:
        return None
    L, yr = rev["end"].iloc[-1], pd.Timedelta(days=364)
    r0, r1, c0, c1 = _val(rev, L), _val(rev, L - yr), _val(cogs, L), _val(cogs, L - yr)
    i0, i1 = _val(inv, L, tol=10), _val(inv, L - yr, tol=10)
    last4 = rev.tail(4)
    return {"rev_growth": r0 / r1 - 1, "gm_change": (1 - c0 / r0) - (1 - c1 / r1),
            "inv_days_change": i0 / c0 * 91 - i1 / c1 * 91, "rev_ttm": last4["val"].sum()}


def test_fast_path_matches_pandas():
    s, px, _ = demo_data.generate(T, ["SPY", "SOXX"], "2014-03-01", seed=4)
    checked = 0
    for d in px.index[400::90]:
        for t in T:
            if t not in s:
                continue
            ref = slow_reference(s[t], d)
            if ref is None:
                continue
            got = factors.fundamental_factors(s[t], d)
            for k in ("rev_growth", "gm_change", "inv_days_change"):
                assert got[k] == pytest.approx(ref[k], rel=1e-12, nan_ok=True), (t, d, k)
            assert factors._Known(s[t]["revenue"], d.value).ttm() == pytest.approx(ref["rev_ttm"], rel=1e-12)
            checked += 1
    assert checked > 50


def test_memo_returns_identical_copies():
    s, px, _ = demo_data.generate(T, ["SPY", "SOXX"], "2014-03-01", seed=4)
    d = px.index[-1]
    plain_r, plain_z = factors.score(s, px, d, T)
    factors.MEMO = {}
    try:
        a_r, a_z = factors.score(s, px, d, T)
        a_r["score"] = 999                                 # mutating a result must not poison the memo
        b_r, b_z = factors.score(s, px, d, T)
        assert len(factors.MEMO) == 1
    finally:
        factors.MEMO = None
    pd.testing.assert_frame_equal(plain_z, b_z)
    pd.testing.assert_series_equal(plain_r["score"], b_r["score"])


@pytest.mark.skipif(not os.environ.get("SEMISCOPE_SLOW"), reason="slow: set SEMISCOPE_SLOW=1")
def test_fast_flag_reuses_research(tmp_path):
    subprocess.run([sys.executable, "run.py", "--demo"], cwd=ROOT, check=True, capture_output=True)
    full = json.loads((ROOT / "docs" / "data.json").read_text())   # research/stats aren't packed
    out = subprocess.run([sys.executable, "run.py", "--demo", "--fast"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    fast = json.loads((ROOT / "docs" / "data.json").read_text())
    assert "--fast: reusing robustness grid" in out
    assert fast["research"]["robustness"] == full["research"]["robustness"]
    assert fast["backtest"]["stats"]["strategy"]["cagr"] == full["backtest"]["stats"]["strategy"]["cagr"]
    assert round(fast["backtest"]["stats"]["strategy"]["cagr"], 3) == 0.212
    assert fast["run_log"][0]["kind"] == "fast"
