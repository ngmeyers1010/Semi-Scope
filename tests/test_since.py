"""'Since your last visit': Python and the dashboard's JS give the same text."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import since
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).parents[1]
PREV = {"asof": "2026-10-12", "top": ["AAPL", "ANET", "INTC", "MPWR", "AMAT"],
        "ranks": {"MU": 9, "AMD": 12, "NVDA": 4, "MSFT": 20}, "pnl": 1000.0, "paper": 0.050, "alerts": 15}
CUR = {"asof": "2026-10-15", "top": ["AAPL", "NVDA", "INTC", "MPWR", "AMAT"],
       "ranks": {"MU": 16, "AMD": 9, "NVDA": 4}, "pnl": 1042.4, "paper": 0.062, "alerts": 17}


def test_full_diff_text():
    r = since.diff(PREV, CUR)
    assert r["text"] == ("Since Oct 12: NVDA entered the top 5; ANET left the top 5; MU fell #9 → #16; "
                         "AMD rose #12 → #9; no longer tracking MSFT; your P&L +$42; paper portfolio +1.2 pts; "
                         "2 new alerts.")
    assert r["moved"] == {"MU": 9, "AMD": 12}


def test_first_visit_and_corrupted():
    for bad in (None, {}, "garbage", {"asof": "2026"}, {"asof": "2026-10-12", "top": "x", "ranks": {}}, [1, 2]):
        r = since.diff(bad, CUR)
        assert r["first"] and r["text"].startswith("Welcome")


def test_nothing_new():
    same = {**PREV, "asof": "2026-10-13"}
    assert since.diff(PREV, same)["text"] == "Nothing new since Oct 12."
    assert since.diff(PREV, PREV)["text"] == "Up to date: nothing new since Oct 12."


def test_snapshot_from_data():
    data = {"prices_asof": "2026-10-13", "top_n": 2,
            "rankings": [{"ticker": "B", "rank": 2}, {"ticker": "A", "rank": 1}, {"ticker": "W", "rank": None}],
            "holdings": [{"ticker": "A", "current": {"rank": 1}}, {"ticker": "X", "current": {"rank": None, "would_rank": 7}},
                         {"ticker": "Z", "current": None}],
            "my_trades": {"totals": {"pnl": 5.0}}, "alert_log": [1, 2, 3]}
    s = since.snapshot(data)
    assert s == {"asof": "2026-10-13", "top": ["A", "B"], "ranks": {"A": 1, "X": 7}, "price_only": ["X"],
                 "pnl": 5.0, "paper": None, "alerts": 3}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_matches_python():
    html = page_source()
    block = re.search(r"// ---- since .*?// ---- end since ----", html, re.S).group(0)
    cases = [[PREV, CUR], [None, CUR], ["garbage", CUR], [PREV, {**PREV, "asof": "2026-10-13"}], [PREV, PREV],
             [{**PREV, "pnl": None}, {**CUR, "pnl": -12345.6, "paper": None, "alerts": 14}],
             [{**PREV, "ranks": {}}, {**CUR, "top": []}]]
    data = {"prices_asof": "2026-10-13", "top_n": 2, "rankings": [{"ticker": "B", "rank": 2}, {"ticker": "A", "rank": 1}],
            "holdings": [{"ticker": "A", "current": {"rank": 1}}], "paper": {"stats": {"paper": {"total_return": 0.1}}}}
    js = block + "\nconsole.log(JSON.stringify({d:%s.map(c=>diffSnapshots(c[0],c[1])), s:makeSnapshot(%s)}));" % (
        json.dumps(cases), json.dumps(data))
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    for (p, c), j in zip(cases, out["d"]):
        py = since.diff(p, c)
        assert j["text"] == py["text"] and j["moved"] == py["moved"] and j["first"] == py["first"]
    assert out["s"] == since.snapshot(data)
