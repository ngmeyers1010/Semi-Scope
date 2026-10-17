"""Sanity tests: run with  python -m pytest tests  (no internet needed)."""
import pytest
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demo_data  # noqa: E402
from factors import score  # noqa: E402
from fundamentals import build_series  # noqa: E402

TICKERS = [f"T{i}" for i in range(12)]


def _data():
    return demo_data.generate(TICKERS, ["SPY", "SOXX"], "2013-03-01", seed=3)


def test_no_lookahead():
    """Scoring with ALL data must equal scoring with data truncated at that date."""
    all_series, px, _ = _data()
    for d in pd.to_datetime(["2016-06-01", "2020-03-02", "2023-09-01"]):
        d = px.index[px.index >= d][0]
        full, _ = score(all_series, px, d, TICKERS)
        cut_series = {t: {k: v[v["filed"] < d] for k, v in s.items()} for t, s in all_series.items()}
        cut, _ = score(cut_series, px.loc[:d], d, TICKERS)
        pd.testing.assert_series_equal(full["score"].sort_index(), cut["score"].sort_index())


def test_q4_derivation_and_restatements():
    rng = np.random.default_rng(0)
    facts, _, _ = demo_data._company(rng, 12, 2012, pd.Timestamp("2016-12-31"))
    s = build_series(facts)["revenue"]
    # every quarter present, consecutive ~91 days apart
    gaps = s["end"].diff().dt.days.dropna()
    assert gaps.between(85, 95).all(), gaps.tolist()
    # Q4 derived = annual - Q1..Q3 (original, not restated, values)
    annual = [f for f in facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"] if f["form"] == "10-K"][0]
    fy_end = pd.Timestamp(annual["end"])
    yr = s[(s["end"] > fy_end - pd.Timedelta(days=360)) & (s["end"] <= fy_end)]
    assert len(yr) == 4
    assert abs(yr["val"].sum() - annual["val"]) < 1


def test_scores_rank_complete():
    all_series, px, _ = _data()
    ranked, _ = score(all_series, px, px.index[-1], TICKERS)
    assert ranked["score"].notna().sum() >= 8
    assert list(ranked["rank"].dropna().sort_values()) == list(range(1, len(ranked["rank"].dropna()) + 1))


def test_rebalance_dates_are_first_trading_day_only():
    from backtest import rebalance_dates
    idx = pd.bdate_range("2026-08-25", "2026-09-30")
    # starting mid-September must NOT treat Sep 2 as a rebalance
    assert rebalance_dates(idx, "2026-09-02") == []
    assert rebalance_dates(idx, "2026-08-01") == [pd.Timestamp("2026-09-01")]


def test_watchlist_does_not_move_universe_scores():
    from factors import score_outsiders
    all_series, px, _ = _data()
    uni, extra = TICKERS[:9], TICKERS[9:]
    d = px.index[-1]
    ranked, _ = score(all_series, px, d, uni)
    out, _ = score_outsiders(all_series, px, d, ranked, extra)
    ranked2, _ = score(all_series, px, d, uni)
    pd.testing.assert_series_equal(ranked["score"], ranked2["score"])
    assert out["would_rank"].dropna().between(1, len(uni) + 1).all()


def test_sales_yield_is_split_safe():
    """A 10:1 split must not make a stock look 10x cheaper or pricier."""
    import factors
    from factors import sales_yield
    all_series, px, _, close, splits = demo_data.generate(
        TICKERS, ["SPY", "SOXX"], "2013-03-01", seed=3, return_market=True)
    factors.MARKET["close"] = close
    split_ticker = TICKERS[0]  # every 4th demo stock splits 10:1 in June 2024
    sd = splits[split_ticker][splits[split_ticker] > 0].index[0]
    before = px.index[px.index < sd - pd.Timedelta(days=60)][-1]
    after = px.index[px.index > sd + pd.Timedelta(days=60)][0]
    y0 = sales_yield(all_series[split_ticker], before, close.loc[before, split_ticker])
    y1 = sales_yield(all_series[split_ticker], after, close.loc[after, split_ticker])
    assert np.isfinite(y0) and np.isfinite(y1)
    assert 0.33 < y1 / y0 < 3, (y0, y1)  # a broken split would be ~10x off
    factors.MARKET["close"] = None


@pytest.mark.slow
def test_robustness_baseline_matches_backtest():
    import robustness
    from backtest import run_backtest, stats
    all_series, px, bench = _data()
    curves, _, _ = run_backtest(all_series, px, bench, TICKERS, "2015-03-01")
    rows = robustness.run(all_series, px, bench, TICKERS, start="2015-03-01")
    assert rows[0]["name"] == "Baseline"
    assert abs(rows[0]["cagr"] - stats(curves["strategy"])["cagr"]) < 1e-6


def test_ytd_cash_flow_decumulation():
    """Cash flow arrives as 3/6/9/12-month YTD totals; quarters must be recovered."""
    from fundamentals import _ytd_quarters
    q = [100.0, 120.0, 90.0, 150.0]
    ytd = np.cumsum(q)
    ends = ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"]
    filed = ["2024-05-01", "2024-08-01", "2024-11-01", "2025-02-20"]
    facts = {"facts": {"us-gaap": {"NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
        {"start": "2024-01-01", "end": e, "val": v, "filed": f, "form": "10-Q" if i < 3 else "10-K"}
        for i, (e, v, f) in enumerate(zip(ends, ytd, filed))]}}}}}
    s = _ytd_quarters(facts, ["NetCashProvidedByUsedInOperatingActivities"])
    assert s["val"].round(6).tolist() == q
    # each quarter is only known once its YTD report was filed
    assert s["filed"].dt.strftime("%Y-%m-%d").tolist() == filed


