"""
SemiScope pipeline: download data -> score -> backtest -> paper portfolio ->
write docs/data.json for the dashboard.

    python run.py          # live data (SEC + Yahoo)
    python run.py --demo   # synthetic data, no internet needed (for testing)
    python run.py --check  # download real data, print a health report, write nothing
"""
from __future__ import annotations

import argparse
import json
import os
import math
from pathlib import Path

import numpy as np
import pandas as pd

import factors
import alerts as alerts_mod
import paper
from backtest import run_backtest, stats
from research import report_card
import robustness
import cycle
import data_health
import digest
import attribution
import filings
import runlog
import orders
import mytrades
import quarterly
import confidence
import explain
import risk
import moves
import slim
import groups
import since
import mystocks
import sizing
import earnings_moves
import valuation
import steady
import earnings_cal
import weekly
import rebalance
import walkthrough
import decay
import concentration
import score_moves
import week_diff
import streak_edge
import capture
import sanity
import drawdowns
import outcomes
import foreign 
from config import MY_STOCKS, PAPER_START, OOS_START, BACKTEST_START, BENCHMARKS, FACTORS, MY_HOLDINGS, TOP_N, UNIVERSE, WATCHLIST
from factors import _known, score, score_outsiders
from fundamentals import build_series

ROOT = Path(__file__).parent
OUT = ROOT / "docs" / "data.json"


# ticker -> what went wrong while downloading (shown under Data health)
FAILURES: dict[str, str] = {}
MAX_MISSING_PRICES = 0.5   # abort if more than half the stocks have no prices


