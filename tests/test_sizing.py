"""Inverse-volatility sizing: weights, no look-ahead, Python/JS agreement."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import orders
import sizing
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).parents[1]


def px_two(n=200, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n)
    calm = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    wild = 100 * np.cumprod(1 + rng.normal(0, 0.03, n))
    return pd.DataFrame({"CALM": calm, "WILD": wild}, index=idx)


def test_weights_sum_to_one_and_calmer_gets_more():
    px = px_two()
    w = sizing.weights(px, ["CALM", "WILD"], px.index[-1], "inverse_vol")
    assert w.sum() == pytest.approx(1.0)
    assert w["CALM"] > w["WILD"]
    assert w["CALM"] / w["WILD"] == pytest.approx(2.9, rel=0.25)    # ~3x calmer -> ~3x the money


def test_equal_path_unchanged():
    px = px_two()
    w = sizing.weights(px, ["CALM", "WILD", "X"], px.index[-1], "equal")
    assert list(w) == pytest.approx([1 / 3] * 3)
    picks = [{"ticker": "A", "price": 10.0}, {"ticker": "B", "price": 33.0}]
    assert orders.plan(picks, 1000, False) == orders.plan(picks, 1000, False, None)


def test_no_look_ahead():
    px = px_two()
    d = px.index[120]
    before = sizing.weights(px, ["CALM", "WILD"], d, "inverse_vol")
    later = px.copy()
    later.iloc[121:, 0] *= np.linspace(1, 5, len(later) - 121)   # CALM goes wild AFTER d
    assert sizing.weights(later, ["CALM", "WILD"], d, "inverse_vol").equals(before)


def test_missing_vol_gets_average_and_weighted_plan_tracks_targets():
    w = orders.calmer_weights([{"ticker": "A", "vol_63d": 0.2}, {"ticker": "B", "vol_63d": 0.4},
                               {"ticker": "C", "vol_63d": None}])
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["A"] == pytest.approx(2 * w["B"])
    assert w["C"] == pytest.approx((w["A"] + w["B"]) / 2)
    p = orders.plan([{"ticker": "A", "price": 1.0}, {"ticker": "B", "price": 1.0}], 900, True, {"A": 2, "B": 1})
    assert [r["cost"] for r in p["rows"]] == pytest.approx([600, 300])


def test_backtest_baseline_is_equal_weight():
    import backtest, inspect
    assert inspect.signature(backtest.run_backtest).parameters["weighting"].default == "equal"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_weighted_plan_javascript_matches_python():
    html = page_source()
    fns = re.search(r"function calmerWeights\(.*?\n\}", html, re.S).group(0) + "\n" + \
        re.search(r"const FRAC_STEP = .*?\nfunction planOrders\(.*?\n\}", html, re.S).group(0)
    picks = [{"ticker": "A", "price": 187.3, "vol_63d": 0.31}, {"ticker": "B", "price": 42.1, "vol_63d": 0.62},
             {"ticker": "C", "price": 905.0, "vol_63d": None}, {"ticker": "D", "price": 12.7, "vol_63d": 0.45}]
    cases = [(picks, 1000, True), (picks, 1000, False), (picks, 2500, False), (picks[:2], 333.33, False)]
    js = fns + "\nconst C=%s;console.log(JSON.stringify(C.map(c=>{const w=calmerWeights(c[0]);" \
               "return [w, planOrders(c[0],c[1],c[2],w)]})));" % json.dumps(cases)
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    for (pk, amt, frac), (jw, jp) in zip(cases, out):
        w = orders.calmer_weights(pk)
        assert w == pytest.approx(jw)
        p = orders.plan(pk, amt, frac, w)
        assert [r["shares"] for r in p["rows"]] == pytest.approx([r["shares"] for r in jp["rows"]])
        assert p["leftover"] == pytest.approx(jp["leftover"])
