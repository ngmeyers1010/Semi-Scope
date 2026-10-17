"""'Invest $X' calculator: edge cases + Python/JavaScript agreement."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orders  # noqa: E402
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).resolve().parents[1]
PICKS = [{"ticker": "A", "price": 50.0}, {"ticker": "B", "price": 120.0}, {"ticker": "C", "price": 900.0},
         {"ticker": "D", "price": 33.3}, {"ticker": "E", "price": 210.0}]


def test_fractional_spends_almost_everything_and_never_overspends():
    p = orders.plan(PICKS, 1000, fractional=True)
    assert p["invested"] <= 1000 + 1e-9
    assert p["leftover"] < 0.5                       # only rounding crumbs left
    assert all(abs(r["cost"] - 200) < 0.1 for r in p["rows"])


def test_whole_shares_and_too_small_budget():
    p = orders.plan(PICKS, 1000, fractional=False)
    rows = {r["ticker"]: r for r in p["rows"]}
    assert all(float(r["shares"]).is_integer() for r in p["rows"])
    costs = [r["cost"] for r in p["rows"] if r["ticker"] != "C"]
    assert max(costs) - min(costs) < 120             # leftover spread evenly, not piled on the cheapest
    assert rows["C"]["shares"] == 0                  # a $900 share never fits a $200 slot
    assert p["invested"] <= 1000 and p["leftover"] < min(r["price"] for r in PICKS)
    tiny = orders.plan(PICKS, 100, fractional=False)
    c = next(r for r in tiny["rows"] if r["ticker"] == "C")
    assert c["shares"] == 0 and "more than this budget" in c["note"]


def test_missing_price_is_skipped_and_money_goes_to_the_rest():
    picks = PICKS[:2] + [{"ticker": "X", "price": None}]
    p = orders.plan(picks, 1000, fractional=True)
    x = next(r for r in p["rows"] if r["ticker"] == "X")
    assert x["shares"] == 0 and "no price" in x["note"]
    assert p["invested"] > 999                       # split between the two with prices


def test_zero_amount_and_no_prices():
    assert orders.plan(PICKS, 0)["invested"] == 0
    assert orders.plan([{"ticker": "X", "price": None}], 500)["leftover"] == 500


def test_compare_holdings():
    c = orders.compare(["A", "B", "C"], {"A": 1, "Z": 25, "Y": 8, "W": None}, n_ranked=28)
    assert c["owned_and_picked"] == ["A"] and c["picked_not_owned"] == ["B", "C"]
    assert c["owned_bottom_half"] == ["Z"] and c["owned_unranked"] == ["W"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_matches_python():
    html = page_source()
    fn = re.search(r"const FRAC_STEP = .*?\nfunction planOrders\(.*?\n\}", html, re.S).group(0)
    cases = [(PICKS, 1000, True), (PICKS, 1000, False), (PICKS, 100, False), (PICKS, 12345.67, False),
             (PICKS[:2] + [{"ticker": "X", "price": None}], 1000, True), (PICKS, 0, True)]
    js = fn + "\nconst C=%s;console.log(JSON.stringify(C.map(c=>planOrders(c[0],c[1],c[2]))));" % json.dumps(cases)
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    for (picks, amt, frac), j in zip(cases, out):
        p = orders.plan(picks, amt, frac)
        assert [r["shares"] for r in p["rows"]] == pytest.approx([r["shares"] for r in j["rows"]])
        assert p["leftover"] == pytest.approx(j["leftover"])