def test_new_fundamentals_present():
    from factors import fundamental_factors
    all_series, px, _ = _data()
    t = next(iter(all_series))
    f = fundamental_factors(all_series[t], px.index[-1], px[t].iloc[-1])
    for k in ("op_margin_change", "fcf_margin", "rd_intensity", "capex_intensity"):
        assert np.isfinite(f[k]), k
    assert 0.1 < f["rd_intensity"] < 0.2  # demo R&D is 15% of sales


def _snap(mode="live", ranks=None, top=None, ic=None, entries=None):
    ranks = ranks or {}
    return {
        "mode": mode, "top_n": 5, "universe_size": 20,
        "rankings": [{"ticker": t, "rank": r} for t, r in (top or {}).items()],
        "holdings": [{"ticker": t, "current": {"rank": r}} for t, r in ranks.items()],
        "research": {"ic": {"score": [["d", v] for v in (ic or [])]}},
        "paper": {"entries": entries or []},
    }


def test_alerts_only_fire_on_changes():
    import alerts
    a = _snap(ranks={"MU": 3, "AMD": 8}, top={"MU": 3, "X": 1}, ic=[0.1, 0.1, 0.1, 0.1])
    assert alerts.compute(a, a) == []
    b = _snap(ranks={"MU": 18, "AMD": 8}, top={"Y": 2, "X": 1}, ic=[0.1, -0.2, -0.2, -0.2])
    out = alerts.compute(a, b)
    kinds = sorted(x["kind"] for x in out)
    assert kinds == ["holding", "model", "top", "top"], out
    mu = next(x for x in out if x["kind"] == "holding")
    assert "MU" in mu["text"] and "Top pick → Bottom quarter" in mu["text"] and mu["level"] == "warning"
    # model warning doesn't repeat once already negative
    assert not [x for x in alerts.compute(b, b) if x["kind"] == "model"]


def test_alerts_new_paper_picks_and_mode_switch():
    import alerts
    e = {"date": "2026-12-01", "reason": "quarterly rebalance", "picks": ["MU", "AMD"]}
    out = alerts.compute(_snap(mode="demo"), _snap(entries=[e]))
    assert [x["kind"] for x in out] == ["paper", "system"]
    assert alerts.compute(None, _snap())== []
    assert alerts.signal(None, 20, 5) == "Not ranked" and alerts.signal(5, 20, 5) == "Top pick"


def test_cycle_phase_classification():
    from cycle import classify
    assert classify(0.20, 0.7) == "Upswing"
    assert classify(0.20, 0.3) == "Late cycle"
    assert classify(-0.10, 0.3) == "Downturn"
    assert classify(-0.10, 0.6) == "Recovery"
    assert classify(float("nan"), 0.5) == "Unknown"


def test_cycle_build_shapes():
    import cycle
    all_series, px, _ = _data()
    ranked, _ = score(all_series, px, px.index[-1], TICKERS)
    uni = {t: {"group": "A" if i % 2 else "B"} for i, t in enumerate(TICKERS)}
    c = cycle.build(ranked, all_series, uni, px.index[-1])
    assert c["phase"] in cycle.PHASES
    assert {g["group"] for g in c["groups"]} == {"A", "B"}
    assert 1 <= len(c["growth_history"]) <= 12


def _q(vals, start="2023-03-31", filed_lag=35):
    ends = pd.date_range(start, periods=len(vals), freq="QE")
    return pd.DataFrame({"end": ends, "val": vals, "filed": ends + pd.Timedelta(days=filed_lag)})


def test_data_health_flags():
    from data_health import company_health
    good = {"revenue": _q([100, 105, 110, 120, 125, 130, 140, 150]),
            "cogs": _q([50, 52, 55, 60, 62, 65, 70, 75]),
            "inventory": _q([30] * 8), "shares": _q([10] * 8)}
    asof = pd.Timestamp("2025-03-15")
    h = company_health(good, asof)
    assert h["status"] == "ok" and not h["flags"] and h["coverage"]["revenue"] == 8

    bad = dict(good)
    bad["revenue"] = _q([100, 105, 110, 500, 125, -5, 140, 150])   # jump + negative
    bad["cogs"] = _q([50, 52, 55, 60, 62, 65, 139, 75])             # GM ~0.7% fine, then ok
    bad["shares"] = _q([10, 10, 10, 40, 40, 40, 40, 40])            # unexplained 4x
    flags = " ".join(company_health(bad, asof)["flags"])
    assert "Negative revenue" in flags and "Revenue jumped" in flags and "Share count" in flags

    late = company_health(good, pd.Timestamp("2026-01-01"))
    assert late["stale"] and late["status"] == "warn"
    assert company_health(None, asof)["status"] == "missing"


