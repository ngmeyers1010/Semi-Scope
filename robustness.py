"""
Robustness checks: do the backtest results survive small changes to the rules?

If performance collapses when you hold 8 stocks instead of 5, rebalance a month
earlier, or drop one factor, the "edge" was probably luck in the settings.
Healthy result: every variant beats the benchmark by a similar margin.

Speed trick: factors are scored ONCE per month-start and cached; each variant
just re-weights the cached z-scores and re-simulates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import concentration
import sizing

from backtest import stats
from config import (BACKTEST_START, BUFFER_RANK, COST_BPS, FACTORS, MIN_FACTORS, REBALANCE_MONTHS, TOP_N,
                    WALK_FORWARD_YEARS)
from factors import score

SCHEDULES = {
    "Mar/Jun/Sep/Dec": [3, 6, 9, 12],
    "Feb/May/Aug/Nov": [2, 5, 8, 11],
    "Jan/Apr/Jul/Oct": [1, 4, 7, 10],
}


def month_starts(index: pd.DatetimeIndex, start) -> list[pd.Timestamp]:
    """First trading day of every month from `start` (same rule as backtest.first_trading_days)."""
    from backtest import first_trading_days
    return [d for d in first_trading_days(index) if d >= pd.Timestamp(start)]


def composite(z: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Weighted composite score from cached z-scores, best first."""
    w = pd.Series({f: weights.get(f, 0) for f in z.columns})
    w = w[w > 0]
    if w.empty:
        return pd.Series(dtype=float)
    zz = z[w.index]
    have = zz.notna()
    c = (zz.fillna(0) * w).sum(axis=1) / (have * w).sum(axis=1)
    c[have.sum(axis=1) < min(MIN_FACTORS, len(w))] = np.nan
    return c.dropna().sort_values(ascending=False)


def simulate(px: pd.DataFrame, schedule: list[tuple[pd.Timestamp, list[str]]],
             cost_bps: float = COST_BPS, info: dict | None = None, weighting: str = "equal") -> pd.Series:
    """schedule: list of (date, picks). Equal weight (or `weighting`, see sizing.py), buy-and-hold between dates.

    If `info` is a dict, it is filled with trading stats:
      turnover  - average one-way turnover per rebalance (0.2 = replaced 20% of the portfolio)
      cost_drag - average yearly return lost to trading costs
    """
    daily = px.pct_change()
    value, prev_w, pts = 1.0, pd.Series(dtype=float), []
    turns, costs = [], []
    for i, (d, picks) in enumerate(schedule):
        end = schedule[i + 1][0] if i + 1 < len(schedule) else px.index[-1]
        if not picks:
            continue
        w = sizing.weights(px, picks, d, weighting)
        traded = w.subtract(prev_w, fill_value=0).abs().sum()
        cost = traded * cost_bps / 1e4
        value *= 1 - cost
        if pts:  # the initial purchase isn't "turnover"
            turns.append(traded / 2)
        costs.append(cost)
        if not pts:
            pts.append((d, value))
        period = daily.loc[(daily.index > d) & (daily.index <= end), picks].fillna(0)
        if len(period):
            g = (1 + period).cumprod()
            path = value * (g * w).sum(axis=1)
            pts += list(path.items())
            value = path.iloc[-1]
            dr = g.iloc[-1] * w
            prev_w = dr / dr.sum()
    eq = pd.Series(dict(pts)).sort_index()
    eq = eq[~eq.index.duplicated(keep="last")]
    if info is not None and len(eq) > 1:
        years = (eq.index[-1] - eq.index[0]).days / 365.25
        info["turnover"] = float(np.mean(turns)) if turns else 0.0
        info["cost_drag"] = float(sum(costs) / years) if years > 0 else 0.0
    return eq


def _rank_ic(x: pd.Series, y: pd.Series) -> float:
    m = x.notna() & y.notna()
    return x[m].rank().corr(y[m].rank()) if m.sum() >= 8 else np.nan


def ic_history(z_by_date: list[tuple[pd.Timestamp, pd.DataFrame]], px: pd.DataFrame,
               factors: list[str]) -> list[tuple[pd.Timestamp, dict]]:
    """For each rebalance date d_i: each factor's IC over the quarter d_i -> d_(i+1).
    Returned as (KNOWN date, ICs): the result is only known at d_(i+1), when the
    quarter is over. Using the known date is what prevents look-ahead."""
    out = []
    for (d, z), (d_next, _) in zip(z_by_date, z_by_date[1:]):
        a, b = px.loc[:d].iloc[-1], px.loc[:d_next].iloc[-1]
        fwd = b / a - 1
        out.append((d_next, {f: _rank_ic(z[f].reindex(fwd.index), fwd) for f in factors if f in z}))
    return out


