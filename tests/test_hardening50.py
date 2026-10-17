"""Round 50 bug hunt (rounds 41-49 code): one regression test per confirmed issue."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import alerts
import digest
import groups
import mytrades
import since
import slim
import steady
import valuation
from fundamentals import shares_series
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).resolve().parents[1]
HTML = page_source()
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _js_block(start, end):
    return re.search(re.escape(start) + r".*?" + re.escape(end), HTML, re.S).group(0)


def _fn(name):
    """Source of a top-level `function name(...)` in index.html."""
    i = HTML.index(f"function {name}(")
    j = HTML.index("\nfunction ", i + 10)
    return HTML[i:j]


# 1. XSS: my_trades.csv text reached innerHTML unescaped
def test_trade_csv_cannot_inject_html(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("date,ticker,action,shares,price,note\n"
                 "2025-01-02,MU,<img src=x onerror=alert(1)>,1,10,\n"
                 "2025-01-02,<svg onload=alert(1)>,buy,1,10,\n"
                 "2025-01-03,$mu ,buy,2,11,\n")
    df, errors = mytrades.load(f)
    assert list(df["ticker"]) == ["MU"]                       # junk ticker rejected, "$mu " cleaned
    assert any("doesn't look like a ticker" in e for e in errors)
    real, lots = _fn("renderReal"), _fn("renderLots")
    assert "M.errors.map(hEsc)" in real
    for body in (real, lots):                                 # every ticker cell is escaped
        assert not re.search(r"\$\{(r|l)\.ticker\}", body), "unescaped ticker in trades tables"
    assert "<option>${hEsc(t)}</option>" in lots


# 2. A price-only holding was labelled "Top pick" (it's never picked)
def test_price_only_holding_is_not_a_top_pick():
    h = {"ticker": "ASML", "in_universe": True, "current": {"rank": None, "would_rank": 3}}
    assert alerts.holding_signal(h, 30, 5) == (alerts.PRICE_ONLY, 3)
    w = {"ticker": "GOOGL", "in_universe": False, "current": {"rank": None, "would_rank": 3}}
    assert alerts.holding_signal(w, 30, 5) == ("Top pick", 3)          # watchlist: unchanged
    data = {"prices_asof": "2026-10-13", "top_n": 5, "universe_size": 30, "rankings": [], "holdings": [h]}
    mine = next(s for s in digest.build(data, write=False)["sections"] if s["title"] == "Your stocks")
    assert mine["items"] == ["ASML: Price data only (≈#3/30, price data only)"]
    assert "priceOnly ? ['≈','Price data only','muted']" in _fn("renderMine")


# 3. The page re-announced a stale stock's old move as "today"
def test_move_chips_skip_stale_stocks():
    assert "if (!m || m.stale_days) return;" in _fn("renderMoves")


# 4. A group whose members listed 3 months ago got a 6-month return
def test_group_with_new_listing_has_no_fake_long_return():
    idx = pd.bdate_range("2025-01-01", periods=300)
    px = pd.DataFrame({"OLD": np.linspace(100, 130, 300), "NEW": np.nan}, index=idx)
    px.iloc[-63:, 1] = np.linspace(10, 20, 63)
    bench = pd.DataFrame({"SOXX": np.linspace(100, 110, 300)}, index=idx)
    out = groups.build(px, bench, {"OLD": {"group": "Old"}, "NEW": {"group": "Fresh IPO"}})
    fresh = next(g for g in out["groups"] if g["group"] == "Fresh IPO")
    assert fresh["ret_6m"] is None and fresh["rel_6m"] is None
    assert fresh["ret_1m"] is not None
    assert groups.group_index(px, ["GONE"]).empty
    assert groups.group_index(px.assign(NEW=np.nan), ["NEW"]).empty


# 5. Sorting the rankings descending put blank rows on top
@needs_node
def test_rank_sort_keeps_blanks_last_both_ways():
    block = _js_block("// ---- ranksort", "// ---- end ranksort ----")
    rows = [{"ticker": "A", "rank": 1, "score": 1.0, "valuation": {"pct": 5}},
            {"ticker": "B", "rank": None, "score": None},
            {"ticker": "C", "rank": None, "would_rank": 2, "score": None, "valuation": {"pct": None}},
            {"ticker": "D", "rank": 3, "score": 0.5, "valuation": {"pct": 90}}]
    js = block + ("\nconst R=%s; const o={};for (const k of ['rank','score','val']) for (const d of [1,-1])"
                  " o[k+d]=sortRankRows(R,k,d).map(r=>r.ticker).join('');console.log(JSON.stringify(o));") % json.dumps(rows)
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out == {"rank1": "ACDB", "rank-1": "DCAB", "score1": "ADBC", "score-1": "DABC",
                   "val1": "ADBC", "val-1": "DABC"}


# 6. A Friday holiday let the weekly P/S history see a filing one day early
def test_valuation_history_has_no_holiday_lookahead():
    idx = pd.bdate_range("2023-01-02", "2024-04-30")
    idx = idx[idx != pd.Timestamp("2024-03-29")]                   # Good Friday: no trading
    close = pd.Series(50.0, index=idx)
    ends = pd.date_range("2021-03-31", "2023-12-31", freq="QE")
    filed = ends + pd.Timedelta(days=30)
    filed = filed.where(ends != pd.Timestamp("2023-12-31"), pd.Timestamp("2024-03-28"))   # late 10-K, a Thursday
    rev = pd.DataFrame({"end": ends, "val": [5e9 if e == pd.Timestamp("2023-12-31") else 1e9 for e in ends],
                        "filed": filed})
    dei = [{"end": str(f.date()), "val": 1e8, "filed": str(f.date()), "accn": f"a{i}"} for i, f in enumerate(filed)]
    s = {"revenue": rev, "shares": shares_series({"facts": {"dei": {"EntityCommonStockSharesOutstanding":
                                                                       {"units": {"shares": dei}}}}})}
    h = valuation.ps_history(s, close, pd.Timestamp("2024-04-30"))
    assert pd.Timestamp("2024-03-28") in h.index and pd.Timestamp("2024-03-29") not in h.index
    from factors import sales_yield                                # what was knowable at Thursday's close
    assert h[pd.Timestamp("2024-03-28")] == pytest.approx(1 / sales_yield(s, pd.Timestamp("2024-03-28"), 50.0))


# 7 + 9. steady.read: rounding matches the page's tile; odd cases read sensibly
def test_steady_read_rounding_and_edge_wording():
    base = {"available": True, "label": "backtest", "info_ratio": 0.3, "best": {"excess": 0.2},
            "worst": {"start": "2022-01-03", "end": "2022-12-30", "excess": -0.004}}
    t = steady.read({**base, "pct_windows_beat": 0.125})
    assert "Beat SPY in 13% " in t                                  # JS Math.round(12.5) = 13
    assert "at −0.4% vs SPY" in t and "-0%" not in t
    flat = steady.read({**base, "pct_windows_beat": 0.0, "best": {"excess": 0.0},
                        "worst": {**base["worst"], "excess": 0.0}})
    assert flat.startswith("Moved in step with SPY") and "never trailed" not in flat
    paper = steady.read({**base, "label": "paper", "pct_windows_beat": 1.0,
                         "worst": {**base["worst"], "excess": 0.03}})
    assert "backtest" not in paper and "hasn't trailed" in paper
    assert "at −28% vs SPY" in steady.read({**base, "pct_windows_beat": 0.7,
                                            "worst": {**base["worst"], "excess": -0.2788}})


# 8 + 10. since: exact-half rounding matches JS; losing the full ranking is reported
def _snap_data(rank, would):
    return {"prices_asof": "2026-10-13", "top_n": 5, "rankings": [],
            "holdings": [{"ticker": "ASML", "in_universe": True, "current": {"rank": rank, "would_rank": would}}]}


def test_since_reports_price_only_switch():
    a = since.snapshot(_snap_data(4, None))
    b = {**since.snapshot(_snap_data(None, 4)), "asof": "2026-10-14"}
    assert b["price_only"] == ["ASML"] and a["price_only"] == []
    assert "ASML now ranked on price data only" in since.diff(a, b)["text"]
    c = {**since.snapshot(_snap_data(4, None)), "asof": "2026-10-15"}
    assert "ASML fully ranked again" in since.diff(b, c)["text"]
    old = {k: v for k, v in a.items() if k != "price_only"}          # snapshot from before round 50
    assert "price data only" not in since.diff(old, b)["text"]


@needs_node
def test_since_matches_js_on_exact_halves_and_price_only():
    block = _js_block("// ---- since", "// ---- end since ----")
    p = {"asof": "2026-10-12", "top": [], "ranks": {"ASML": 4}, "price_only": [], "pnl": None, "paper": 0.05, "alerts": 0}
    c = {"asof": "2026-10-13", "top": [], "ranks": {"ASML": 4}, "price_only": ["ASML"], "pnl": None,
         "paper": 0.0525, "alerts": 0}
    cases = [[p, c], [{**p, "paper": 0.0}, {**c, "paper": 0.0015}], [c, {**p, "asof": "2026-10-14"}]]
    data = _snap_data(None, 4)
    js = block + "\nconsole.log(JSON.stringify({d:%s.map(x=>diffSnapshots(x[0],x[1]).text), s:makeSnapshot(%s)}));" % (
        json.dumps(cases), json.dumps(data))
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out["d"] == [since.diff(a, b)["text"] for a, b in cases]
    assert out["s"] == since.snapshot(data)
    assert "+0.3 pts" in out["d"][0] or "+0.2 pts" in out["d"][0]     # whichever: both sides agree


# minor: series with repeated dates must not be packed (it lost data)
def test_pack_leaves_series_with_repeated_dates_alone():
    x = {"a": [["2026-01-01", 1], ["2026-01-01", 2]], "b": [["2026-01-02", 3]]}
    assert slim.unpack(slim.pack(x)) == x
    y = {"a": [["2026-01-01", 1], ["2026-01-02", 2]], "b": [["2026-01-01", 3], ["2026-01-02", 4]]}
    assert slim.unpack(slim.pack(y)) == y and "_d" in slim.pack(y)