def test_stale_holding_alert():
    import alerts
    base = _snap(ranks={"MU": 3})
    a = dict(base, data_health={"rows": [{"ticker": "MU", "stale": False}], "stale_days": 120})
    b = dict(base, data_health={"rows": [{"ticker": "MU", "stale": True}], "stale_days": 120})
    out = alerts.compute(a, b)
    assert [x["kind"] for x in out] == ["data"] and "MU" in out[0]["text"]


def test_digest_sections():
    import digest
    d = _snap(ranks={"MU": 2, "AAPL": 19}, top={"MU": 2, "X": 1}, ic=[0.1, -0.2, -0.2, -0.3])
    d.update(prices_asof="2026-12-01", top_n=5, universe_size=20,
             rankings=[{"ticker": "X", "rank": 1, "score": 1.2}, {"ticker": "MU", "rank": 2, "score": 0.9}],
             alerts=[{"kind": "top", "level": "info", "text": "MU entered the top 5"}],
             cycle={"phase": "Upswing", "phase_text": "t", "median_growth": 0.1, "accel_share": 0.6},
             paper={"entries": [{"date": "2026-10-15"}], "stats": {"paper": {"total_return": 0.08},
                                                                     "SPY": {"total_return": 0.03}}})
    for h in d["holdings"]:
        h["in_universe"] = True
    out = digest.build(d, write=False)
    md = out["markdown"]
    assert "Cycle: Upswing" in md and "X (+1.20), MU (+0.90)" in md and "MU entered the top 5" in md
    assert "MU: Top pick (#2/20)" in md and "AAPL: Bottom quarter (#19/20)" in md
    assert "ahead by 5.0 pts" in md and "NOT been working" in md


def test_attribution_sums_to_quarter_return():
    import attribution
    from backtest import run_backtest
    all_series, px, bench = _data()
    _, quarters, _ = run_backtest(all_series, px, bench, TICKERS, "2015-03-01")
    meta = {t: {"group": "A" if i % 2 else "B"} for i, t in enumerate(TICKERS)}
    a = attribution.build(quarters, meta)
    for q in quarters:
        if any(pd.isna(v) for v in q["pick_returns"].values()):
            continue
        assert abs(sum(q["contrib"].values()) - q["return"]) < 1e-4, q["date"]  # stored values rounded to 5 dp
        assert abs(sum(q["contrib_groups"].values()) - q["return"]) < 1e-4
    assert abs(sum(r["contrib"] for r in a["stocks"]) - a["total_contrib"]) < 1e-9
    assert {g["group"] for g in a["groups"]} <= {"A", "B"}


def test_buffer_sell_rule():
    import robustness
    from config import FACTORS
    all_series, px, _ = _data()
    w = {f: c["weight"] for f, c in FACTORS.items() if c["weight"] > 0}
    dates = [d for d in robustness.month_starts(px.index, "2016-03-01") if d.month in (3, 6, 9, 12)]
    ranked = [(d, robustness.composite(score(all_series, px, d, TICKERS)[1], w)) for d in dates]
    buf = robustness.buffer_schedule(ranked, n=3, buffer=6)
    for (d, r), (_, picks) in zip(ranked, buf):
        assert len(picks) == 3
        assert set(picks) <= set(r.index[:6]), d          # never holds anything ranked worse than 6
    base = [(d, list(r.index[:3])) for d, r in ranked]
    ib, ibuf = {}, {}
    robustness.simulate(px, base, info=ib)
    robustness.simulate(px, buf, info=ibuf)
    assert ibuf["turnover"] <= ib["turnover"] + 1e-12
    assert ibuf["cost_drag"] <= ib["cost_drag"] + 1e-12


def test_next_filing_estimate():
    import filings
    # a company that files ~Feb 20 (10-K), ~May 5, ~Aug 5, ~Nov 5 every year
    dates = []
    for y in (2024, 2025, 2026):
        for md in ("02-20", "05-05", "08-05", "11-05"):
            d = pd.Timestamp(f"{y}-{md}")
            if d < pd.Timestamp("2026-10-14"):
                dates.append(d)
    nxt = filings.estimate_next(dates, "2026-10-14")
    assert abs((nxt - pd.Timestamp("2026-11-05")).days) <= 3, nxt
    # right after a filing, the next one is a quarter away, not the one just made
    nxt2 = filings.estimate_next(dates + [pd.Timestamp("2026-11-04")], "2026-11-10")
    assert abs((nxt2 - pd.Timestamp("2027-02-20")).days) <= 3, nxt2
    # fallback: no year of history -> last + median gap
    short = [pd.Timestamp("2026-02-01"), pd.Timestamp("2026-05-02"), pd.Timestamp("2026-08-01")]
    nxt3 = filings.estimate_next(short, "2026-08-10")
    assert 80 <= (nxt3 - pd.Timestamp("2026-08-01")).days <= 100
    assert filings.estimate_next([], "2026-01-01") is None
