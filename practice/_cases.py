"""Per-exercise data for check.py: the exercise list, study plan, skills, the hint ladder, and
the inputs each exercise is checked on (built from the same simulated data every time)."""
from __future__ import annotations

import types
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).parent


EXERCISES = {
    1: ("ex01_last_price", "last_price"), 2: ("ex02_daily_returns", "daily_returns"),
    3: ("ex03_total_return", "total_return"), 4: ("ex04_best_stock", "best_stock"),
    5: ("ex05_annual_vol", "annual_vol"), 6: ("ex06_max_drawdown", "max_drawdown"),
    7: ("ex07_monthly_returns", "monthly_returns"), 8: ("ex08_group_median", "group_median"),
    9: ("ex09_gross_margin", "gross_margin"), 10: ("ex10_momentum_z", "momentum_z"),
    11: ("ex11_mini_backtest", "mini_backtest"), 12: ("ex12_write_a_test", "check_max_drawdown"),
    13: ("ex13_z_move", "z_move"), 14: ("ex14_fifo_lots", "fifo_gains"),
    15: ("ex15_t_test", "edge_stats"), 16: ("ex16_inverse_vol", "inverse_vol_weights"),
    17: ("ex17_own_percentile", "own_percentile"), 18: ("ex18_fake_the_network", "latest_close"),
    19: ("ex19_rolling_excess", "rolling_excess"), 20: ("ex20_dedupe_log", "merge_log"),
    21: ("ex21_reproduce_the_score", "reproduce_score"),
    22: ("ex22_signal_decay", "excess_at"),
    23: ("ex23_explain_a_score_change", "explain_change"),
    24: ("ex24_up_down_capture", "up_down_capture"),
    25: ("ex25_drawdown_episodes", "episodes"),
    26: ("ex26_bootstrap_a_range", "block_paths"),
    27: ("ex27_catch_a_bad_number", "flag_jumps"),
    28: ("ex28_readable_colours", "luminance"),
    29: ("ex29_what_changed_this_week", "week_diff"),
    30: ("ex30_stayers_vs_new", "classify"),
    31: ("ex31_beta_and_a_bad_day", "beta"),
    32: ("ex32_sharpe_and_effective_bets", "sharpe"),
    33: ("ex33_paper_portfolio_return", "paper_return"),
}


# Study order (practice/PLAN.md lists the same sessions in the same order; a test checks it).
PLAN = [
    ("Week 1: pandas basics", [1, 2, 3, 4, 7]),
    ("Week 2: risk, and checking your own work", [5, 6, 12, 9, 8]),
    ("Week 3: factors and backtests", [10, 13, 11, 16, 14]),
    ("Week 4: is the edge real?", [15, 17, 19, 22, 24]),
    ("Week 5: rebuild the dashboard's own logic", [18, 20, 21, 23, 25]),
    ("Week 6: bonus", [26, 27, 28, 29, 30, 31, 32, 33]),
]


PLAN_ORDER = [n for _, ns in PLAN for n in ns]


SKILLS = {
    1: "pick a column, drop missing values, take the last row", 2: ".pct_change() for daily returns",
    3: "slice by date with .loc", 4: "math on whole rows, .idxmax()", 5: ".std() and annualizing with sqrt(252)",
    6: ".cummax(): the running high", 7: "groupby by month", 8: "groupby by category, median vs mean",
    9: "combine two tables by date", 10: "your first factor and a z-score", 11: "a backtest with no peeking",
    12: "write a test that catches bugs", 13: "is today's move unusual?", 14: "FIFO tax lots with a loop",
    15: "t-stat and sample size", 16: "inverse-volatility weights", 17: "boolean masks and percentiles",
    18: "test with a fake download", 19: "rolling 1-year excess, compounding", 20: "dedupe a log with a set",
    21: "reproduce the dashboard's score", 22: "signal decay and the next trading day",
    23: "explain a score change exactly", 24: "up/down capture with masks", 25: "drawdown episodes",
    26: "bootstrap a range of outcomes", 27: "catch a bad SEC number (median of earlier quarters)",
    28: "readable colours (WCAG contrast)",
    29: "what changed this week (two dicts, tuple sort keys)",
    30: "stayers vs new picks (pairing quarters, a per-quarter t-stat)",
    31: "beta and a bad day (covariance, a percentile as risk)",
    32: "Sharpe and effective bets (annualizing, a covariance matrix)",
    33: "the paper portfolio's return (holding periods, drift, trading costs)",
}


LABEL_PCTS = [None, 0, 9.9, 10, 24.9, 25, 50, 75, 75.1, 90, 90.1, 100]


