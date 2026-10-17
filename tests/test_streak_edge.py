"""Stayers vs new picks (streak_edge.py) and its Research-tab card."""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import streak_edge  # noqa: E402
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

HTML = page_source()


def Q(date, end, picks, rets, uni=0.0):
    return {"date": date, "end": end, "picks": picks, "pick_returns": dict(zip(picks, rets)), "universe": uni}


def test_known_answer_by_hand():
    qs = [Q("q1", "q2", ["A", "B"], [0.10, 0.00]),
          Q("q2", "q3", ["A", "C"], [0.05, 0.01], uni=0.01),      # A stays (+0.04), C new (0.00)
          Q("q3", "q4", ["C", "D"], [0.03, -0.02], uni=0.0)]      # C stays (+0.03), D new (-0.02)
    rows = streak_edge.classify(qs)
    assert rows == [{"date": "q2", "stay": [pytest.approx(0.04)], "new": [pytest.approx(0.0)]},
                    {"date": "q3", "stay": [pytest.approx(0.03)], "new": [pytest.approx(-0.02)]}]
    r = streak_edge.build(qs)
    assert r["stayers"] == {"n": 2, "avg_excess": 0.035, "hit_rate": 1.0}
    assert r["new"] == {"n": 2, "avg_excess": -0.01, "hit_rate": 0.0}
    assert r["diff"] == pytest.approx(0.045) and r["quarters"] == 2 and r["diff_q"] == pytest.approx(0.045)
    assert "Too few to tell" in r["read"]


def test_gap_in_calendar_means_no_stayers():
    qs = [Q("q1", "q2", ["A"], [0.1]), Q("q3", "q4", ["A", "B"], [0.1, 0.2])]   # q1 didn't end on q3
    assert streak_edge.classify(qs)[0]["stay"] == [] and streak_edge.build(qs) is None


def test_no_look_ahead():
    qs = [Q(f"d{i}", f"d{i+1}", [["A", "B", "C"], ["A", "D", "E"], ["D", "F", "A"]][i % 3], [0.01 * i, -0.02, 0.03])
          for i in range(9)]
    full = streak_edge.classify(qs)
    for k in range(2, 9):
        assert streak_edge.classify(qs[:k]) == full[:k - 1]               # a later quarter never changes an earlier row
    bumped = copy.deepcopy(qs)
    for p in bumped[5]["pick_returns"]:
        bumped[5]["pick_returns"][p] += 1.0                               # change returns: membership doesn't move
    assert [(r["date"], len(r["stay"]), len(r["new"])) for r in streak_edge.classify(bumped)] == \
           [(r["date"], len(r["stay"]), len(r["new"])) for r in full]


def test_reads():
    big = lambda d, t, q=40: {"stayers": {"n": 100, "avg_excess": 0.02}, "new": {"n": 80, "avg_excess": 0.01},
                              "quarters": q, "diff_q": d, "t": t}
    assert "came out ahead (t 2.5)" in streak_edge.read(big(0.01, 2.5)) and "stayers" in streak_edge.read(big(0.01, 2.5))
    assert "new picks came out ahead" in streak_edge.read(big(-0.01, -2.1))
    assert "could easily be luck (t 0.3" in streak_edge.read(big(0.002, 0.3))
    assert "no spread" in streak_edge.read(big(0.01, None))
    assert "Too few" in streak_edge.read(big(0.01, 3.0, q=3))


def test_empty_and_short():
    assert streak_edge.build(None) is None and streak_edge.build([]) is None
    assert streak_edge.build([Q("q1", "q2", ["A"], [0.1])]) is None
    assert streak_edge.build([Q("q1", "q2", ["A"], [0.1]), {"date": "q2", "picks": [], "universe": None}]) is None


def test_demo_and_card():
    import slim
    d = slim.unpack(json.loads((ROOT / "docs" / "data.json").read_text()))
    r = d["research"]["streak_edge"]
    again = streak_edge.build(d["backtest"]["quarters"])                 # from the rounded copy in data.json
    for g in ("stayers", "new"):
        assert r[g]["n"] == again[g]["n"] and r[g]["avg_excess"] == pytest.approx(again[g]["avg_excess"], abs=1e-4)
    assert r["stayers"]["n"] + r["new"]["n"] == sum(len(q["picks"]) for q in d["backtest"]["quarters"][1:])
    assert 'id="streak-card" hidden' in HTML and "renderStreakEdge();" in HTML and "<dt>Streak effect</dt>" in HTML
    fn = re.search(r"function renderStreakEdge\(\).*?\n}\n", HTML, re.S).group(0)
    assert "textContent = K.read" in fn and "card.hidden = !(K" in fn
