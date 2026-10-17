"""Biggest score moves (score_moves.py on top of explain.py): which stat moved each stock."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import digest  # noqa: E402
import explain  # noqa: E402
import score_moves as sm  # noqa: E402

W = {"growth": 2.0, "margin": 1.0, "mom": 1.0, "off": 0.0}
LABELS = {"growth": "Revenue growth YoY", "margin": "Gross-margin change (YoY)", "mom": "Price momentum"}


def row(t, z, raw=None, rank=None):
    return {"ticker": t, "z": z, "raw": raw or {}, "rank": rank}


def test_one_factor_changes_and_is_named():
    prev = [row("MU", {"growth": 0.0, "margin": 0.5, "mom": 0.1}, {"growth": 0.12}, 9)]
    cur = [row("MU", {"growth": 1.0, "margin": 0.5, "mom": 0.1}, {"growth": 0.31}, 4)]
    moves = sm.build(explain.explain_all(prev, cur, W), LABELS)
    assert len(moves) == 1 and moves[0]["ticker"] == "MU"
    assert moves[0]["delta"] == pytest.approx(2.0 / 4)                  # 2 × Δz 1.0 ÷ Σw 4
    assert moves[0]["text"] == "MU +0.50 (#9 → #4): mostly Revenue growth YoY +12.0% → +31.0% (+0.50)."


def test_contributions_add_up_even_when_factors_appear():
    prev = [row("A", {"growth": 0.4, "margin": None, "mom": -0.2}), row("B", {"growth": 1.0, "margin": 1.0, "mom": 1.0})]
    cur = [row("A", {"growth": -0.6, "margin": 1.5, "mom": 0.9}), row("B", {"growth": 0.2, "margin": 0.9, "mom": -0.5})]
    e = explain.explain_all(prev, cur, W)
    for m in sm.build(e, LABELS, min_delta=0.0):
        full = e[m["ticker"]]
        assert sum(d["contrib"] for d in full["drivers"]) == pytest.approx(m["delta"], abs=0.01)


def test_spread_out_moves_say_so():
    prev = [row("X", {"growth": 0.0, "margin": 0.0, "mom": 0.0})]
    cur = [row("X", {"growth": 0.2, "margin": 0.5, "mom": 0.5})]       # contribs .1, .125, .125
    m = sm.build(explain.explain_all(prev, cur, W), LABELS)[0]
    assert "spread out:" in m["text"] and "mostly" not in m["text"]


def test_threshold_order_and_cap():
    prev = [row(t, {"growth": 0.0, "margin": 0.0, "mom": 0.0}) for t in "ABCDEFG"]
    cur = [row(t, {"growth": g, "margin": 0.0, "mom": 0.0}) for t, g in zip("ABCDEFG", [0.1, -2, 1, 0.5, -0.6, 3, 0.29])]
    moves = sm.build(explain.explain_all(prev, cur, W), LABELS)
    assert [m["ticker"] for m in moves] == ["F", "B", "C", "E", "D"]      # |Δ| = 1.5, 1, .5, .3, .25; A, G < 0.15
    assert all(abs(m["delta"]) >= sm.MIN_DELTA for m in moves)


def test_first_run_and_added_removed_tickers():
    assert sm.build(None, LABELS) == [] and sm.build({}, LABELS) == []
    prev = [row("OLD", {"growth": 1.0}), row("KEEP", {"growth": 0.0, "mom": 0.0})]
    cur = [row("NEW", {"growth": 2.0}), row("KEEP", {"growth": 1.0, "mom": 0.0})]
    moves = sm.build(explain.explain_all(prev, cur, W), LABELS)
    assert [m["ticker"] for m in moves] == ["KEEP"]                       # only stocks in both runs


def test_digest_section_only_when_there_are_moves():
    base = {"rankings": [], "top_n": 5}
    titles = [s["title"] for s in digest.sections(base)]
    assert not any("score moves" in t for t in titles)
    data = {**base, "explain": {"run_date": "2026-10-14"},
            "score_moves": [{"text": "MU +0.50: mostly Revenue growth YoY +12.0% → +31.0% (+0.50)."}]}
    sec = next(s for s in digest.sections(data) if s["title"].startswith("Biggest score moves"))
    assert sec["title"] == "Biggest score moves since 2026-10-14" and sec["items"][0].startswith("MU +0.50")
