"""Quarterly report cards: boundaries, append-only, sensible with missing data."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import quarterly  # noqa: E402
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).resolve().parents[1]


def test_quarter_boundaries():
    assert quarterly.quarter_of("2026-03-31") == "2026Q1"
    assert quarterly.quarter_of("2026-04-01") == "2026Q2"
    lo, hi = quarterly.bounds("2026Q4")
    assert (lo, hi) == (pd.Timestamp("2026-10-01"), pd.Timestamp("2026-12-31"))
    # only FINISHED quarters get a report
    assert quarterly.completed_quarters("2026-01-15", "2026-10-14") == ["2026Q1", "2026Q2", "2026Q3"]
    assert quarterly.completed_quarters("2026-10-15", "2026-12-31") == []


def test_quarter_returns_chain_across_quarters():
    idx = pd.to_datetime(["2026-01-02", "2026-03-31", "2026-04-01", "2026-06-30"])
    r = quarterly.quarter_returns(pd.Series([100, 110, 115, 121.0], index=idx))
    assert r["2026Q1"] == pytest.approx(0.10)
    assert r["2026Q2"] == pytest.approx(121 / 110 - 1)        # measured from Q1's close, not Q2's first day


def test_never_rewrites_existing_report(tmp_path):
    (tmp_path / "2026Q1.md").write_text("ORIGINAL")
    made = quarterly.write_new({}, tmp_path, ["2026Q1", "2026Q2"])
    assert made == ["2026Q2"]
    assert (tmp_path / "2026Q1.md").read_text() == "ORIGINAL"


def test_report_with_no_picks_and_no_trades_is_sensible():
    md = quarterly.build_report({}, "2027Q1")
    assert "# SemiScope report card: 2027Q1" in md
    assert "not enough data" in md and "No picks recorded" in md and "No real trades" in md


def test_report_uses_live_paper_when_available():
    data = {"quarter_returns": {"paper": {"2027Q1": 0.08}, "SPY": {"2027Q1": 0.05}},
            "paper": {"entries": [{"date": "2027-03-01", "reason": "rebalance", "picks": ["MU", "AMD"]}]},
            "my_trades": {"quarters": [{"quarter": "2027Q1", "me": 0.02, "spy": 0.05, "vs_spy": -0.03}]}}
    md = quarterly.build_report(data, "2027Q1")
    assert "Model beat SPY by 3.0%" in md and "you trailed the model by 6.0%" in md
    assert "Paper picks from 2027-03-01" in md and "backtest" not in md.lower().split("verdict")[1][:60]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_dashboard_markdown_converter():
    html = page_source()
    fn = re.search(r"function mdToHtml\(md\)\{.*?\n\}", html, re.S).group(0)
    md = quarterly.build_report({"quarter_returns": {"SPY": {"2027Q1": 0.05}}}, "2027Q1") + "\n<script>x</script>"
    out = subprocess.run(["node", "-e", fn + "\nconsole.log(mdToHtml(%s))" % json.dumps(md)],
                         capture_output=True, text=True, check=True).stdout
    assert "<h1>" in out and "<table>" in out and "<li>" in out and "<b>Verdict:</b>" in out
    assert "<script>" not in out                                 # HTML is escaped