def walk_forward_weights(hist: list[tuple[pd.Timestamp, dict]], d: pd.Timestamp, fallback: dict,
                         years: int = WALK_FORWARD_YEARS, min_quarters: int = 4) -> dict:
    """Weights at date d = each factor's mean IC over the trailing `years`, using
    only quarters already finished by d. Negative means are clipped to 0 (a stat
    that stopped working is switched off, never flipped). Falls back to the fixed
    weights until there's enough history."""
    lo = d - pd.DateOffset(years=years)
    known = [ics for k, ics in hist if lo < k <= d]
    if len(known) < min_quarters:
        return dict(fallback)
    df = pd.DataFrame(known)
    w = df[[f for f in fallback if f in df]].mean().clip(lower=0)
    return w.to_dict() if w.sum() > 0 else dict(fallback)


def buffer_schedule(ranked_by_date: list[tuple[pd.Timestamp, pd.Series]], n: int,
                    buffer: int) -> list[tuple[pd.Timestamp, list[str]]]:
    """Sell discipline: keep a holding while it stays in the top `buffer`;
    only replace stocks that fall out, refilling from the top of the ranking."""
    holdings: list[str] = []
    out = []
    for d, ranked in ranked_by_date:
        order = list(ranked.index)
        allowed = set(order[:buffer])
        keep = [h for h in holdings if h in allowed]
        for t in order:
            if len(keep) >= n:
                break
            if t not in keep:
                keep.append(t)
        holdings = keep
        out.append((d, list(keep)))
    return out


def run(all_series: dict, px: pd.DataFrame, bench: pd.DataFrame, tickers: list[str],
        start=BACKTEST_START) -> list[dict]:
    """Backtest every rule variant; returns one stats row per variant (baseline first)."""
    base_w = {f: c["weight"] for f, c in FACTORS.items() if c["weight"] > 0}
    cache = {d: score(all_series, px, d, tickers)[1] for d in month_starts(px.index, start)}

    def sched(months, weights, n):
        return [(d, composite(z, weights).head(n).index.tolist())
                for d, z in cache.items() if d.month in months]

    V = lambda name, group, months=REBALANCE_MONTHS, w=base_w, n=TOP_N, buffer=None, cost=COST_BPS, weighting="equal": \
        {"name": name, "group": group, "months": months, "w": w, "n": n, "buffer": buffer, "cost": cost,
         "weighting": weighting}
    variants = [V("Baseline", "baseline")]
    for n in (3, 8, 10):
        if n != TOP_N:
            variants.append(V(f"Hold top {n}", "holdings", n=n))
    for name, months in SCHEDULES.items():
        if sorted(months) != sorted(REBALANCE_MONTHS):
            variants.append(V(f"Rebalance {name}", "timing", months=months))
    for b in sorted({BUFFER_RANK, 8}, reverse=True):
        if b > TOP_N:
            variants.append(V(f"Sell rule: keep while top {b}", "sell rule", buffer=b))
    variants.append(V("Costs 30 bps (stress test)", "costs", cost=30))
    variants.append(V("Inverse-vol weights", "sizing", weighting="inverse_vol"))
    for f in base_w:
        w = dict(base_w); w.pop(f)
        variants.append(V(f"Without {FACTORS[f]['label'].split(' (')[0]}", "leave-one-out", w=w))
    variants.append(V("All weights equal", "weights", w={f: 1.0 for f in base_w}))

    # walk-forward: re-learn weights each quarter from trailing IC (no future data)
    rebal = [(d, z) for d, z in cache.items() if d.month in REBALANCE_MONTHS]
    hist = ic_history(rebal, px, list(base_w))
    wf_sched = [(d, composite(z, walk_forward_weights(hist, d, base_w)).head(TOP_N).index.tolist())
                for d, z in rebal]
    variants.append({**V(f"Walk-forward weights ({WALK_FORWARD_YEARS}-yr trailing IC)", "walk-forward"),
                     "schedule": wf_sched})

    # concentration: at most 2 picks per industry group (appended last so other rows keep their order)
    variants.append({**V(f"Max {concentration.CAP} per group", "concentration"),
                     "schedule": [(d, concentration.capped_picks(list(composite(z, base_w).index), TOP_N))
                                  for d, z in cache.items() if d.month in REBALANCE_MONTHS]})

    spy = bench["SPY"] if "SPY" in bench else None
    rows = []
    for v in variants:
        if v.get("schedule"):
            schedule = v["schedule"]
        elif v["buffer"]:
            ranked = [(d, composite(z, v["w"])) for d, z in cache.items() if d.month in v["months"]]
            schedule = buffer_schedule(ranked, v["n"], v["buffer"])
        else:
            schedule = sched(v["months"], v["w"], v["n"])
        info: dict = {}
        eq = simulate(px, schedule, cost_bps=v["cost"], info=info, weighting=v.get("weighting", "equal"))
        s = stats(eq)
        if spy is not None and len(eq):
            sp = spy.loc[eq.index[0]:eq.index[-1]].dropna()
            s["spy_cagr"] = stats(sp / sp.iloc[0]).get("cagr")
        rows.append({"name": v["name"], "group": v["group"], **s, **info})
    base = rows[0]["cagr"]
    for r in rows:
        r["vs_baseline"] = r["cagr"] - base
        r["beats_spy"] = r.get("spy_cagr") is not None and r["cagr"] > r["spy_cagr"]
    return rows


