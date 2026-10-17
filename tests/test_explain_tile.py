"""The "?" on KPI tiles: explainTile() text (node), tile() markup, and Learn as the single source."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).resolve().parents[1]
HTML = page_source()
node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
EXPECTED_TERMS = {"CAGR", "Sharpe ratio", "Max drawdown", "Hit rate", "Paper portfolio", "Volatility", "Beta",
                  "VaR (value at risk)", "Effective bets", "Information ratio", "Tracking error", "t-stat", "p-value",
                  "P&L (profit and loss)"}
BLOCK = re.search(r"// ---- explain tile ----.*?// ---- end explain tile ----", HTML, re.S).group(0)


def js(calls):
    code = BLOCK + f"\nconst C = {json.dumps(calls)};\nconsole.log(JSON.stringify(C.map(c => explainTile(...c))));"
    return json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)


@node
def test_each_term_plugs_in_the_numbers():
    got = js([
        ["CAGR", "D.", {"cagr": 0.21242, "total": 15.702, "spy": 0.13, "start": "2012-03-01", "end": "2026-10-09"}],
        ["Sharpe ratio", "D.", {"sharpe": 0.84482, "spy": 0.71}],
        ["Max drawdown", "D.", {"mdd": -0.48559, "spy": -0.34}],
        ["Hit rate", "D.", {"rate": 0.5862, "n": 58}],
        ["Paper portfolio", "D.", {"ret": 0.031, "since": "2026-09-01", "spy": 0.012}],
    ])
    assert got[0] == ("D. CAGR +21.2%: money in this strategy grew about 21.2% a year on average, so $1,000 in 2012 "
                      "would be about $16,702 by 2026-10-09 (S&P 500: +13.0% a year).")
    assert got[1] == "D. Sharpe 0.84: about 0.84 of yearly return for each 1 of yearly bounce (volatility); the S&P 500 managed 0.71."
    assert got[2] == "D. Max drawdown −48.6%: at the worst point, $1,000 at the previous high had shrunk to about $514 (S&P 500 worst: −34.0%)."
    assert got[3].startswith("D. It beat the S&P 500 in 59% of 58 quarters (about 34 of them).")
    assert got[4] == "D. Paper return +3.1% since 2026-09-01, vs +1.2% for the S&P 500 over the same days. These picks were recorded before the results were known."


@node
def test_missing_values_give_the_definition_only_and_text_stays_text():
    got = js([["CAGR", "Def.", {}], ["Sharpe ratio", "Def.", {"sharpe": None}], ["Hit rate", "Def.", {"rate": 0.5}],
              ["Unknown term", "Def.", {"x": 1}], ["CAGR", "", {}], ["CAGR", "<b>x</b> & y", {"cagr": 0.1}]])
    assert got[:4] == ["Def."] * 4 and got[4] == ""
    assert got[5].startswith("<b>x</b> & y CAGR +10.0%")              # plain text: the page uses textContent
    fn = re.search(r"document.addEventListener\('click'.*?\n}\);", HTML, re.S).group(0)
    assert "tip.textContent = explainTile(" in fn and "innerHTML" not in fn


def test_tiles_use_learn_terms_that_exist():
    import html as _h
    terms = {_h.unescape(t) for t in re.findall(r'<div class="term"><dt>([^<]+)</dt>', HTML)}
    branches = set(re.findall(r"term === '([^']+)'", BLOCK))
    used = {t for t in branches if re.search(rf",\s*'{re.escape(t)}',\s*[{{\w]", HTML)}
    assert branches == EXPECTED_TERMS and used == branches        # every branch is wired to a tile
    assert branches <= terms                                       # and has a Learn entry
    t = re.search(r"function tile\(.*?\n}\n", HTML, re.S).group(0)
    assert 'aria-expanded="false"' in t and "aria-controls=" in t and 'data-term="${hEsc(term)}"' in t and "hidden" in t
    assert "LEARN_DEFS[dt.textContent.trim()] = dd.textContent.trim()" in HTML        # one source: the Learn list


@node
def test_round_92_terms():
    got = js([
        ["Volatility", "", {"vol": 0.318}], ["Beta", "", {"beta": 1.42}],
        ["VaR (value at risk)", "", {"dollars": -243.5, "amount": 10000, "var": 0.02435}],
        ["Effective bets", "", {"eff": 2.07, "n": 5}], ["Effective bets", "", {"eff": 4.1, "n": 5}],
        ["Information ratio", "", {"ir": 0.45}], ["Information ratio", "", {"ir": -0.2}],
        ["Tracking error", "", {"te": 0.181}], ["t-stat", "", {"t": 2.31, "n": 58}], ["t-stat", "", {"t": -0.4}],
        ["p-value", "", {"p": 0.012}], ["p-value", "", {"p": 0.0004}], ["p-value", "", {"p": 0.25}],
        ["P&L (profit and loss)", "", {"pnl": 1234.4, "realized": 400, "unrealized": 834.4}],
        ["P&L (profit and loss)", "", {"pnl": -50}],
    ])
    assert got[0] == "Volatility 32%: in a typical year these stocks could easily land about 32% above or below their average return."
    assert got[1].startswith("Beta 1.42: when the S&P 500 moved 1%, these stocks tended to move about 1.4%") and "roughly 14%" in got[1]
    assert got[2] == "On a bad day (about 1 trading day in 20), $10,000 in these stocks could lose about $244 (2.4%) or more."
    assert got[3].endswith("about 2.1 independent bets, because they tend to rise and fall together.") and got[4].endswith("4.1 independent bets.")
    assert "0.45% a year of lead" in got[5] and "0.20% a year of lag" in got[6]
    assert got[7] == "Tracking error 18.1%: in a typical year the strategy ends up about 18% ahead of or behind SPY."
    assert got[8] == "t 2.3: the average edge over SPY is 2.3 standard errors above zero (58 quarters); 2+ is unlikely to be luck."
    assert "below zero;" in got[9]
    assert got[10] == "p 0.012: if there were no real edge, luck alone would look this good about 1.2% of the time (about 1 in 83)."
    assert got[11].startswith("p < 0.001") and "about 25% of the time (about 1 in 4)" in got[12]
    assert got[13] == ("Total P&L $1,234: $400 locked in from shares you sold (realized) and $834 on shares you still own "
                       "(unrealized, it can still change).")
    assert got[14] == "Total P&L −$50."
    missing = js([[t, "Def.", {}] for t in sorted(EXPECTED_TERMS)])
    assert missing == ["Def."] * len(EXPECTED_TERMS)


PRACTICE_KEYWORDS = {    # each mapped exercise's name or skill must mention this
    "CAGR": "return", "Max drawdown": "drawdown", "Volatility": "vol", "t-stat": "t-stat", "p-value": "t-stat",
    "Information ratio": "excess", "Tracking error": "excess", "Hit rate": "backtest", "P&L (profit and loss)": "fifo",
    "Backtest": "backtest", "Point-in-time": "peeking", "Factor": "factor", "z-score": "z-score", "σ (z-move)": "z_move",
    "Inverse-volatility weighting": "inverse", "P/S vs its own history": "percentile", "Composite score": "score",
    "Signal decay": "decay", "Up/down capture": "capture", "Underwater / recovery time": "drawdown",
    "Bootstrap": "bootstrap", "Streak effect": "stayers", "Beta": "beta", "VaR (value at risk)": "bad day",
    "Sharpe ratio": "sharpe", "Effective bets": "effective bets", "Paper portfolio": "paper portfolio",
}


def _term_exercise():
    block = re.search(r"const TERM_EXERCISE = \{(.*?)\};", HTML, re.S).group(1)
    return {t: (int(n), name) for t, n, name in re.findall(r"'([^']+)': \[(\d+), '([a-z_]+)'\]", block)}


def test_practice_map_points_at_real_relevant_exercises():
    import html as _h
    import sys
    sys.path.insert(0, str(ROOT / "practice"))
    import check
    m = _term_exercise()
    assert set(m) == set(PRACTICE_KEYWORDS)
    terms = {_h.unescape(t) for t in re.findall(r'<div class="term"><dt>([^<]+)</dt>', HTML)}
    for term, (n, name) in m.items():
        assert term in terms, term                                         # a real Learn term
        assert n in check.EXERCISES and check.EXERCISES[n][0][5:] == name, (term, n, name)
        about = (check.EXERCISES[n][0] + " " + check.EXERCISES[n][1] + " " + check.SKILLS[n]).lower()
        assert PRACTICE_KEYWORDS[term] in about, (term, about)
    branches = set(re.findall(r"term === '([^']+)'", BLOCK))
    assert branches <= set(m)          # every number with a "?" now has an exercise (gaps closed in rounds 94-96)


def test_practice_html_has_an_anchor_for_every_exercise():
    import sys
    sys.path.insert(0, str(ROOT / "practice"))
    import check
    page = (ROOT / "docs" / "practice.html").read_text()
    assert sorted(int(x) for x in re.findall(r'id="ex-(\d+)"', page)) == sorted(check.EXERCISES)


@node
def test_practice_line_text_and_explain_unchanged():
    code = BLOCK + "\nconsole.log(JSON.stringify([practiceLine('Max drawdown'), practiceLine('Turnover'), practiceLine('Streak effect')]));"
    got = json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)
    assert got[0] == {"text": "Practice it: ex06 max_drawdown (python practice/check.py 6)", "href": "practice.html#ex-6"}
    assert got[1] is None and got[2]["href"] == "practice.html#ex-30"
    assert js([["Max drawdown", "D.", {"mdd": -0.5}]])[0] == "D. Max drawdown −50%: at the worst point, $1,000 at the previous high had shrunk to about $500."
    fn = re.search(r"function practiceNode\(.*?\n}\n", HTML, re.S).group(0)
    assert "textContent" in fn and "innerHTML" not in fn
