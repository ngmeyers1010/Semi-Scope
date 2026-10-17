"""Rank-change explainer: contributions add up, appear/disappear handled, right top driver."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import explain  # noqa: E402
import alerts  # noqa: E402

W = {"a": 1.0, "b": 1.0, "c": 0.5, "info": 0.0}


def test_contributions_sum_to_score_change():
    rng = np.random.default_rng(1)
    for _ in range(50):
        zp = dict(zip("abc", rng.normal(size=3)))
        zn = dict(zip("abc", rng.normal(size=3)))
        e = explain.explain_change(zp, zn, W)
        assert sum(d["contrib"] for d in e["drivers"]) == pytest.approx(e["delta"], abs=1e-9)
        # unchanged factor set: contribution = w * dz / W
        d = next(d for d in e["drivers"] if d["factor"] == "a")
        assert d["contrib"] == pytest.approx(1.0 * (zn["a"] - zp["a"]) / 2.5, abs=1e-12)


def test_factor_appearing_and_disappearing():
    e = explain.explain_change({"a": 1.0, "b": 0.5}, {"a": 1.0, "c": 2.0}, W)
    st = {d["factor"]: d["status"] for d in e["drivers"]}
    assert st == {"a": "changed", "b": "dropped", "c": "new"}
    assert sum(d["contrib"] for d in e["drivers"]) == pytest.approx(e["delta"], abs=1e-12)
    assert "info" not in st                                       # weight-0 factors ignored


def test_top_driver_on_hand_made_example():
    # inventory blew out (z falls 1.5), momentum ticked up slightly
    e = explain.explain_change({"a": 0.2, "b": 1.0, "c": 0.0}, {"a": 0.3, "b": -0.5, "c": 0.1}, W,
                               {"b": 4.0}, {"b": 27.0})
    top = e["drivers"][0]
    assert top["factor"] == "b" and top["contrib"] == pytest.approx(-1.5 / 2.5)
    s = explain.sentence(e, {"b": "Inventory-days change YoY"}, n=1)
    assert s.startswith("Inventory-days change YoY") and "(-0.60)" in s


def test_alert_gets_because_line():
    prev = {"mode": "live", "top_n": 5, "universe_size": 20, "rankings": [], "holdings": [
        {"ticker": "MU", "current": {"rank": 3}}]}
    cur = {"mode": "live", "top_n": 5, "universe_size": 20, "rankings": [], "holdings": [
        {"ticker": "MU", "current": {"rank": 18}}], "explain": {"run_text": {"MU": "Inventory days +4d → +27d (-0.42)"}}}
    a = [x for x in alerts.compute(prev, cur) if x["kind"] == "holding"]
    assert a and "because: Inventory days" in a[0]["text"]
