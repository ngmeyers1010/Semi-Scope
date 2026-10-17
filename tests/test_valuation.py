"""'Cheap vs its own history': P/S percentile vs the stock's own 5-year range."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import valuation
from fundamentals import shares_series
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).parents[1]
ASOF = pd.Timestamp("2026-10-13")


def company(rev_per_q=1e9, start="2019-01-01", shares_raw=1e8, split_date=None):
    """Quarterly revenue (filed 35 days after quarter end) + cover-page shares, SEC-shaped."""
    ends = pd.date_range(start, ASOF - pd.Timedelta(days=40), freq="QE")
    rev = pd.DataFrame({"end": ends, "val": float(rev_per_q), "filed": ends + pd.Timedelta(days=35)})
    dei = []
    for i, e in enumerate(ends):
        f = e + pd.Timedelta(days=35)
        n = shares_raw * (10 if split_date is not None and f >= pd.Timestamp(split_date) else 1)
        dei.append({"end": (f - pd.Timedelta(days=7)).strftime("%Y-%m-%d"), "val": n,
                    "filed": f.strftime("%Y-%m-%d"), "accn": f"a{i}"})
    splits = None
    if split_date is not None:
        idx = pd.bdate_range(start, ASOF)
        splits = pd.Series(0.0, index=idx)
        splits[idx[idx >= pd.Timestamp(split_date)][0]] = 10.0
    facts = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": dei}}}}}
    return {"revenue": rev, "shares": shares_series(facts, splits)}


def prices(start="2019-01-01", level=50.0):
    idx = pd.bdate_range(start, ASOF)
    return pd.Series(level, index=idx, dtype=float)


def test_split_in_window_does_not_fake_a_cheap_history():
    # 10:1 split in 2024; prices are split-ADJUSTED (flat), raw share counts jump 10x.
    # Shares are converted to today's units, so P/S is flat through the split: 50th percentile.
    v = valuation.one(company(split_date="2024-06-10"), prices(), ASOF)
    assert v["lo"] == pytest.approx(v["hi"]) == pytest.approx(v["ps"])
    assert v["pct"] == 50.0 and v["label"] == "about usual"
    assert v["years"] >= 4.9


def test_percentile_tracks_the_price():
    p = prices()
    p.loc["2025-01-01":] = 100.0          # price doubled -> P/S at the top of its range
    v = valuation.one(company(), p, ASOF)
    assert v["pct"] > 75 and v["ps"] == pytest.approx(2 * v["lo"], rel=1e-6)
    p.loc["2026-09-01":] = 20.0           # crash -> cheapest it has been
    v = valuation.one(company(), p, ASOF)
    assert v["pct"] < 10 and v["label"] == "near its cheapest"


def test_less_than_two_years_has_no_percentile():
    v = valuation.one(company(start="2025-01-01"), prices(start="2025-01-01"), ASOF)
    assert v["ps"] > 0 and v["pct"] is None and v["label"] == "not enough history"
    assert "not enough history" in valuation.sentence("X", v)


def test_zero_or_negative_sales_and_foreign_filer():
    assert valuation.one(company(rev_per_q=0), prices(), ASOF) is None
    assert valuation.one(company(rev_per_q=-5e8), prices(), ASOF) is None
    assert valuation.one({}, prices(), ASOF) is None            # foreign filer: no SEC series
    close = pd.DataFrame({"A": prices(), "F": prices()})
    out = valuation.build({"A": company()}, close, ["A", "F", "MISSING"], ASOF)
    assert list(out) == ["A"]


def test_uses_only_known_filings():
    # a quarter filed AFTER asof must not change today's P/S
    s = company()
    late = pd.DataFrame({"end": [ASOF - pd.Timedelta(days=10)], "val": [9e9], "filed": [ASOF + pd.Timedelta(days=20)]})
    s2 = {**s, "revenue": pd.concat([s["revenue"], late], ignore_index=True)}
    assert valuation.one(s2, prices(), ASOF)["ps"] == valuation.one(s, prices(), ASOF)["ps"]


def test_percentile_ties_and_label_bounds():
    assert valuation.percentile(5, [1, 5, 9]) == pytest.approx(50.0)
    assert valuation.percentile(10, [1, 2, 3]) == 100.0
    assert np.isnan(valuation.percentile(1, []))
    assert [valuation.label(p) for p in (0, 9.9, 10, 24.9, 25, 75, 75.1, 90, 90.1, 100)] == [
        "near its cheapest", "near its cheapest", "cheaper than usual", "cheaper than usual", "about usual",
        "about usual", "pricier than usual", "pricier than usual", "near its priciest", "near its priciest"]
    assert [valuation.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 100, 101, 111)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "100th", "101st", "111th"]


def test_digest_mentions_holdings_at_extremes():
    import digest
    hold = lambda t, pct: {"ticker": t, "in_universe": True, "current": {"rank": 3, "valuation":
                           {"ps": 2.0, "pct": pct, "label": valuation.label(pct)}}}
    data = {"prices_asof": "2026-10-13", "top_n": 5, "rankings": [], "universe_size": 30,
            "holdings": [hold("LOW", 4.0), hold("MID", 50.0), hold("HIGH", 97.0)]}
    items = next(s for s in digest.build(data, write=False)["sections"] if s["title"] == "Your stocks")["items"]
    text = " ".join(items)
    assert "LOW: P/S 2.0x, 4th percentile" in text and "HIGH: P/S 2.0x, 97th percentile" in text
    assert "MID: P/S" not in text


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_labels_match_python():
    html = page_source()
    block = re.search(r"// ---- valpct .*?// ---- end valpct ----", html, re.S).group(0)
    pcts = [None, 0, 3.2, 9.99, 10, 17, 24.9, 25, 50, 75, 75.1, 89.9, 90, 90.1, 99.5, 100]
    ords = [0, 1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 50.4, 12.5, 2.5, 99.6, 101, 111, 112]
    js = block + "\nconsole.log(JSON.stringify({l:%s.map(valLabel), o:%s.map(ordinal)}));" % (
        json.dumps(pcts), json.dumps(ords))
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out["l"] == [valuation.label(p) for p in pcts]
    assert out["o"] == [valuation.ordinal(p) for p in ords]
