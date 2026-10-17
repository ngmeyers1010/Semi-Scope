"""'What could $1,000 become?' (outcomes.py): block bootstrap with known answers."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import digest  # noqa: E402
import outcomes as oc  # noqa: E402


def qs(strat, spy=None):
    spy = spy if spy is not None else [0.0] * len(strat)
    return [{"return": r, "spy": s} for r, s in zip(strat, spy)]


def test_constant_returns_give_identical_paths():
    o = oc.build(qs([0.02] * 12), n_paths=300)
    for h in o["horizons"]:
        want = 1000 * 1.02 ** (4 * h["years"])
        assert h["p10"] == pytest.approx(want) and h["p50"] == pytest.approx(want) and h["p90"] == pytest.approx(want)
        assert h["loss"] == 0 and h["beat_spy"] == 1.0
    assert o["worst_dd_5pct"] == pytest.approx(0.0)
    assert o["fan"]["p50"][-1] == round(1000 * 1.02 ** 20) and len(o["fan"]["q"]) == 21


def test_seed_makes_it_reproducible_and_blocks_are_consecutive():
    rng = np.random.default_rng(0)
    r = list(rng.normal(0.03, 0.12, 40))
    a, b = oc.build(qs(r), n_paths=500), oc.build(qs(r), n_paths=500)
    assert a == b
    assert oc.build(qs(r), n_paths=500, seed=7)["horizons"] != a["horizons"]
    idx = oc.sample_index(40, 20, n_paths=50, block=4, seed=1)
    assert idx.shape == (50, 20) and idx.max() < 40
    blocks = idx.reshape(50, 5, 4)
    assert (np.diff(blocks, axis=2) == 1).all()             # 4 consecutive quarters per block


def test_paired_spy_comparison():
    rng = np.random.default_rng(1)
    r = list(rng.normal(0.02, 0.1, 30))
    o = oc.build(qs(r, r), n_paths=500)                     # strategy IS SPY
    assert all(h["beat_spy"] == 0.0 for h in o["horizons"])
    better = oc.build(qs([x + 0.01 for x in r], r), n_paths=500)
    assert all(h["beat_spy"] == 1.0 for h in better["horizons"])   # paired: always ahead


def test_percentiles_ordered_and_read():
    rng = np.random.default_rng(2)
    o = oc.build(qs(list(rng.normal(0.02, 0.15, 50)), list(rng.normal(0.015, 0.08, 50))), n_paths=1000)
    for h in o["horizons"]:
        assert h["p10"] <= h["p50"] <= h["p90"] and 0 <= h["loss"] <= 1
    assert all(lo <= m <= hi for lo, m, hi in zip(o["fan"]["p10"], o["fan"]["p50"], o["fan"]["p90"]))
    assert "not a forecast" in o["read"] and "$1,000 became" in o["read"]


def test_too_few_quarters_and_bad_values():
    assert oc.build(qs([0.01] * 7)) is None and oc.build([]) is None and oc.build(None) is None
    rows = qs([0.01] * 10) + [{"return": float("nan"), "spy": 0.0}, {"return": None}]
    o = oc.build(rows, n_paths=100)
    assert o["n_quarters"] == 10
    no_spy = oc.build([{"return": 0.01} for _ in range(10)], n_paths=100)
    assert "beat_spy" not in no_spy["horizons"][0] and "spy_p50" not in no_spy["fan"]


def test_digest_line():
    data = {"rankings": [], "outcomes": {"read": "Replaying the backtest's 59 quarters ..."}}
    sec = next(s for s in digest.sections(data) if s["title"].startswith("What could $1,000"))
    assert sec["items"][0].startswith("Replaying")
