"""Weekly review: question generator (Python) + the page's shared JS copies."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import slim
import weekly
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data.json"


def load(p=DATA):
    return slim.unpack(json.loads(p.read_text()))


@pytest.mark.skipif(not DATA.exists(), reason="run python run.py --demo first")
def test_three_distinct_questions_about_real_things():
    d = load()
    qs = weekly.questions(d)
    assert len(qs) == 3 and len({q["kind"] for q in qs}) == 3 and len({q["q"] for q in qs}) == 3
    tickers = {r["ticker"] for r in d["rankings"] + d["watchlist"]}
    for q in qs:
        assert q["link"].startswith("index.html")
        if "#stock=" in q["link"]:
            t = q["link"].split("=")[1]
            assert t in tickers and t in q["q"]
    assert d.get("weekly", {}).get("questions") == qs        # stored by run.py


def test_sparse_data_gives_fewer_questions_without_crashing(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "tests" / "fixtures" / "make_sparse.py")], check=True, capture_output=True)
    f = ROOT / "tests" / "fixtures" / "sparse_data.json"
    d = load(f)
    f.unlink()
    qs = weekly.questions(d)
    assert len(qs) <= 3
    assert weekly.questions({}) == [] and weekly.build({})["questions"] == []


def test_each_generator_on_hand_made_data():
    d = {"holdings": [{"ticker": "MU"}, {"ticker": "AMD"}], "top_n": 5,
         "explain": {"rebalance_date": "2026-09-01", "rebalance": {"MU": {"rank_prev": 9, "rank_now": 16},
                                                                   "AMD": {"rank_prev": 11, "rank_now": 9}},
                     "rebalance_text": {"MU": "Revenue growth YoY +40% → +5%"}},
         "rankings": [{"ticker": "INTC", "rank": 2, "valuation": {"pct": 97.0, "ps": 2.5}},
                      {"ticker": "MU", "rank": 16, "valuation": {"pct": 4.0, "ps": 1.1}}],
         "steady": {"backtest": {"available": True, "worst": {"start": "2022-01-05", "end": "2022-12-23", "excess": -0.28}}},
         "earnings_cal": {"rows": [{"ticker": "MU", "owned": True, "days": 6, "move": 0.061}]},
         "groups": {"groups": [{"group": "Compute", "rel_3m": 0.08}, {"group": "Memory", "rel_3m": -0.12}]}}
    qs = weekly.questions(d, n=5)
    assert [q["kind"] for q in qs] == ["mover", "valuation", "steady", "earnings", "groups"]
    assert qs[0]["q"].startswith("MU fell from #9 to #16") and qs[0]["hint"].startswith("Revenue growth")
    assert "INTC" in qs[1]["q"] and "97th percentile" in qs[1]["q"]       # most extreme of the two
    assert "trailed SPY by 28%" in qs[2]["q"]
    assert "±6.1%" in qs[3]["q"]
    # broken pieces are skipped, not fatal
    bad = {**d, "explain": {"rebalance": {"MU": {"rank_prev": "x", "rank_now": None}}}, "groups": {"groups": [None]}}
    assert all(q["kind"] != "mover" for q in weekly.questions(bad, n=5))


def test_weekly_page_shares_the_dashboards_helpers():
    page = (ROOT / "docs" / "weekly.html").read_text()
    main = page_source()
    for pat in (r"const hEsc = .*?\n", r"function unpackPairs\(x\)\{.*?\n\}\n"):
        a, b = re.search(pat, page, re.S), re.search(pat, main, re.S)
        assert a and b and a.group(0) == b.group(0), f"weekly.html's copy drifted: {pat}"
    # every data value that reaches innerHTML goes through hEsc (no raw ${q.q} etc.)
    assert not re.search(r"\$\{(q\.q|q\.hint|r\.text|a\.text|h\.ticker|r\.ticker)\}", page)
    assert 'href="weekly.html"' in main


def _wk(prev, cur_rows, hist=None, top_n=3, explain=None):
    d = {"top_n": top_n, "rankings": cur_rows, "week_ranks": {"asof": "2026-10-06", "ranks": prev}}
    if hist is not None:
        d["rank_history"] = hist
    if explain is not None:
        d["explain"] = explain
    return d


ROWS = [{"ticker": "D", "rank": 1.0}, {"ticker": "A", "rank": 2.0}, {"ticker": "B", "rank": 3.0},
        {"ticker": "C", "rank": 4.0}, {"ticker": "X", "rank": None}]


def test_rankings_week_wording():
    prev = {"A": 1, "B": 2, "C": 3, "D": 4}
    hist = [{"asof": "a", "ranks": {"A": 1, "B": 3, "D": 9}}, {"asof": "b", "ranks": prev}]
    rw = weekly.rankings_week(_wk(prev, ROWS, hist))
    assert rw["text"] == ("D (#4 → #1) joined the top 3; C (#3 → #4) dropped out. "
                          "Longest streak: A and B (3+ weeks in the top 3).")
    assert rw["link"] == "index.html#tab=rank&card=week-card" and rw["asof"] == "2026-10-06"
    same = weekly.rankings_week(_wk({"D": 1, "A": 2, "B": 3, "C": 4}, ROWS, []))
    assert same["text"] == "Same top 3 as last week."                    # no history: no streak line (all 1)
    new = weekly.rankings_week(_wk({"A": 1, "B": 2, "C": 3}, ROWS, None))
    assert new["text"].startswith("D (unranked → #1) joined the top 3; C (#3 → #4) dropped out.")


def test_entered_question_is_linked_and_hinted():
    prev = {"A": 1, "B": 2, "C": 3, "D": 4}
    ex = {"rebalance_date": "2026-09-01", "rebalance_text": {"D": "Price momentum +5% → +30%"}}
    qs = weekly.questions(_wk(prev, ROWS, explain=ex), n=5)
    q = next(q for q in qs if q["kind"] == "entered")
    assert q["q"].startswith("D joined the top 3 this week (from #4 to #1).")
    assert q["link"] == "index.html#tab=rank&card=week-card&stock=D"
    assert q["hint"] == "Since the 2026-09-01 rebalance: Price momentum +5% → +30%"
    ex2 = {**ex, "run_date": "2026-10-12", "run_text": {"D": "Gross margin up"}}
    assert next(q for q in weekly.questions(_wk(prev, ROWS, explain=ex2), n=5)
                if q["kind"] == "entered")["hint"] == "Since the last update (2026-10-12): Gross margin up"
    page = (ROOT / "docs" / "weekly.html").read_text()
    assert re.search(r"/\^index\\\.html\(#\[(.*?)\]\*\)\?\$/", page).group(1) == r"\w=.\-&"   # safeLink lets it through


def test_missing_week_data_means_no_section_and_no_question():
    for d in ({"rankings": ROWS, "top_n": 3}, {"rankings": ROWS, "top_n": 3, "week_ranks": None},
              {"rankings": ROWS, "top_n": 3, "week_ranks": {"asof": "x", "ranks": {}}}, {},
              {"rankings": [], "top_n": 3, "week_ranks": {"asof": "x", "ranks": {"A": 1}}}):
        assert weekly.rankings_week(d) is None
        assert all(q["kind"] != "entered" for q in weekly.questions(d, n=9))
        assert weekly.build(d)["rankings_week"] is None
    # no one entered: no question, but the summary still says so
    same = _wk({"D": 1, "A": 2, "B": 3, "C": 4}, ROWS)
    assert all(q["kind"] != "entered" for q in weekly.questions(same, n=9))


@pytest.mark.skipif(not DATA.exists(), reason="run python run.py --demo first")
def test_demo_rankings_week_is_stored_and_page_uses_textcontent():
    d = load()
    rw = d["weekly"]["rankings_week"]
    assert rw == weekly.rankings_week(d) and "joined the top 5" in rw["text"]
    page = (ROOT / "docs" / "weekly.html").read_text()
    assert "$('rankweek').textContent = RW.text" in page and 'id="rankweek-card" hidden' in page