# ---------- Start-date luck ----------
# A backtest that starts on one particular day can look better or worse than the strategy
# really is. Re-run the baseline from 12 different starts: each of the 3 quarterly calendars,
# each starting 0, 3, 6 or 9 months after BACKTEST_START. If the headline CAGR sits in the
# middle of that spread, it wasn't a lucky start.
LUCK_OFFSETS = (0, 3, 6, 9)


def start_luck(all_series: dict, px: pd.DataFrame, tickers: list[str], start=BACKTEST_START,
               baseline_cagr: float | None = None) -> dict | None:
    base_w = {f: c["weight"] for f, c in FACTORS.items() if c["weight"] > 0}
    cache = {d: score(all_series, px, d, tickers)[1] for d in month_starts(px.index, start)}
    runs = []
    for cal_name, months in SCHEDULES.items():
        for off in LUCK_OFFSETS:
            begin = pd.Timestamp(start) + pd.DateOffset(months=off)
            schedule = [(d, composite(z, base_w).head(TOP_N).index.tolist())
                        for d, z in cache.items() if d.month in months and d >= begin]
            if len(schedule) < 4:
                continue
            s = stats(simulate(px, schedule))
            runs.append({"calendar": cal_name, "offset_months": off, "start": schedule[0][0].strftime("%Y-%m-%d"),
                         "cagr": s.get("cagr"), "sharpe": s.get("sharpe"),
                         "baseline": cal_name == "Mar/Jun/Sep/Dec" and off == 0})
    return summarize(runs, baseline_cagr)


def summarize(runs: list[dict], baseline_cagr: float | None = None) -> dict | None:
    ok = [r for r in runs if r.get("cagr") is not None]
    if len(ok) < 3:
        return None
    c = sorted(r["cagr"] for r in ok)
    sh = sorted(r["sharpe"] for r in ok if r.get("sharpe") is not None)
    base = baseline_cagr if baseline_cagr is not None else next((r["cagr"] for r in ok if r.get("baseline")), None)
    med = c[len(c) // 2] if len(c) % 2 else (c[len(c) // 2 - 1] + c[len(c) // 2]) / 2
    out = {"runs": runs, "n": len(ok), "cagr_min": c[0], "cagr_median": med, "cagr_max": c[-1],
           "sharpe_min": sh[0] if sh else None, "sharpe_max": sh[-1] if sh else None, "baseline_cagr": base}
    out["rank_pct"] = None if base is None else sum(x < base for x in c) / len(c)
    out["read"] = luck_read(out)
    return out


def luck_read(s: dict) -> str:
    lo, hi, base = s["cagr_min"], s["cagr_max"], s.get("baseline_cagr")
    head = f"Starting on a different date moves CAGR between {lo:.0%} and {hi:.0%} ({s['n']} starts)."
    if base is None:
        return head
    p = s.get("rank_pct") or 0
    if p >= 0.8:
        return head + (f" The {base:.1%} headline is near the TOP of that range, so part of it is a lucky start: "
                       f"expect closer to the {s['cagr_median']:.0%} median.")
    if p <= 0.2:
        return head + f" The {base:.1%} headline is near the BOTTOM: if anything, the start date was unlucky."
    return head + f" The {base:.1%} headline sits mid-pack, so it isn't a lucky start."
