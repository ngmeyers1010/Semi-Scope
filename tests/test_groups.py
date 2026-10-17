"""Group leadership: index math, breadth, relative strength, missing members."""
import numpy as np
import pandas as pd
import pytest

import groups


def panel():
    idx = pd.bdate_range("2025-01-01", periods=200)
    a = pd.Series(np.linspace(100, 200, 200), index=idx)      # steady riser
    b = pd.Series(np.linspace(100, 50, 200), index=idx)       # steady faller
    c = pd.Series(100.0, index=idx)                            # flat
    soxx = pd.Series(np.linspace(100, 120, 200), index=idx)
    return pd.DataFrame({"A": a, "B": b, "C": c}), pd.DataFrame({"SOXX": soxx})


def test_group_index_is_average_daily_return():
    px, _ = panel()
    idx = groups.group_index(px, ["A", "C"])
    r = (px["A"].pct_change().fillna(0) + 0) / 2               # C contributes 0% every day
    assert idx.iloc[-1] == pytest.approx((1 + r).prod())
    assert idx.iloc[0] == 1.0


def test_breadth_counts():
    px, _ = panel()
    assert groups.breadth(px, ["A", "B", "C"]) == pytest.approx(1 / 3)   # only A is above its 50-day avg
    assert groups.breadth(px, ["NOPE"]) is None


def test_relative_return_vs_soxx_and_leadership():
    px, bench = panel()
    meta = {"A": {"group": "Up"}, "B": {"group": "Down"}, "C": {"group": "Flat"}}
    out = groups.build(px, bench, meta)
    g = {r["group"]: r for r in out["groups"]}
    soxx_3m = bench["SOXX"].iloc[-1] / bench["SOXX"].iloc[-64] - 1
    assert g["Flat"]["rel_3m"] == pytest.approx(0 - soxx_3m)
    assert [r["group"] for r in out["groups"]] == ["Up", "Flat", "Down"]
    assert out["read"].startswith("Up (1 stock) leading")
    assert "SOXX" in out["index"] and out["index"]["Up"][0][1] == 1.0


def test_missing_member_and_gaps_dont_crash():
    px, bench = panel()
    px.loc[px.index[50:60], "A"] = np.nan
    meta = {"A": {"group": "G"}, "GONE": {"group": "G"}, "ALSO_GONE": {"group": "H"}}
    out = groups.build(px, bench, meta)
    assert [r["group"] for r in out["groups"]] == ["G"] and out["groups"][0]["n"] == 1
    assert np.isfinite(groups.group_index(px, ["A"]).iloc[-1])
    assert groups.build(px, None, meta)["groups"][0]["rel_3m"] is None
