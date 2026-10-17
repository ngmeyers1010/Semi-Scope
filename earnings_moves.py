"""
Earnings reactions: how hard does each stock move when it reports?

For each of a stock's last 8 SEC filings (10-Q / 10-K), we look at the FIRST
trading day after the filing date and measure that day's return. Then we compare
the average size of those "reaction days" with an ordinary day for the same
stock: "moves 2.3x more than usual on earnings".

Caveat: the SEC filing date is a proxy. Most companies put out the earnings press
release on the same day or a little earlier, so this measures the reaction around
the filing, not to the exact minute of the announcement.

No look-ahead: only reaction days on or before `asof` count, and each day's
z-move uses the stock's volatility from the year BEFORE that day.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import filings

N_EVENTS = 8
YEAR = 252


def reaction_day(index: pd.DatetimeIndex, filed) -> pd.Timestamp | None:
    """First trading day strictly AFTER the filing date (None if not in the data yet)."""
    pos = index.searchsorted(pd.Timestamp(filed).normalize(), side="right")
    return index[pos] if pos < len(index) else None


def one(p: pd.Series, filed_dates: list, asof) -> dict | None:
    """Reaction stats for one price series and its filing dates."""
    asof = pd.Timestamp(asof)
    p = p.dropna().loc[:asof]
    if len(p) < 60:
        return None
    r = p.pct_change()
    events = []
    for f in filed_dates:
        day = reaction_day(p.index, f)
        if day is None or day > asof:
            continue
        i = p.index.get_loc(day)
        if i < 30:                                   # not enough history before it
            continue
        sigma = float(r.iloc[max(1, i - YEAR):i].std())   # the year before, excluding the day itself
        ret = float(r.iloc[i])
        if not sigma or math.isnan(sigma) or math.isnan(ret):
            continue
        events.append({"filed": pd.Timestamp(f).strftime("%Y-%m-%d"),
                       "day": day.strftime("%Y-%m-%d"), "ret": ret, "z": ret / sigma})
    events = events[-N_EVENTS:]
    if not events:
        return None
    days = {e["day"] for e in events}
    normal = r.iloc[-YEAR:]
    normal = normal[~normal.index.strftime("%Y-%m-%d").isin(days)].dropna()
    normal_abs = float(normal.abs().mean())
    avg_abs = float(np.mean([abs(e["ret"]) for e in events]))
    return {
        "events": events,
        "n": len(events),
        "avg_abs": avg_abs,                        # typical earnings move, ± this much
        "normal_abs": normal_abs,                  # typical ordinary day
        "ratio": avg_abs / normal_abs if normal_abs else None,
        "pct_up": sum(e["ret"] > 0 for e in events) / len(events),
        "avg_abs_z": float(np.mean([abs(e["z"]) for e in events])),
    }


def build(all_series: dict, px: pd.DataFrame, tickers: list[str], asof) -> dict[str, dict]:
    """{ticker: reaction stats} for every ticker with SEC filings and prices."""
    out = {}
    for t in dict.fromkeys(tickers):
        if t not in px:
            continue
        dates = filings.filing_dates(all_series.get(t), asof)
        m = one(px[t], dates, asof)
        if m:
            out[t] = m
    return out


def summary(m: dict | None) -> str:
    """'moves ±6.1% on earnings (2.3x a normal day), up 5 of 8 times'"""
    if not m:
        return ""
    ups = round(m["pct_up"] * m["n"])
    ratio = f" ({m['ratio']:.1f}x a normal day)" if m.get("ratio") else ""
    return f"moves ±{m['avg_abs']:.1%} on earnings{ratio}, up {ups} of {m['n']} times"