@lru_cache(maxsize=1)
def data():
    """Simulated SemiScope data: (all_series, px). Same every time (fixed seed)."""
    import demo_data
    tickers = ["MU", "AMD", "NVDA", "INTC", "AMAT", "LRCX", "TXN", "ADI"]
    all_series, px, _ = demo_data.generate(tickers, ["SPY", "SOXX"], "2016-03-01", seed=11)
    return all_series, px[tickers]


def _table():
    groups = {"MU": "Memory", "AMD": "Compute", "NVDA": "Compute", "INTC": "Compute",
              "AMAT": "Equipment", "LRCX": "Equipment", "TXN": "Analog", "ADI": "Analog"}
    _, px = data()
    g = px.iloc[-1] / px.iloc[-253] - 1
    return pd.DataFrame({"ticker": list(groups), "group": list(groups.values()),
                         "rev_growth": [round(float(g[t]), 4) for t in groups]})


def _args(n):
    all_series, px = data()
    s = all_series["MU"]
    return {
        1: [(px, "MU"), (px, "NVDA")], 2: [(px,)], 3: [(px, "AMD", "2020-01-01", "2021-06-30")],
        4: [(px,), (px, 63)], 5: [(px, "INTC"), (px, "MU", 252)],
        6: [(px["NVDA"].dropna(),), (pd.Series([100, 150, 75, 120.0]),)],
        7: [(px, "AMAT")], 8: [(_table(),)], 9: [(s["revenue"], s["cogs"])], 10: [(px,)],
        11: [(px, "2021-03-01", "2021-06-01"), (px, "2022-09-01", "2023-03-01", 2)],
        13: [(px["MU"],), (px["NVDA"], 5)],
        14: [([("2024-01-02", 10, 50.0), ("2025-03-01", 5, 80.0)], 12, 100.0, "2025-06-01"),
             ([("2024-06-01", 3, 20.0)], 3, 15.0, "2025-06-01"),          # exactly 365 days: short-term
             ([("2024-06-01", 3, 20.0), ("2024-07-01", 4, 30.0)], 5, 25.0, "2025-06-03")],
        15: [([0.02, -0.01, 0.03, 0.01, 0.00, 0.04],), ([-0.01, 0.02, -0.03],)],
        16: [(px, ["MU", "NVDA", "TXN"]), (px, ["AMD", "ADI"], 21)],
        17: [(_weekly_ps(), float(_weekly_ps().dropna().iloc[-1])), (pd.Series([2, 3, 3, 3, 5.0]), 3.0),
             (pd.Series([1.0, np.nan, 2.0, np.nan, 4.0]), 3.0)],
        18: [("NVDA", _fake_download()), ("MU", _fake_download()), ("NVDAA", _fake_download()),
             ("ZZZZ", _fake_download())],
        19: [(px["NVDA"].dropna(), px["MU"].reindex(px["NVDA"].dropna().index))],
        20: [(_log_old(), [{"text": "MU entered the top 5"}, {"text": "AMD hit a new 52-week high"}], "2026-10-13"),
             (_log_old(), [], "2026-10-14"),
             ([{"date": "2026-10-1%d" % (i % 3), "text": f"alert {i % 20}"} for i in range(60)],
              [{"text": "x"}, {"text": "x"}], "2026-10-15")],
        21: [(_score_data(), "AAA"), (_score_data(), "BBB")] + _real_score_args(),
        22: _decay_args(),
        24: _capture_args(),
        25: _dd_args(),
        26: _boot_args(),
        27: [(list(v),) for v in EX27_CASES],
        28: [(c,) for c in EX28_COLOURS],
        29: EX29_CASES + _real_week_args(),
        30: [(q,) for q in EX30_QUARTERS] + _real_quarters_args(),
        31: _beta_args(),
        32: _sharpe_args(),
        33: _paper_args(),
        23: [({"growth": 0.0, "margin": 0.5, "mom": 0.1}, {"growth": 1.0, "margin": 0.5, "mom": 0.1}, EX23_W),
             ({"growth": 0.4, "margin": None, "mom": -0.2, "off": 3.0}, {"growth": -0.6, "margin": 1.5, "mom": None, "off": 1.0}, EX23_W),
             ({"growth": 1.0, "margin": 1.0, "mom": None}, {"growth": 1.0, "margin": None, "mom": None}, EX23_W)],
    }[n]


EX23_W = {"growth": 2.0, "margin": 1.0, "mom": 1.0, "off": 0.0}


EX23_HEADLINES = [({"growth": 0.5, "margin": 0.0}, 0.5), ({"growth": 0.10, "margin": 0.125, "mom": 0.125}, 0.35),
                  ({"growth": -0.4, "margin": 0.25}, -0.15), ({"growth": 0.2, "margin": 0.1}, 0.4), ({}, 0.0),
                  ({"growth": -0.3, "mom": 0.05}, -0.25),
                  ({"growth": 0.4, "margin": -0.3, "mom": -0.3}, -0.2)]      # top factor points the other way


