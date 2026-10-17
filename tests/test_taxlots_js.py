"""The dashboard's JS lot helpers match mytrades.py."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

import mytrades as mt
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_python():
    html = page_source()
    block = re.search(r"// ---- lots .*?// ---- end lots ----", html, re.S).group(0)
    dates = ["2023-03-15", "2024-02-29", "2023-12-31", "2024-01-31", "2020-02-29"]
    lots = [{"ticker": "MU", "date": "2023-03-15", "shares": 5.0, "price": 60.0},
            {"ticker": "MU", "date": "2024-02-29", "shares": 3.5, "price": 90.0},
            {"ticker": "AMD", "date": "2024-06-01", "shares": 2.0, "price": 150.0}]
    cases = [("MU", 4, 100, "2024-03-16"), ("MU", 7, 100, "2025-03-01"), ("MU", 99, 80, "2025-02-28"),
             ("AMD", 1, 120, "2025-06-02")]
    js = block + "\nconsole.log(JSON.stringify({d:%s.map(longTermDate), p:%s.map(c=>previewSell(%s,c[0],c[1],c[2],c[3]))}));" % (
        json.dumps(dates), json.dumps(cases), json.dumps(lots))
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out["d"] == [mt.long_term_date(d).strftime("%Y-%m-%d") for d in dates]
    for c, j in zip(cases, out["p"]):
        p = mt.preview_sell(lots, *c)
        assert (j["st"], j["lt"], j["capped"]) == (pytest.approx(p["st"]), pytest.approx(p["lt"]), p["capped"])
        assert [x["term"] for x in j["pieces"]] == [x["term"] for x in p["pieces"]]
