"""Round 40 bug hunt: one regression test per confirmed bug."""
import math

import numpy as np
import pandas as pd
import pytest

import confidence
import mytrades as mt
import paper
import since


def _px(cols, n=60):
    idx = pd.bdate_range("2026-01-02", periods=n)
    rng = np.random.default_rng(0)
    return pd.DataFrame({c: 100 * np.cumprod(1 + rng.normal(0, 0.01, n)) for c in cols}, index=idx)


def test_paper_survives_a_pick_with_no_prices():
    px = _px(["AAA", "BBB"])
    bench = _px(["SPY"])
    state = {"entries": [{"date": str(px.index[5].date()), "picks": ["AAA", "BBB", "GONE"], "reason": "x",
                          "entry_prices": {"AAA": 100.0, "BBB": 100.0, "GONE": 50.0}}]}
    out = paper.performance(state, px, bench)          # used to KeyError: ['GONE'] not in index
    assert out is not None and len(out["curves"]["paper"]) > 2
    h = {x["ticker"]: x for x in out["holdings"]}
    assert h["GONE"]["last"] is None and h["AAA"]["last"] is not None


def test_trade_after_last_price_is_not_fatal(tmp_path):
    close = _px(["MU"])
    f = tmp_path / "t.csv"
    later = (close.index[-1] + pd.Timedelta(days=3)).date()
    f.write_text(f"date,ticker,action,shares,price,note\n{later},MU,buy,1,100,\n")
    out = mt.build(f, close, close, _px(["SPY"]), None)   # used to IndexError
    assert out["n_trades"] == 1
    assert any("after the latest price" in e for e in out["errors"])


def test_since_ignores_nan_and_bool_ranks():
    prev = {"asof": "2026-10-12", "top": [], "ranks": {"MU": float("nan"), "AMD": True, "NVDA": 5}}
    cur = {"asof": "2026-10-13", "top": [], "ranks": {"MU": 9, "AMD": 3, "NVDA": 4}}
    r = since.diff(prev, cur)                           # used to ValueError on int(nan)
    assert r["moved"] == {"NVDA": 5}


def test_confidence_near_identical_returns_not_strong():
    x = [0.01 + 1e-17 * i for i in range(20)]           # float noise only
    r = confidence.t_test(x)
    assert r["t"] is None or abs(r["t"]) < 1e6
    assert confidence.analyze(x)["verdict"] != "Statistically strong"


def test_sparse_fixture_builder():
    """The 'first live run' fixture used by the browser smoke test strips what it should."""
    import json
    import sys
    from pathlib import Path
    src = Path(__file__).parents[1] / "docs" / "data.json"
    if not src.exists():
        pytest.skip("run python run.py --demo first")
    sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
    import make_sparse
    d = make_sparse.sparse(json.loads(src.read_text()))
    assert d["paper"] is None and d["reports"] == [] and d["my_trades"]["n_trades"] == 0
    assert any(h["current"] is None for h in d["holdings"])
    json.dumps(d, allow_nan=False)                      # still strict JSON