EX27_CASES = [
    [100, 105, 110, 110_000, 115, 120],          # a units error (1,000x)
    [10, 10, 10, 80, 10],                         # exactly 8x: counts (>=)
    [100, 100, 100_000, 100_000, 100_000, 100],   # an error repeated: don't compare with dropped quarters
    [100, 30, 100, 100, 700],                     # one low quarter: the median ignores it, the mean doesn't
    [100, 10, 100],                               # only 2 earlier quarters needed, not just the last one
    [100, 100, 100, 900, 900, 900, 900],          # judged on EARLIER quarters only
    [100, -5, 102, None, 0.05, 104, 0, 110],      # negatives, zero and a missing value
]


# Colours from the dashboard itself, light and dark mode, plus edge cases (3 digits, no '#',
# capitals, spaces, and one channel that sits right on the 0.03928 linearization cut).
EX28_COLOURS = ["#ffffff", "#000000", "#1f66c4", "#0b0b0b", "#f6f6f4", "#6b6a65", "#7a7974", "#5b9cec",
                "#ec7a7a", "#9a9990", "fff", "#0a0", "1F66C4", " #808080 ", "#0a0a0a", "#777777"]


EX28_PAIRS = [("#ffffff", "#000000"), ("#000000", "#ffffff"), ("#6b6a65", "#f6f6f4"), ("#7a7974", "#f6f6f4"),
              ("#1f66c4", "#f6f6f4"), ("#9a9990", "#1a1a18"), ("#ec7a7a", "#ec7a7a"), ("fff", "#0b0b0b")]


