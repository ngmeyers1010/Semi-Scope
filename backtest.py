"""
Quarterly-rebalance backtest: on each rebalance date, score the universe with
data known that day, buy the top N equally weighted, hold until the next
rebalance. Compared against SPY, SOXX, and an equal-weight universe basket.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import sizing

from config import COST_BPS, REBALANCE_MONTHS, TOP_N
from factors import score


FIRST_DAY_SLACK = 7   # an index's very first day only counts as "first trading day" if it's this early


def first_trading_days(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """The first trading day of every month the index covers.

    A day counts only if the trading day before it (in the index) is in an earlier month. The
    index's very first day has no "day before", so it counts only if it falls in the first week
    of its month: an index that starts on Dec 16 must not call Dec 16 a first trading day
    (round 55 bug). Weekends and holidays (e.g. Jan 1, Labor Day) still fit in a week."""
    out, prev = [], None
    for d in index:
        if prev is None:
            if d.day <= FIRST_DAY_SLACK:
                out.append(d)
        elif (d.year, d.month) != (prev.year, prev.month):
            out.append(d)
        prev = d
    return out


def rebalance_dates(index: pd.DatetimeIndex, start, end=None, months=None) -> list[pd.Timestamp]:
    """First trading day of each rebalance month, within [start, end]."""
    months = REBALANCE_MONTHS if months is None else months
    lo, hi = pd.Timestamp(start), pd.Timestamp(end or index[-1])
    return [d for d in first_trading_days(index) if d.month in months and lo <= d <= hi]


def stats(equity: pd.Series) -> dict[str, float]:
    """Summary stats for a daily equity curve starting at 1.0."""
    r = equity.pct_change().dropna()
    if len(r) < 2:
        return {}
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = equity.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    vol = r.std() * np.sqrt(252)
    dd = (equity / equity.cummax() - 1).min()
    return {"total_return": equity.iloc[-1] - 1, "cagr": cagr, "volatility": vol,
            "sharpe": (r.mean() * 252) / vol if vol else np.nan, "max_drawdown": dd}


def run_backtest(all_series: dict, px: pd.DataFrame, bench_px: pd.DataFrame,
                 tickers: list[str], start, weighting: str = "equal") -> tuple[dict[str, pd.Series], list[dict], list[dict]]:
    """Run the quarterly top-N strategy.

    Returns (curves, quarters, panel):
      curves   - equity curves for the strategy and benchmarks (start at 1.0)
      quarters - one dict per rebalance: picks, their returns, benchmark returns
      panel    - per completed quarter: z-scores, scores and forward returns
                 (used by the factor report card)
    """
    dates = rebalance_dates(px.index, start)
    daily = px.pct_change()
    equity = pd.Series(dtype=float)
    value, prev_w = 1.0, pd.Series(dtype=float)
    quarters, panel = [], []

    for i, d in enumerate(dates):
        end = dates[i + 1] if i + 1 < len(dates) else px.index[-1]
        ranked, z = score(all_series, px, d, tickers)
        if i + 1 < len(dates):  # completed quarters only -> factor research panel
            fwd = px.loc[end, ranked.index] / px.loc[d, ranked.index] - 1
            panel.append({"date": d, "z": z, "score": ranked["score"], "fwd": fwd})
        picks = ranked["score"].dropna().head(TOP_N).index.tolist()
        if not picks:
            continue
        w = sizing.weights(px, picks, d, weighting)   # equal by default; see sizing.py
        turnover = w.subtract(prev_w, fill_value=0).abs().sum()
        value *= 1 - turnover * COST_BPS / 1e4

        period = daily.loc[(daily.index > d) & (daily.index <= end), picks].fillna(0)
        # buy-and-hold within the quarter (weights drift with prices)
        growth = (1 + period).cumprod()
        path = value * (growth * w).sum(axis=1)
        if equity.empty:
            equity = pd.concat([pd.Series({d: value}), path])
        else:
            equity = pd.concat([equity, path])
        start_val = value
        value = path.iloc[-1] if len(path) else value
        drifted = (growth.iloc[-1] * w) if len(path) else w
        prev_w = drifted / drifted.sum()

        qret = value / start_val - 1
        b = bench_px.loc[(bench_px.index >= d) & (bench_px.index <= end)]
        bret = (b.iloc[-1] / b.iloc[0] - 1) if len(b) > 1 else pd.Series(dtype=float)
        uni = px.loc[(px.index >= d) & (px.index <= end), ranked.index]
        uret = (uni.iloc[-1] / uni.iloc[0] - 1).mean() if len(uni) > 1 else np.nan
        stock_rets = (px.loc[end, picks] / px.loc[d, picks] - 1)
        quarters.append({
            "date": d.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"),
            "picks": picks, "pick_returns": {t: float(v) for t, v in stock_rets.items()},
            "return": float(qret), "spy": float(bret.get("SPY", np.nan)),
            "soxx": float(bret.get("SOXX", np.nan)), "universe": float(uret),
        })

    equity = equity[~equity.index.duplicated(keep="last")]
    curves = {"strategy": equity}
    s = equity.index[0]
    for b in bench_px.columns:
        bp = bench_px[b].loc[s:].dropna()
        if len(bp):
            curves[b] = bp / bp.iloc[0]
    eq_uni = (1 + daily.loc[daily.index > s, tickers].mean(axis=1).fillna(0)).cumprod()
    curves["universe"] = pd.concat([pd.Series({s: 1.0}), eq_uni])
    return curves, quarters, panel