def load_live() -> tuple:
    """Returns all_series, px, bench, close, splits.

    Tolerates partial failures: a stock whose download fails is skipped and
    noted in FAILURES. Only a widespread outage (> half missing) stops the run,
    so a bad day never overwrites a good dashboard with an empty one."""
    import data_sources as ds
    allmeta = {**UNIVERSE, **WATCHLIST}
    tickers = list(allmeta)
    start = (pd.Timestamp(BACKTEST_START) - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
    px_all, close_all, splits_all = ds.prices(tickers + list(BENCHMARKS), start)
    no_px = [t for t in tickers if t not in px_all]
    for t in no_px:
        FAILURES[t] = "price download failed"
    if len(no_px) > MAX_MISSING_PRICES * len(tickers):
        raise SystemExit(f"ABORT: no prices for {len(no_px)}/{len(tickers)} stocks "
                         f"(Yahoo outage?). Dashboard left unchanged.")
    missing_bench = [b for b in BENCHMARKS if b not in px_all]
    if missing_bench:
        raise SystemExit(f"ABORT: no benchmark prices for {missing_bench}. Dashboard left unchanged.")
    try:
        ciks = ds.ticker_to_cik()
    except Exception as e:
        print(f"  ! SEC ticker list failed: {e} — scoring on price factors only")
        ciks = {}
    all_series = {}
    hand, problems = foreign.load()           # hand-entered foreign-filer quarters (state/foreign_fundamentals.csv)
    for p in problems:
        print(f"  ! foreign_fundamentals.csv: {p}")
    for t in tickers:
        if not allmeta[t]["sec"]:
            if t in hand:
                all_series[t] = hand[t]
            continue
        if t not in ciks:
            FAILURES.setdefault(t, "not found in SEC ticker list")
            continue
        try:
            sp = splits_all[t] if splits_all is not None and t in splits_all else None
            all_series[t] = build_series(ds.company_facts(ciks[t]), sp)
        except Exception as e:  # one bad company shouldn't kill the run
            FAILURES.setdefault(t, f"SEC download failed ({type(e).__name__})")
            print(f"  ! {t}: {e}")
    keep = [t for t in tickers if t in px_all]
    return (all_series, px_all[keep], px_all[[b for b in BENCHMARKS if b in px_all]],
            close_all[keep], splits_all)


def load_demo() -> tuple:
    """Same shape as load_live(), but synthetic data (no internet needed)."""
    import demo_data
    return demo_data.generate(list(UNIVERSE) + list(WATCHLIST), list(BENCHMARKS),
                              BACKTEST_START, return_market=True)


def market_still_open(last_bar, now=None) -> bool:
    """True while `last_bar` is today's unfinished price bar (New York time, before 4:10pm).

    Morning runs see a half-finished day. Anything that is recorded for good (the paper portfolio's
    picks and entry prices, the "since last run" baseline) must wait for the after-close run."""
    now = pd.Timestamp.now("America/New_York") if now is None else pd.Timestamp(now)
    now = now.tz_localize("America/New_York") if now.tzinfo is None else now.tz_convert("America/New_York")
    same_day = pd.Timestamp(last_bar).normalize() == now.tz_localize(None).normalize()
    return bool(same_day and now.hour * 60 + now.minute < 16 * 60 + 10)


def _clean(x):
    """Make numpy/pandas values JSON-safe (NaN -> null, rounded floats)."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if math.isnan(x) or math.isinf(x) else round(float(x), 5)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, pd.Timestamp):
        return x.strftime("%Y-%m-%d")
    return x


def _curve(s: pd.Series, step: str = "W-FRI") -> list[list]:
    """Downsample an equity curve to [[date, value], ...] for the dashboard."""
    s = s.resample(step).last().dropna()
    return [[d.strftime("%Y-%m-%d"), round(float(v), 4)] for d, v in s.items()]


def _ratio_near(s: pd.DataFrame | None, end: pd.Timestamp, denom: float, tol: int = 20) -> float | None:
    """Value of s for the quarter ending near `end`, divided by denom."""
    if s is None or s.empty or not denom:
        return None
    m = s[(s["end"] - end).abs().dt.days <= tol]["val"]
    return float(m.iloc[0]) / denom if len(m) else None


def company_history(series: dict, asof, n: int = 12) -> list[dict]:
    """Last n quarters of revenue, gross margin, inventory days for the dashboard."""
    rev = _known(series.get("revenue"), asof)
    if rev is None or rev.empty:
        return []
    cogs = series.get("cogs")
    inv = series.get("inventory")
    opi = series.get("opinc")
    out = []
    for _, r in rev.tail(n).iterrows():
        c = cogs[(cogs["end"] - r["end"]).abs().dt.days <= 20]["val"] if cogs is not None and not cogs.empty else []
        i = inv[(inv["end"] - r["end"]).abs().dt.days <= 10]["val"] if inv is not None and not inv.empty else []
        c = float(c.iloc[0]) if len(c) else None
        i = float(i.iloc[0]) if len(i) else None
        out.append({"q": r["end"].strftime("%Y-%m-%d"), "rev": float(r["val"]),
                    "gm": (1 - c / r["val"]) if c and r["val"] else None,
                    "dio": (i / c * 91) if i and c else None,
                    "om": _ratio_near(opi, r["end"], r["val"])})
    return out


def research_oos(ic_series, curves):
    """Out-of-sample split of the report card + backtest (see research.oos_check)."""
    from research import oos_check
    return oos_check(ic_series, curves, OOS_START, {f: c["weight"] for f, c in FACTORS.items()},
                     {f: c["label"] for f, c in FACTORS.items()})


def check(all_series, px, close, demo: bool = False) -> int:
    """Print a plain-English report on the downloaded data. Returns an exit code
    (0 = fine to run, 1 = something serious). Writes nothing."""
    allmeta = {**UNIVERSE, **WATCHLIST}
    asof = px.index[-1]
    print(f"\nDATA CHECK ({'demo' if demo else 'live'}) — prices through {asof.date()}")
    stale_px = (asof - px.apply(lambda c: c.last_valid_index())).dt.days
    print(f"{'ticker':6s} {'px days':>8s} {'last px':>10s} {'qtrs rev':>8s} {'latest qtr':>10s}  notes")
    problems = 0
    for t in allmeta:
        if t not in px:
            print(f"{t:6s} {'—':>8s} {'—':>10s} {'—':>8s} {'—':>10s}  !! {FAILURES.get(t, 'no prices')}")
            problems += 1
            continue
        s = all_series.get(t)
        rev = _known(s.get("revenue"), asof) if s else None
        h = data_health.company_health(s, asof)
        notes = list(h["flags"]) if allmeta[t]["sec"] else ["foreign filer: price factors only"]
        if t in FAILURES:
            notes.insert(0, "!! " + FAILURES[t])
        if stale_px[t] > 5:
            notes.insert(0, f"!! last price {stale_px[t]} days old")
        print(f"{t:6s} {px[t].notna().sum():8d} {px[t].dropna().iloc[-1]:10.2f} "
              f"{0 if rev is None else len(rev):8d} {h['latest_quarter'] or '—':>10s}  "
              f"{'; '.join(notes) or 'ok'}")
    tickers = [t for t in px.columns if t in UNIVERSE]
    ranked, _ = score(all_series, px, asof, tickers)
    n = int(ranked["score"].notna().sum())
    print(f"\n{n}/{len(UNIVERSE)} universe stocks scoreable; "
          f"avg {ranked['n_factors'].mean():.1f}/{len(FACTORS)} factors each")
    print(f"Top {TOP_N} today: {ranked['score'].dropna().head(TOP_N).index.tolist()}")
    if n < TOP_N * 2:
        print("!! Too few stocks scoreable — something is wrong with the data.")
        problems += 1
    print("RESULT:", "OK ✓" if problems == 0 else f"{problems} problem(s) — read the !! lines above")
    return 0 if n >= TOP_N * 2 else 1


def main() -> None:
    """Run the pipeline; log the run as ok or failed either way."""
    import sys
    demo = "--demo" in sys.argv
    if "--check" in sys.argv:
        return _main()
    log = runlog.DEMO_LOG if demo else runlog.LOG
    try:
        _main(log)
    except BaseException as e:  # includes SystemExit from a deliberate abort
        if isinstance(e, SystemExit) and e.code in (0, None):
            raise
        runlog.append("failed", log, skipped=list(FAILURES), mode="demo" if demo else "live",
                      error=f"{type(e).__name__}: {e}")
        raise


def _main(log=None) -> None:
    """Run the whole pipeline and write docs/data.json."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--check", action="store_true", help="download + report only, write nothing")
    ap.add_argument("--fast", action="store_true",
                    help="reuse the last run's robustness grid + walk-forward (the slowest part)")
    args = ap.parse_args()

    if args.check:
        all_series, px, _bench, close, _ = load_demo() if args.demo else load_live()
        factors.MARKET["close"] = close
        raise SystemExit(check(all_series, px, close, args.demo))

    prev = slim.unpack(json.loads(OUT.read_text())) if OUT.exists() else None

    print("Loading data…")
    all_series, px, bench, close, splits = load_demo() if args.demo else load_live()
    # drop impossible SEC numbers (units errors, negative revenue) before anything is scored
    all_series, SANITY = sanity.clean(all_series)
    if SANITY:
        print(f"  Sanity: {sum(len(v) for v in SANITY.values())} flag(s) on {', '.join(sorted(SANITY))}")
    factors.MARKET["close"] = close  # split-adjusted, non-dividend closes for market cap
    factors.MEMO = {}                 # share score() results across backtest/robustness/explain
    watch = [t for t in px.columns if t in WATCHLIST]
    tickers = [t for t in px.columns if t in UNIVERSE]
    asof = px.index[-1]
    print(f"  {len(tickers)} stocks, {len(all_series)} with SEC fundamentals, prices to {asof.date()}")

    print("Scoring today…")
    ranked, z = score(all_series, px, asof, tickers)
    outs = score_outsiders(all_series, px, asof, ranked, watch)

    print("Backtesting…")
    curves, quarters, panel = run_backtest(all_series, px, bench, tickers, BACKTEST_START)

    attrib = attribution.build(quarters, UNIVERSE)
    if attrib.get("helpers"):
        print(f"  Biggest contributors: {', '.join(r['ticker'] for r in attrib['helpers'][:3])}; "
              f"top-3 share of gains {attrib['top3_share'] or 0:.0%}")

    print("Factor report card…")
    card, ic_series = report_card(panel, list(FACTORS))
    for f, r in card.items():
        print(f"  {f:16s} IC {r['mean_ic']:+.3f}  t {r['ic_t']:+.2f}  hit {r['hit_rate']:.0%}  → {r['verdict']}")
    bt_stats = {k: stats(v) for k, v in curves.items()}
    beat_spy = [q["return"] > q["spy"] for q in quarters if not math.isnan(q["spy"])]

    oos = research_oos(ic_series, curves)
    print(f"  Out-of-sample: {oos['summary']}")

    print("Cycle view…")
    cyc = cycle.build(ranked, all_series, UNIVERSE, asof)
    print(f"  Phase: {cyc['phase']} — " + ", ".join(f"{g['group']} {g['phase']}" for g in cyc["groups"]))

    print("Data health…")
    nf = pd.concat([ranked[["n_factors"]]] + ([outs[0][["n_factors"]]] if len(outs[0]) else []))
    stale_px = mystocks.stale(tickers + watch, px, FAILURES)      # last bar(s) missing, e.g. a Yahoo hiccup
    health = data_health.build(all_series, tickers + watch, nf, asof, {**UNIVERSE, **WATCHLIST},
                               failures=FAILURES, stale_px=stale_px, sanity=SANITY)
    hs = health["summary"]
    print(f"  {hs['ok']} ok, {hs['warn']} flagged, {hs['missing']} no SEC data, {hs['stale']} stale")

    print("Robustness checks…")
    prev_rob = ((prev or {}).get("research") or {}).get("robustness")
    reuse = args.fast and prev_rob and prev.get("mode") == ("demo" if args.demo else "live")
    if reuse:
        robust = prev_rob
        print(f"  --fast: reusing robustness grid from {prev.get('prices_asof')} (full refresh runs on Fridays)")
    else:
        robust = robustness.run(all_series, px, bench, tickers)
    # start-date luck: the baseline from 12 different starts (reused on --fast, like the grid)
    prev_luck = ((prev or {}).get("research") or {}).get("start_luck")
    luck = prev_luck if reuse and prev_luck else robustness.start_luck(
        all_series, px, tickers, baseline_cagr=next((r["cagr"] for r in robust if r["name"] == "Baseline"), None))
    # signal decay: how the backtest's picks did 1-12 months later (reused on --fast)
    prev_decay = ((prev or {}).get("research") or {}).get("decay")
    dec = prev_decay if reuse and prev_decay else decay.build(px, quarters, tickers)
    if dec:
        print(f"  Signal decay: {dec['read']}")
    run_kind = "fast" if reuse else "full"
    for r in robust:
        print(f"  {r['name']:34s} CAGR {r['cagr']:+.1%}  Sharpe {r['sharpe']:.2f}  MaxDD {r['max_drawdown']:.0%}")

    print("Updating paper portfolio…")
    if args.demo:
        paper.STATE = ROOT / "state" / "paper_portfolio_demo.json"
    intraday = (not args.demo) and market_still_open(px.index[-1])
    if intraday:
        print("  market is still open: today's prices are intraday, so no paper picks or 'since' baseline are recorded this run")
    # an unfinished day is never recorded as an entry (the log is append-only); the after-close run does it
    state, new = paper.update(all_series, px.iloc[:-1] if intraday else px, tickers)
    if new:
        print(f"  recorded new picks for {[d.date() for d in new]}")
    perf = paper.performance(state, px, bench)

    print("My real trades…")
    trades_file = ROOT / "state" / ("my_trades_demo.csv" if args.demo else "my_trades.csv")
    if args.demo:
        mytrades.write_demo(trades_file, close)
    mine = mytrades.build(trades_file, close, px, bench, curves.get("strategy"),
                          # demo trades are written in already split-adjusted prices, so don't adjust them again
                          splits if isinstance(splits, pd.DataFrame) and not args.demo else None, demo=args.demo)
    print(f"  {mine['n_trades']} trades" + (f", P&L ${mine['totals']['pnl']:,.0f}" if mine.get("totals") else "")
          + (f", {len(mine['errors'])} problem(s)" if mine["errors"] else ""))

    filing_info = filings.build(all_series, tickers + watch, asof)
    earn = earnings_moves.build(all_series, px, tickers + watch, asof)
    vals = valuation.build(all_series, close, tickers + watch, asof)   # P/S vs its own 5-yr range

    def row_json(t, row, zt, meta):
        p = px[t].dropna()
        return {
            "ticker": t, "name": meta.get("name", t), "group": meta.get("group", ""),
            "rank": row.get("rank"), "would_rank": row.get("would_rank"),
            "score": row["score"], "n_factors": row["n_factors"],
            "raw": {f: row.get(f) for f in FACTORS},
            "z": {f: (zt.loc[t, f] if t in zt.index else None) for f in FACTORS},
            "gross_margin": row.get("gross_margin"), "inv_days": row.get("inv_days"),
            "latest_quarter": row.get("latest_quarter"),
            "valuation": vals.get(t),
            "last_price": float(p.iloc[-1]),
            "ret_3m": float(p.iloc[-1] / p.iloc[-63] - 1) if len(p) > 63 else None,
            # ~1 year of weekly closes for the compare chart (small: ~52 points)
            "px_1y": [[d.strftime("%Y-%m-%d"), round(float(v), 4)]
                      for d, v in p.iloc[-252:].iloc[::-5].iloc[::-1].items()],
            "history": company_history(all_series.get(t, {}), asof),
            "owned": t in MY_HOLDINGS,
            "stale_days": stale_px.get(t, 0),
            "filing": filing_info.get(t),
            "earnings": earn.get(t),
        }

    rankings = [row_json(t, r, z, UNIVERSE.get(t, {})) for t, r in ranked.iterrows()]
    out_raw, out_z = outs
    watchlist = [row_json(t, r, out_z, WATCHLIST.get(t, {})) for t, r in out_raw.iterrows()]

    # holdings: rank now + rank at each past rebalance (from the backtest panel)
    holdings = []
    for t in MY_HOLDINGS:
        hist = []
        for p in panel[-8:]:
            sc = p["score"].dropna()
            if t in sc.index:
                hist.append([p["date"].strftime("%Y-%m-%d"), int((sc > sc[t]).sum()) + 1, len(sc)])
        cur = next((r for r in rankings + watchlist if r["ticker"] == t), None)
        holdings.append({"ticker": t, "in_universe": t in UNIVERSE, "current": cur, "rank_history": hist})

    # inputs for the "Invest $X" calculator (the math itself runs in the browser)
    top = [r for r in rankings if r["rank"] is not None and not pd.isna(r["rank"])][:TOP_N]   # NaN = unscored
    hold_rank = {h["ticker"]: (h["current"] or {}).get("rank") or (h["current"] or {}).get("would_rank")
                 for h in holdings}
    hold_rank = {t: (int(r) if r is not None and not pd.isna(r) else None) for t, r in hold_rank.items()}
    n_ranked = int(ranked["score"].notna().sum())
    vol63 = sizing.trailing_vol(px, [r["ticker"] for r in top], asof)
    _f = lambda v: None if v is None or pd.isna(v) else float(v)
    order_inputs = {
        "picks": [{"ticker": r["ticker"], "name": r["name"], "rank": r["rank"], "price": r["last_price"],
                   "days_to_filing": (r["filing"] or {}).get("days_until"),
                   "earn_move": (r["earnings"] or {}).get("avg_abs"),
                   "vol_63d": _f(vol63.get(r["ticker"]))} for r in top],
        "earn_soon_days": orders.EARN_SOON,
        "compare": orders.compare([r["ticker"] for r in top], hold_rank, n_ranked),
        "holding_ranks": hold_rank, "n_ranked": n_ranked,
    }

    data = {
        "generated_at": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC"),
        "prices_asof": asof.strftime("%Y-%m-%d"),
        "mode": "demo" if args.demo else "live",
        "top_n": TOP_N,
        "factors": FACTORS,
        "benchmarks": BENCHMARKS,
        "rankings": rankings,
        "watchlist": watchlist,
        "cycle": cyc,
        "groups": groups.build(px[[t for t in tickers if t in px]], bench, {t: UNIVERSE[t] for t in tickers if t in UNIVERSE}, ranked),
        "upcoming_filings": filings.upcoming(filing_info),
        "data_health": health,
        "holdings": holdings,
        "order_plan_inputs": order_inputs,
        "my_trades": mine,
        "moves": moves.price_moves(px, list(dict.fromkeys(MY_HOLDINGS + [r["ticker"] for r in top] + tickers + watch)),
                                   avg_cost={p_["ticker"]: p_["avg_cost"] for p_ in (mine.get("positions") or [])
                                             if p_.get("avg_cost")}),
        "risk": risk.build(px, bench, [r["ticker"] for r in top], mine.get("positions")),
        "universe_size": int(ranked["score"].notna().sum()),
        "backtest": {
            "start": BACKTEST_START,
            "curves": {k: _curve(v) for k, v in curves.items()},
            "stats": bt_stats,
            "quarters": quarters,
            "attribution": attrib,
            "hit_rate_vs_spy": (sum(beat_spy) / len(beat_spy)) if beat_spy else None,
        },
        "research": {"card": card, "ic": ic_series, "robustness": robust, "oos": oos, "start_luck": luck, "decay": dec,
                     "streak_edge": streak_edge.build(quarters)},   # do stayers beat new picks?
        "paper": None if perf is None else {
            "curves": {k: _curve(v, "D") for k, v in perf["curves"].items()},
            "stats": perf["stats"], "holdings": perf["holdings"], "entries": perf["entries"],
            "attribution": attribution.paper(perf["entries"], px, {**UNIVERSE, **WATCHLIST}),
        },
    }
    # calendar-quarter returns for the quarterly report cards
    qcurves = {"strategy": curves.get("strategy")}
    if perf is not None:
        qcurves.update({"paper": perf["curves"].get("paper")})
    for b in ("SPY", "SOXX"):
        if b in bench:
            qcurves[b] = bench[b]
    data["quarter_returns"] = {k: quarterly.quarter_returns(v) for k, v in qcurves.items() if v is not None}
    # "is the edge real?": significance of quarterly excess returns over SPY
    qr, this_q = data["quarter_returns"], quarterly.quarter_of(asof)
    paper_excess = [qr["paper"][q] - qr["SPY"][q] for q in sorted(qr.get("paper", {}))
                    if q != this_q and q in qr.get("SPY", {})]   # completed quarters only
    data["confidence"] = confidence.build(quarters, paper_excess)
    # "is the edge steady?": rolling 1-year excess vs SPY, tracking error, information ratio
    data["steady"] = steady.build(curves, bench, (perf or {}).get("curves", {}).get("paper") if perf else None)
    data["drawdowns"] = drawdowns.build(curves, bench)
    data["outcomes"] = outcomes.build(quarters)          # "What could $1,000 become?" (bootstrap)
    data["capture"] = capture.build(curves, bench, (perf or {}).get("curves", {}).get("paper") if perf else None)
    # earnings season: next report date + typical earnings-day move for your stocks and the picks
    data["earnings_cal"] = earnings_cal.build(
        data["rankings"] + data["watchlist"], asof, set(MY_HOLDINGS),
        {r["ticker"] for r in data["rankings"] if r.get("rank") is not None and r["rank"] <= TOP_N})
    # your stock list (state/my_stocks.csv): problems to show, and a link to edit it on GitHub
    repo, branch = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_REF_NAME") or "main"
    mine_list = MY_STOCKS or {}
    data["my_stocks"] = {
        "from_file": MY_STOCKS is not None,
        "holdings": MY_HOLDINGS, "watch": mine_list.get("watch", []), "notes": mine_list.get("notes", {}),
        "problems": mine_list.get("problems", []),
        "unknown": mystocks.unknown(MY_HOLDINGS + mine_list.get("watch", []), FAILURES),
        "stale": mystocks.stale(MY_HOLDINGS + mine_list.get("watch", []), px, FAILURES),
        "edit_url": f"https://github.com/{repo}/edit/{branch}/state/my_stocks.csv" if repo else None,
    }
    # multiple-testing haircut: we tried every robustness variant, so the best-looking one is biased up
    strat = curves.get("strategy")
    if strat is not None:
        data["confidence"]["dsr"] = confidence.deflated_sharpe(
            strat.pct_change().dropna().tolist(), [row.get("sharpe") for row in robust])
    # the universe numbers behind every z-score, so the arithmetic can be shown (walkthrough.py)
    data["z_stats"] = {f: factors.z_stats(ranked[f]) for f, c in FACTORS.items() if c["weight"] > 0 and f in ranked}
    data = _clean(data)

    # why did scores move? (since the last run, and since the last quarterly rebalance)
    wts = {f: c["weight"] for f, c in FACTORS.items()}
    labels = {f: c["label"] for f, c in FACTORS.items()}
    cur_rows = data["rankings"] + data["watchlist"]
    ex = {"run": {}, "run_date": None, "rebalance": {}, "rebalance_date": None}
    if prev and prev.get("mode") == data["mode"] and prev.get("prices_asof") != data["prices_asof"]:
        ex["run"] = explain.explain_all(prev.get("rankings", []) + prev.get("watchlist", []), cur_rows, wts)
        ex["run_date"] = prev.get("prices_asof")
    if quarters:
        rb = pd.Timestamp(quarters[-1]["date"])
        rb_ranked, rb_z = score(all_series, px, rb, tickers)
        rb_rows = [{"ticker": t, "rank": (int(rb_ranked.loc[t, "rank"]) if pd.notna(rb_ranked.loc[t, "rank"]) else None),
                    "z": {f: (rb_z.loc[t, f] if t in rb_z.index else None) for f in FACTORS},
                    "raw": {f: rb_ranked.loc[t, f] if f in rb_ranked else None for f in FACTORS}} for t in rb_ranked.index]
        ex["rebalance"] = explain.explain_all(_clean(rb_rows), data["rankings"], wts)
        ex["rebalance_date"] = rb.strftime("%Y-%m-%d")
    ex["run_text"] = {t: explain.sentence(e, labels) for t, e in ex["run"].items() if abs(e["delta"]) > 1e-6}
    ex["rebalance_text"] = {t: explain.sentence(e, labels) for t, e in ex["rebalance"].items() if abs(e["delta"]) > 1e-6}
    data["explain"] = _clean(ex)
    # the few biggest score moves since the last run, each with the stat that caused it
    data["score_moves"] = _clean(score_moves.build(ex["run"], labels))
    # next-rebalance preview: drift since the last entry, and what would change if it were today
    last_px = {t: float(px[t].dropna().iloc[-1]) for t in px.columns if px[t].notna().any()}
    data["rebalance"] = _clean(rebalance.preview((state.get("entries") or [None])[-1], last_px,
                                                 ranked["score"].dropna().index.tolist(), asof))
    # ranks 5 trading days ago, for "What changed since last week" (Rankings tab)
    # ...and 10, 15, 20 days ago too, for "N weeks in the top" streaks (oldest first; last = week_ranks)
    data["rank_history"] = week_diff.history(lambda d: score(all_series, px, d, tickers)[0], px, asof)
    data["week_ranks"] = week_diff.week_entry(data["rank_history"], px, asof)
    data["walkthrough"] = walkthrough.steps(data)       # "How did #1 get its score?" (Rankings tab)
    # "Is it just the hot group?" (Live paper portfolio tab): today's top N vs past picks
    conc = concentration.build(ranked["score"].dropna().head(TOP_N).index.tolist(), quarters)
    if conc:
        conc["cap"] = concentration.cap_read(robust)
    data["concentration"] = _clean(conc)
    data["weekly"] = weekly.build(data)          # one-screen review + 3 questions (docs/weekly.html)
    new_alerts = alerts_mod.compute(prev, data)
    data["alerts"] = new_alerts
    data["alert_log"] = alerts_mod.merge_log(prev, new_alerts, data["prices_asof"], data["mode"])
    if not args.demo:
        alerts_mod.write(new_alerts, data["prices_asof"])
    for a in new_alerts:
        print(f"  ALERT [{a['level']}] {a['text']}")
    # what changed since the previous run (same wording as the dashboard's "since your last visit")
    snap_file = ROOT / "state" / ("prev_snapshot_demo.json" if args.demo else "prev_snapshot.json")
    try:
        prev_snap = json.loads(snap_file.read_text()) if snap_file.exists() else None
    except (ValueError, OSError):
        prev_snap = None                                  # corrupted file: treat as first run
    cur_snap = since.snapshot(data)
    data["since"] = since.diff(prev_snap, cur_snap)
    data["digest"] = digest.build(data, write=not args.demo)
    rep_dir = ROOT / ("reports_demo" if args.demo else "reports")
    if args.demo:      # demo: the last 4 finished quarters
        qs = quarterly.completed_quarters(asof - pd.DateOffset(months=12), asof)
    else:              # live: every finished quarter since the paper portfolio started
        qs = quarterly.completed_quarters(max(pd.Timestamp(PAPER_START), px.index[0]), asof)
    made = quarterly.write_new(data, rep_dir, qs)
    if made:
        print(f"  New quarterly report(s): {', '.join(made)}")
    data["reports"] = quarterly.load_all(rep_dir)
    runlog.append("ok", log, skipped=list(FAILURES), mode=data["mode"], kind=run_kind)
    data["research"]["robustness_asof"] = (prev or {}).get("research", {}).get("robustness_asof") if run_kind == "fast" \
        else data["prices_asof"]
    data["run_log"] = runlog.recent(log)
    OUT.parent.mkdir(exist_ok=True)
    # phone-friendly: heavy per-stock fields go to detail.json (loaded on demand), time series are packed
    slim_data, detail = slim.split(json.loads(json.dumps(data)))
    slim_data["detail_file"] = "detail.json"
    (OUT.parent / "detail.json").write_text(json.dumps(detail, separators=(",", ":")))
    OUT.write_text(json.dumps(slim.pack(slim_data), separators=(",", ":")))
    if not intraday:     # keep yesterday's close as the baseline until the after-close run
        snap_file.write_text(json.dumps(cur_snap, indent=1))
    s = bt_stats["strategy"]
    print(f"Done → {OUT.relative_to(ROOT)}")
    print(f"  Backtest CAGR {s['cagr']:.1%} | Sharpe {s['sharpe']:.2f} | MaxDD {s['max_drawdown']:.1%}")
    print(f"  Top {TOP_N} now: {ranked['score'].dropna().head(TOP_N).index.tolist()}")


if __name__ == "__main__":
    main()