# Same cases as tests/test_week_diff.py (a test checks they match): nothing moved, one in/one out,
# ties, a new ticker, a removed ticker, more than 3 movers, and three "nothing to compare" cases.
EX29_CASES = [
    ({"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}, {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}, 3),
    ({"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}, {"D": 1, "A": 2, "B": 3, "C": 4, "F": 5, "E": 6}, 3),
    ({"A": 5, "B": 5, "C": 1, "D": 9}, {"A": 2, "B": 2, "C": 9, "D": 1}, 2),
    ({"A": 1, "B": 2, "C": 3}, {"A": 1, "NEW": 2, "B": 3, "C": 4}, 2),
    ({"A": 1, "GONE": 2, "B": 3}, {"A": 1, "B": 2}, 2),
    ({"Z": 10, "Y": 10, "X": 10, "W": 10, "V": 1}, {"Z": 6, "Y": 6, "X": 6, "W": 6, "V": 2}, 1),
    ({}, {"A": 1}, 5), (None, {"A": 1}, 5), ({"A": 1}, {}, 5),
]


def _real_week_args():
    """The dashboard's own week: docs/data.json's week_ranks vs today's rankings (skipped if missing)."""
    try:
        import json
        import slim
        d = slim.unpack(json.loads((HERE.parent / "docs" / "data.json").read_text()))
        cur = {r["ticker"]: int(r["rank"]) for r in d["rankings"] if r.get("rank") is not None}
        return [(dict(d["week_ranks"]["ranks"]), cur, int(d["top_n"]))] if d.get("week_ranks") else []
    except Exception:  # noqa: BLE001
        return []


@lru_cache(maxsize=1)
def _spy():
    """SPY from the same simulated market as data() (same seed)."""
    import demo_data
    tickers = ["MU", "AMD", "NVDA", "INTC", "AMAT", "LRCX", "TXN", "ADI"]
    _, _, bench = demo_data.generate(tickers, ["SPY", "SOXX"], "2016-03-01", seed=11)
    return bench["SPY"]


def _beta_args():
    """(stock returns, market returns): different date ranges, gaps on different days, and a calm
    stock, so lining up by date matters."""
    _, px = data()
    m = _spy().pct_change()
    mu = px["MU"].pct_change().iloc[-300:].copy()
    mu.iloc[[5, 40, 41, 200]] = np.nan                       # missing days the market does have
    m_gap = m.copy()
    m_gap.iloc[-150] = np.nan                                # and one the stock has
    calm = px["TXN"].pct_change().iloc[-252:]
    return [(mu, m_gap), (calm, m), (px["NVDA"].pct_change().dropna(), m.iloc[-500:])]


def _sharpe_args():
    """Daily curves: a stock (as a curve from 1.0), an equal-weight basket, and a flat-then-up line."""
    _, px = data()
    mu = px["MU"].dropna()
    basket = (1 + px[["AMD", "TXN", "ADI"]].pct_change().iloc[1:].mean(axis=1)).cumprod()
    idx = pd.bdate_range("2024-01-01", periods=60)
    steps = pd.Series(np.r_[np.ones(20), np.linspace(1, 1.3, 40)], index=idx)
    return [(mu / mu.iloc[0],), (basket,), (steps,)]


def _eb_args():
    _, px = data()
    r = px[["MU", "NVDA", "AMD", "TXN", "ADI"]].pct_change().iloc[-252:]
    r2 = px[["INTC", "AMAT", "LRCX"]].pct_change().iloc[-126:]
    return [(r, {"MU": 1, "NVDA": 1, "AMD": 1, "TXN": 1, "ADI": 1}),
            (r, {"MU": 0.4, "NVDA": 0.3, "TXN": 0.2, "ADI": 0.1}),          # AMD not held
            (r2, {"INTC": 5, "AMAT": 3, "LRCX": 2})]


def _paper_px():
    """6 tickers, 45 trading days; one has a missing day, one only starts trading later."""
    idx = pd.bdate_range("2026-01-05", periods=45)
    rng = np.random.default_rng(33)
    cols = {}
    for k, t in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]):
        cols[t] = 50 * (k + 1) * np.cumprod(1 + rng.normal(0.002 * (k - 2), 0.02, len(idx)))
    df = pd.DataFrame(cols, index=idx)
    df.iloc[17, 1] = np.nan                      # BBB: no price one day
    df.iloc[:10, 5] = np.nan                     # FFF: not trading for the first two weeks
    return df


def _paper_args():
    p = _paper_px()
    d = [x.strftime("%Y-%m-%d") for x in p.index]
    e3 = [{"date": d[2], "picks": ["AAA", "BBB", "CCC"]}, {"date": d[15], "picks": ["BBB", "DDD", "FFF"]},
          {"date": d[30], "picks": ["AAA", "EEE", "FFF", "ZZZ"]}]           # ZZZ: no prices at all
    e1 = [{"date": d[0], "picks": ["CCC", "DDD"]}]
    _, px = data()
    dd = [x.strftime("%Y-%m-%d") for x in px.index[-130:]]
    real = [{"date": dd[0], "picks": ["MU", "NVDA", "AMD"]}, {"date": dd[63], "picks": ["NVDA", "TXN", "ADI"]}]
    for e, prices in ((e3, p), (e1, p), (real, px)):          # like the real log (the answer ignores them)
        for x in e:
            x["entry_prices"] = {t: (float(prices[t].loc[:x["date"]].dropna().iloc[-1])
                                     if t in prices and prices[t].loc[:x["date"]].notna().any() else None)
                                 for t in x["picks"]}
    return [(e3, p), (e1, p), (e3, p, 25), (real, px)]


def _var_args():
    _, px = data()
    r = px[["MU", "NVDA", "TXN"]].pct_change().iloc[-504:].mean(axis=1)
    r2 = px["AMD"].pct_change().iloc[-252:].copy()
    r2.iloc[[3, 30]] = np.nan
    return [(r, 1000.0), (r2, 10000.0), (pd.Series([0.01, -0.02, np.nan, 0.03, -0.05, 0.0]), 500.0)]


def _q30(date, end, picks, rets, uni=0.0):
    return {"date": date, "end": end, "picks": picks, "pick_returns": dict(zip(picks, rets)), "universe": uni}


# The first set matches tests/test_streak_edge.py's known answer (a test checks it).
EX30_QUARTERS = [
    [_q30("q1", "q2", ["A", "B"], [0.10, 0.00]), _q30("q2", "q3", ["A", "C"], [0.05, 0.01], uni=0.01),
     _q30("q3", "q4", ["C", "D"], [0.03, -0.02])],
    [_q30("q1", "q2", ["A"], [0.1]), _q30("q3", "q4", ["A", "B"], [0.1, 0.2])],              # a gap: q1 ended on q2, not q3
    [_q30("a", "b", ["A", "B", "C"], [0.02, 0.01, -0.03], uni=0.005),
     _q30("b", "c", ["A", "B", "D"], [0.06, None, 0.01], uni=0.02),                         # B has no return: skip it
     _q30("c", "d", ["D", "E", "A"], [-0.04, 0.03, 0.00], uni=-0.01),
     _q30("e", "f", ["D", "F", "G"], [0.02, 0.05, -0.01], uni=0.01),                          # gap again: all new
     _q30("f", "g", ["D", "F", "H"], [0.01, 0.04, 0.02], uni=0.015),
     {"date": "g", "end": "h", "picks": [], "pick_returns": {}, "universe": 0.0}],             # no picks: skipped
]


def _real_quarters_args():
    try:
        import json
        import slim
        d = slim.unpack(json.loads((HERE.parent / "docs" / "data.json").read_text()))
        return [(d["backtest"]["quarters"],)]
    except Exception:  # noqa: BLE001
        return []


def _boot_args():
    """(returns, years, n_paths): constant returns, a short history where the LAST block matters,
    and backtest-like quarterly returns from the simulated prices."""
    _, px = data()
    q = px.resample("QE").last().pct_change().dropna(how="all").mean(axis=1)
    return [([0.02] * 10, 1, 50), ([0.10, -0.05, 0.03, 0.08, -0.20], 2, 400),
            ([round(float(x), 6) for x in q], 5, 2000)]


def _dd_curve(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def _dd_args():
    """A dip that recovers, one still open at the end, two dips plus a tiny wiggle, and real prices."""
    _, px = data()
    return [(_dd_curve([100, 110, 99, 88, 95, 110, 120]),),
            (_dd_curve([100, 120, 90, 80, 100]),),
            (_dd_curve([100, 90, 101, 100.5, 101.2, 130, 100, 131]),),
            (px["MU"].dropna().iloc[-500:],)]


def _dd_norm(eps):
    """Comparable form: dates as 'YYYY-MM-DD' strings, depth to 9 decimals."""
    out = []
    for e in eps:
        f = lambda d: None if d is None else str(pd.Timestamp(d).date())
        out.append({"peak": f(e.get("peak")), "trough": f(e.get("trough")), "recovery": f(e.get("recovery")),
                    "depth": round(float(e.get("depth")), 9)})
    return out


def _capture_args():
    """Real-ish daily prices (MU vs an equal-weight basket), plus a hand-made pair with a FLAT
    benchmark month in which the strategy jumps (it must not count as an up or down month)."""
    _, px = data()
    basket = px.mean(axis=1)
    idx = pd.bdate_range("2024-01-01", "2024-12-31")
    month = idx.to_period("M")
    b_m = {1: .04, 2: -.03, 3: 0.0, 4: .05, 5: -.02, 6: .03, 7: -.04, 8: .02, 9: 0.0, 10: -.01, 11: .06, 12: .01}
    s_m = {1: .05, 2: -.02, 3: .20, 4: .06, 5: -.01, 6: .02, 7: -.05, 8: .03, 9: -.15, 10: -.02, 11: .05, 12: .02}
    def daily(mret):        # one jump on each month's first trading day, flat otherwise
        r = pd.Series(0.0, index=idx)
        first = ~month.duplicated()
        for m, v in mret.items():
            r[first & (month.month == m)] = v
        return 100 * (1 + r).cumprod()
    return [(px["MU"].dropna(), basket), (px["NVDA"].dropna(), px["AMAT"].dropna()), (daily(s_m), daily(b_m))]


def _decay_args():
    """A date whose +1 month is a weekend, a 3-month case with a stock not listed yet,
    and a horizon past the end of the data (-> None)."""
    _, px = data()
    px = px.copy()
    idx = px.index
    weekend = next(d for d in idx[-400:] if (d + pd.DateOffset(months=1)) not in idx)
    px.loc[:idx[idx.get_loc(weekend) + 3], "INTC"] = np.nan        # "IPO" a few days after the start
    uni = list(px.columns)
    return [(px, weekend, ["MU", "NVDA"], uni, 1), (px, weekend, ["AMD"], uni, 3),
            (px, idx[-30], ["MU"], uni, 2)]


def _score_data():
    """Tiny data.json-like dict: a clipped value, a lower-is-better stat, a missing stat,
    and a weight-0 stat, so each rule matters."""
    return {
        "factors": {"growth": {"weight": 2.0, "sign": 1}, "margin": {"weight": 1.0, "sign": 1},
                    "vol": {"weight": 1.0, "sign": -1}, "unused": {"weight": 0.0, "sign": 1}},
        "z_stats": {"growth": {"lo": -0.1, "hi": 0.4, "mean": 0.1, "sd": 0.15},
                    "margin": {"lo": -0.05, "hi": 0.05, "mean": 0.0, "sd": 0.03},
                    "vol": {"lo": 0.2, "hi": 0.6, "mean": 0.35, "sd": 0.1},
                    "unused": {"lo": 0, "hi": 1, "mean": 0.5, "sd": 0.2}},
        "rankings": [{"ticker": "AAA", "raw": {"growth": 0.9, "margin": 0.02, "vol": 0.3, "unused": 1.0}},
                     {"ticker": "BBB", "raw": {"growth": 0.05, "margin": None, "vol": 0.55}}],
    }


def _real_data():
    import json
    import slim
    p = HERE.parent / "docs" / "data.json"
    try:
        d = slim.unpack(json.loads(p.read_text()))
    except (OSError, ValueError):
        return None
    return d if d.get("z_stats") and d.get("rankings") else None


def _real_score_args():
    d = _real_data()
    if not d:
        return []
    top = min((r for r in d["rankings"] if r.get("rank") is not None), key=lambda r: r["rank"])
    return [(d, top["ticker"])]


def _log_old():
    """A log with yesterday's entries, today's first run, and an old exact duplicate."""
    return [{"date": "2026-10-13", "text": "MU entered the top 5"},
            {"date": "2026-10-13", "text": "INTC left the top 5"},      # gone in the re-run
            {"date": "2026-10-12", "text": "NVDA fell 4%"},
            {"date": "2026-10-12", "text": "NVDA fell 4%"},              # duplicate
            {"date": "2026-10-09", "text": "New paper picks"}]


def _weekly_ps():
    """A P/S-like weekly series (MU's price / 40) with a few missing weeks, like real data."""
    _, px = data()
    w = (px["MU"].resample("W-FRI").last() / 40).iloc[-260:].copy()
    w.iloc[[3, 50, 120]] = np.nan
    return w


def _fake_download():
    """Pretend Yahoo: closes for the asked tickers. MU's last 2 days are missing, NVDAA is a typo."""
    _, px = data()
    def download(tickers):
        out = {}
        for t in tickers:
            if t == "NVDAA":
                out[t] = pd.Series(np.nan, index=px.index[-30:])
            elif t in px:
                s = px[t].iloc[-30:].copy()
                if t == "MU":
                    s.iloc[-2:] = np.nan
                out[t] = s
        return pd.DataFrame(out, index=px.index[-30:])
    return download


def _load(folder: Path, mod: str, fn: str):
    """Run the file fresh every time. Compiling the source ourselves (instead of importing) skips
    Python's __pycache__: a file saved twice in the same second with the same size would otherwise
    run the OLD version, and you'd be checking code you already changed."""
    path = folder / f"{mod}.py"
    m = types.ModuleType(f"{folder.name}_{mod}")
    m.__file__ = str(path)
    exec(compile(path.read_text(), str(path), "exec"), m.__dict__)
    return getattr(m, fn)


def _same(got, want) -> str | None:
    """None if equal (within rounding), else a short explanation."""
    if isinstance(want, list):
        if not isinstance(got, list):
            return f"expected a list, got {type(got).__name__}"
        if got != want:
            return (f"expected {len(want)} entries starting {want[:2]},\n    you returned {len(got)} "
                    f"starting {got[:2]}")
        return None
    if want is None:
        return None if got is None else f"expected None (no usable price), got {got!r}"
    if isinstance(want, tuple):
        if not isinstance(got, (tuple, list)) or len(got) != len(want):
            return f"expected a tuple of {len(want)} numbers like {tuple(round(x, 4) for x in want)}, got {got!r}"
        try:
            if all(abs(float(g) - float(w)) < 1e-9 for g, w in zip(got, want)):
                return None
        except (TypeError, ValueError):
            pass
        return f"expected {tuple(round(float(x), 4) for x in want)}, got {tuple(got)!r}"
    if isinstance(want, dict):
        if not isinstance(got, dict):
            return f"expected a dict, got {type(got).__name__}"
        if set(got) != set(want):
            return f"expected keys {sorted(want)}, got {sorted(got)}"
        bad = [k for k in want if not isinstance(got[k], (int, float)) or abs(got[k] - want[k]) > 1e-9]
        if bad:
            return "values differ: " + ", ".join(f"{k}: expected {want[k]:+.4f}, got {got[k]!r}" for k in bad[:3])
        return None
    if isinstance(want, (pd.Series, pd.DataFrame)):
        if not isinstance(got, type(want)):
            return f"expected a {type(want).__name__}, got {type(got).__name__}"
        if got.shape != want.shape:
            return f"expected shape {want.shape}, got {got.shape}"
        if isinstance(want, pd.DataFrame):
            if list(got.columns) != list(want.columns):
                return f"expected columns {list(want.columns)}, got {list(got.columns)}"
            num = [c for c in want.columns if pd.api.types.is_numeric_dtype(want[c])]
            got, want = got[num], want[num]
        try:
            g, w = got.to_numpy(dtype=float), want.to_numpy(dtype=float)
        except (ValueError, TypeError) as e:
            return f"couldn't compare values ({e})"
        if not np.allclose(g, w, equal_nan=True, rtol=1e-6, atol=1e-9):
            return f"values differ. First few expected:\n{want.head(3)}\n    you returned:\n{got.head(3)}"
        if isinstance(want, pd.Series) and list(map(str, got.index)) != list(map(str, want.index)):
            return f"right values but wrong labels/order. Expected index starts {list(want.index[:3])}"
        return None
    if isinstance(want, str):
        return None if got == want else f"expected {want!r}, got {got!r}"
    if got is None:
        return "your function returned None. Did you forget `return`?"
    try:
        return None if abs(float(got) - float(want)) < 1e-6 else f"expected {float(want):.6f}, got {float(got):.6f}"
    except (TypeError, ValueError):
        return f"expected a number like {want!r}, got {got!r}"


# ---- hint ladder: `check.py 5 --hint` gives stronger help each time, never the whole answer ----
# level 1: what to look up; level 2: the steps in plain words; level 3: the first line of the answer.
HINT_LADDER = {
    1: ("Look up: selecting a column (px[ticker]), .dropna(), .iloc.",
        "1) take the column for that ticker  2) drop the missing values  3) take the last item  4) make it a float"),
    2: ("Look up: .pct_change() and .iloc with a slice (iloc[1:]).",
        "1) percent change from the day before, for every column at once  2) drop the first row (it has no day before)"),
    3: ("Look up: .loc with a date range (px.loc['2020-01-01':'2021-06-30', ticker]).",
        "1) slice the dates for that ticker and drop missing values  2) last price / first price - 1"),
    4: ("Look up: .iloc[-1], .iloc[-days], .idxmax().",
        "1) today's prices / prices `days` rows ago - 1, for every stock  2) drop missing  3) the label of the biggest one"),
    5: ("Look up: .pct_change(), .tail(n), .std(), and why volatility scales with sqrt(time).",
        "1) daily returns, drop missing  2) keep the last `days` of them  3) their std  4) times sqrt(252)"),
    6: ("Look up: .cummax() (the running high) and .min().",
        "1) price / running high - 1 for every day (0 at a new high, negative below it)  2) the lowest of those"),
    7: ("Look up: .groupby() on s.index.to_period('M'), .last(), .pct_change().",
        "1) drop missing  2) group the days by month and keep each month's last price  3) percent change month to month  4) drop the first"),
    8: ("Look up: .groupby('group')['rev_growth'], .median(), .sort_values(ascending=False).",
        "1) group the rows by industry  2) median growth in each group  3) sort, biggest first"),
    9: ("Look up: DataFrame.merge(on='end', suffixes=...), new columns, .sort_values, .reset_index(drop=True).",
        "1) join revenue and cost on the quarter end date  2) gross margin = 1 - cost / revenue  3) keep end + margin, sorted by date"),
    10: ("Look up: .iloc[-21], .iloc[-126], z-score = (x - mean) / std.",
         "1) return from 126 days ago to 21 days ago, per stock  2) drop missing  3) z-score them  4) sort, highest first"),
    11: ("Look up: .loc[:date] (only the past), .nlargest(k), .loc[start:end, columns].",
         "1) keep only prices up to `start`  2) momentum from those  3) pick the top k  4) their average return from start to end"),
    12: ("Look up: assert, and what a buggy max_drawdown might return.",
         "1) make a small price Series where you know the drawdown by hand  2) assert fn(s) is close to it  3) add a case with no drawdown (0)"),
    13: ("Look up: .pct_change(), .iloc[-253:-1] (the year before today), np.sqrt.",
         "1) daily returns  2) their std over the year BEFORE today  3) today's n-day move  4) move / (std * sqrt(n))"),
    14: ("Look up: for loops over a list of tuples, min(), pd.Timestamp differences (.days).",
         "1) go through lots oldest first  2) take as many shares as you still need from each  3) gain = shares * (price - cost)  4) add it to long if held > 365 days, else short"),
    15: ("Look up: pd.Series, .mean(), .std() (sample sd), math.sqrt, math.ceil.",
         "1) mean and sd  2) t = mean / (sd / sqrt(n))  3) quarters needed for t = 2: ceil((2 * sd / mean) ** 2)"),
    16: ("Look up: .tail(n), .pct_change().std(), np.sqrt(252), dividing a Series by its .sum().",
         "1) recent daily returns for the tickers  2) annualized vol of each  3) 1 / vol  4) divide by the total so the weights add to 1"),
    17: ("Look up: .dropna(), comparisons that give True/False Series (h < today), and .sum() on them.",
         "1) drop missing  2) count values below today and equal to today  3) 100 * (below + half the equal) / count\n"
         "  Then valuation_label(pct): a chain of if pct < 10 / < 25 / <= 75 / <= 90."),
    18: ("Look up: passing a function as an argument (download), `in` on a DataFrame's columns, .empty.",
         "1) px = download([ticker])  2) not a column? return None  3) drop missing; empty? None  4) the last value as a float"),
    19: ("Look up: .shift(252), subtracting two Series (dates line up by themselves), .idxmin().",
         "1) 1-year return = p / p.shift(252) - 1, for both  2) strategy minus SPY, drop missing\n"
         "  Then worst_window(excess): the date of the lowest value (.idxmin()) and that value."),
    20: ("Look up: list comprehensions, dict(a, date=...) to copy with a change, and a set() of keys you've seen.",
         "1) drop old entries from today's date  2) new ones (stamped with today) first, then the rest\n"
         "  3) skip any (date, text) already seen  4) keep the first 40"),
    21: ("Look up: next(... for r in list if ...), dict .get(), min(max(x, lo), hi) for clipping.",
         "1) find the stock's row  2) for each factor with weight > 0 and a value: clip it, z = (x - mean) / sd * sign\n"
         "  3) score = sum(weight * z) / sum(weight) over the factors you used"),
    22: ("Look up: pd.Timestamp, pd.DateOffset(months=...), index.searchsorted, .loc[date, names].",
         "1) the first trading day on/after date + months (None if past the data)  2) picks' average return minus the universe's\n"
         "  Then overlap_t(values, months): t-stat divided by sqrt(months / 3) for overlapping windows."),
    23: ("Look up: dict comprehensions, sum(...) over a filtered dict, max(d, key=...).",
         "1) total weight of the factors each side actually has  2) for each factor: its share after minus its share before\n"
         "  Then headline(): the biggest contributor, if it explains at least half the move in the same direction."),
    24: ("Look up: .resample('ME').last(), pd.concat(axis=1), boolean masks (both['b'] > 0).",
         "1) monthly returns for both, side by side, drop missing  2) up months = benchmark > 0, down months = benchmark < 0\n"
         "  3) capture = average strategy return / average benchmark return, for each kind of month"),
    25: ("Look up: .cummax(), .items() to loop with dates, .idxmin() on a slice.",
         "1) underwater = curve / running high - 1  2) walk it: going below 0 starts an episode (peak = the day before)\n"
         "  3) back to 0 closes it; still under at the end -> recovery None  4) keep only the deep ones"),
    26: ("Look up: np.random.default_rng(seed), rng.integers, np.arange, fancy indexing r[idx], np.cumprod(axis=1).",
         "1) random block starts for every path  2) expand each start into `block` quarters in a row  3) 1000 * cumprod(1 + r)\n"
         "  Then summary(paths): 10th/50th/90th percentile of the last column and the share below 1000."),
    27: ("Look up: enumerate, statistics.median, a list of positions you've already dropped.",
         "1) skip missing / <= 0  2) median of up to 4 EARLIER kept quarters (need 2)  3) drop if 8x away either way\n"
         "  Then nonpositive(values): the positions that are <= 0."),
    28: ("Look up: str.lstrip('#'), int(x, 16), a formula from the WCAG spec, max/min.",
         "1) parse the hex, each channel / 255  2) linearize each  3) 0.2126 R + 0.7152 G + 0.0722 B\n"
         "  Then contrast(a, b) = (lighter + 0.05) / (darker + 0.05), and best_ink(bg): #0b0b0b or #ffffff."),
    29: ("Look up: dict .get() (None when missing), comprehensions with a filter, sorted(key=lambda t: (a, b, c)).",
         "1) None if either dict is empty  2) entered/left the top: rank <= top_n now vs before\n"
         "  3) climbs/drops among tickers in both, biggest first, ties by new rank then name  4) new = in cur, not prev"),
    33: ("Look up: pd.Timestamp, boolean masks on an index (daily.index > d), .reindex(columns=...).fillna(0), .cumprod(), Series.subtract(fill_value=0).",
         "1) for each entry: equal weights, charge cost on |new - old weights|  2) returns after the entry day up to the next entry\n"
         "  3) value *= sum(growth at the end * weight); keep the drifted weights for the next cost  4) value - 1"),
    32: ("Look up: .pct_change().dropna(), .mean(), .std(), np.sqrt, DataFrame.cov(), np.diag, the @ operator.",
         "1) daily returns  2) Sharpe = (mean * 252) / (std * sqrt(252))\n"
         "  Then effective_bets(r, w): weights in column order, sigma = sqrt(diag(cov)), (w @ sigma / sqrt(w @ cov @ w)) ** 2."),
    31: ("Look up: pd.concat([...], axis=1).dropna(), Series.cov(), Series.var(), np.percentile.",
         "1) line up the two return Series by date, drop days missing either  2) beta = cov(stock, market) / var(market)\n"
         "  Then var95(returns, amount): drop missing, -np.percentile(r, 5) * amount."),
    30: ("Look up: zip(xs, xs[1:]) to pair each quarter with the one before, set() membership, math.sqrt.",
         "1) for each quarter after the first: stayer if in the previous picks AND prev end == this date  2) excess = return - universe\n"
         "  Then gap_t(rows): per-quarter gap (mean stay - mean new), t = mean / (sample sd / sqrt(n))."),
}


# where the main function's first line leans on a helper you don't have, point at the helper's
# first line instead (it must still be a line of the solution file; a test checks)
LEVEL3_FROM = {28: 'h = str(hex_colour).strip().lstrip("#")'}
