"""'What changed this week' (Rankings tab): week_diff.py and weekDiff() in index.html must agree."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import week_diff  # noqa: E402
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

HTML = page_source()
node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

CASES = [
    ({"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}, {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}, 3),  # nothing moved
    ({"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}, {"D": 1, "A": 2, "B": 3, "C": 4, "F": 5, "E": 6}, 3),  # D enters, C leaves
    ({"A": 5, "B": 5, "C": 1, "D": 9}, {"A": 2, "B": 2, "C": 9, "D": 1}, 2),     # ties: same climb -> lower new rank, then name
    ({"A": 1, "B": 2, "C": 3}, {"A": 1, "NEW": 2, "B": 3, "C": 4}, 2),           # a new ticker enters the top: no "from"
    ({"A": 1, "GONE": 2, "B": 3}, {"A": 1, "B": 2}, 2),                          # a removed ticker leaves: no "to"
    ({"Z": 10, "Y": 10, "X": 10, "W": 10, "V": 1}, {"Z": 6, "Y": 6, "X": 6, "W": 6, "V": 2}, 1),   # only 3 movers shown
    ({}, {"A": 1}, 5), (None, {"A": 1}, 5), ({"A": 1}, {}, 5),                   # nothing to compare -> None
]


def test_python_diff_by_hand():
    d = week_diff.diff(*CASES[1])
    assert [x["ticker"] for x in d["entered"]] == ["D"] and d["entered"][0] == {"ticker": "D", "from": 4, "to": 1}
    assert d["left"] == [{"ticker": "C", "from": 3, "to": 4}]
    assert [x["ticker"] for x in d["up"]] == ["D", "F"] and [x["ticker"] for x in d["down"]] == ["A", "B", "C"]  # all -1: by new rank
    t = week_diff.diff(*CASES[2])
    assert [x["ticker"] for x in t["up"]] == ["D", "A", "B"]       # D +8, then A/B +3 each, A first by name
    assert week_diff.diff(*CASES[3])["entered"] == [{"ticker": "NEW", "from": None, "to": 2}]
    assert week_diff.diff(*CASES[3])["new"] == ["NEW"]
    assert week_diff.diff(*CASES[4])["left"] == [{"ticker": "GONE", "from": 2, "to": None}]
    assert len(week_diff.diff(*CASES[5])["up"]) == 3
    assert week_diff.diff(*CASES[0]) == {"entered": [], "left": [], "up": [], "down": [], "new": []}
    for c in CASES[6:]:
        assert week_diff.diff(*c) is None


@node
def test_js_weekdiff_matches_python():
    block = re.search(r"// ---- week diff ----.*?// ---- end week diff ----", HTML, re.S).group(0)
    js = block + f"\nconst C = {json.dumps(CASES)};\nconsole.log(JSON.stringify(C.map(c => weekDiff(c[0], c[1], c[2]))));"
    got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert got == [week_diff.diff(*c) for c in CASES]
    rows = [{"ticker": "A", "rank": 1.0}, {"ticker": "B", "rank": None}, {"ticker": "C", "rank": 3}]
    js2 = block + f"\nconsole.log(JSON.stringify(rankMap({json.dumps(rows)})));"
    out = json.loads(subprocess.run(["node", "-e", js2], capture_output=True, text=True, check=True).stdout)
    assert out == week_diff.ranks_of(rows) == {"A": 1, "C": 3}


def test_build_uses_five_sessions_back_and_handles_short_history():
    idx = pd.bdate_range("2026-09-01", periods=10)
    px = pd.DataFrame({"A": range(10)}, index=idx, dtype=float)
    seen = []
    fake = lambda d: (seen.append(d), pd.DataFrame({"rank": [2.0, 1.0, float("nan")]}, index=["A", "B", "C"]))[1]
    out = week_diff.build(fake, px, idx[-1], ["A", "B", "C"])
    assert seen == [idx[-6]] and out == {"asof": idx[-6].strftime("%Y-%m-%d"), "ranks": {"A": 2, "B": 1}}
    assert week_diff.build(fake, px.iloc[:5], idx[4], ["A"]) is None


def test_card_is_wired_and_text_only():
    assert 'id="week-card" hidden' in HTML and "renderWeek();" in HTML
    fn = re.search(r"function renderWeek\(\).*?\n}\n", HTML, re.S).group(0)
    assert "innerHTML" not in fn and "textContent" in fn
    assert "card.hidden = !d" in fn                                   # no earlier snapshot -> hidden


def test_demo_data_has_week_ranks():
    import slim
    d = slim.unpack(json.loads((ROOT / "docs" / "data.json").read_text()))
    w = d.get("week_ranks")
    assert w and w["asof"] < d["prices_asof"] and len(w["ranks"]) >= 10
    assert len(json.dumps(w)) < 2000                                  # tiny


H = [{"asof": "w1", "ranks": {"A": 1, "B": 9, "C": 2, "E": 3}},
     {"asof": "w2", "ranks": {"A": 2, "B": 1, "E": 3}},                 # C missing this week
     {"asof": "w3", "ranks": {"A": 3, "B": 2, "C": 1, "E": 4}}]
CUR = {"A": 3, "B": 3, "C": 2, "D": 1, "E": 9, "F": 3}
STREAK_CASES = [(H, CUR, t, 3) for t in "ABCDEFZ"] + [([], CUR, "A", 3), (None, CUR, "A", 3), (H, {}, "A", 3),
                                                      (H, CUR, "A", 2), (H, {"E": 4}, "E", 4)]


def test_streaks_by_hand():
    s = lambda *a: week_diff.streak_of(*a)
    assert s(H, CUR, "A", 3) == 4                      # today + all 3 snapshots
    assert s(H, CUR, "B", 3) == 3                      # rank 9 in w1 ends it
    assert s(H, CUR, "C", 3) == 2                      # missing in w2 ends it
    assert s(H, CUR, "D", 3) == 1                      # new to the top today
    assert s(H, CUR, "E", 3) == 0                      # not in the top today
    assert s(H, {"E": 4}, "E", 4) == 4                 # exactly top_n counts: today 4, w3 4, w2 3, w1 3
    assert s([], CUR, "A", 3) == 1 and s(None, CUR, "A", 3) == 1
    assert week_diff.streaks(H, CUR, 3) == {"A": 4, "B": 3, "C": 2, "D": 1, "F": 1}


@node
def test_js_streakof_matches_python():
    block = re.search(r"// ---- streaks ----.*?// ---- end streaks ----", HTML, re.S).group(0)
    js = block + f"\nconst C = {json.dumps(STREAK_CASES)};\nconsole.log(JSON.stringify(C.map(c => streakOf(...c))));"
    got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert got == [week_diff.streak_of(*c) for c in STREAK_CASES]


def test_history_steps_and_week_entry():
    idx = pd.bdate_range("2026-08-03", periods=30)
    px = pd.DataFrame({"A": range(30)}, index=idx, dtype=float)
    fake = lambda d: pd.DataFrame({"rank": [1.0, 2.0]}, index=["A", "B"])
    h = week_diff.history(fake, px, idx[-1])
    assert [x["asof"] for x in h] == [idx[-1 - k].strftime("%Y-%m-%d") for k in (20, 15, 10, 5)]
    assert week_diff.week_entry(h, px, idx[-1]) == h[-1] == week_diff.build(fake, px, idx[-1], ["A", "B"])
    short = week_diff.history(fake, px.iloc[:12], idx[11])            # only 10 and 5 back fit
    assert [x["asof"] for x in short] == [idx[1].strftime("%Y-%m-%d"), idx[6].strftime("%Y-%m-%d")]
    assert week_diff.week_entry([], px, idx[-1]) is None


def test_demo_rank_history_and_pill():
    import slim
    d = slim.unpack(json.loads((ROOT / "docs" / "data.json").read_text()))
    h = d["rank_history"]
    assert len(h) == 4 and [x["asof"] for x in h] == sorted(x["asof"] for x in h) and h[-1] == d["week_ranks"]
    assert len(json.dumps(h)) < 3000
    assert "${streakPill(r)}" in HTML and 'class="pill streak"' in HTML
