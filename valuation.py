"""
"Cheap vs its own history": where today's price-to-sales sits in the stock's OWN range.

Semis are cyclical, so comparing NVDA's P/S with TXN's says little. Comparing NVDA today
with NVDA over the last 5 years says more: "6.2x sales, higher than 82% of weeks since 2021".

    P/S = market cap / TTM sales = 1 / sales_yield

Every weekly point uses only data known that week (sales_yield() already enforces
"filed before"), split-adjusted closes and SEC share counts in today's split units, so a
10:1 split doesn't make the history look 10x cheaper.

Informational only: it is NOT part of the score, so rankings and the backtest don't change.
The plain-English label is mirrored in docs/index.html (`// ---- valpct` block);
tests/test_valuation.py checks both languages agree.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from factors import sales_yield

YEARS = 5           # look-back window
MIN_YEARS = 2       # less history than this -> no percentile
MIN_POINTS = 80     # weekly points with a valid P/S (≈ 1.5 years of the 2)
EXTREME_LO, EXTREME_HI = 10, 90


def label(pct: float | None) -> str:
    """Plain-English read of a 0-100 percentile (same thresholds as valLabel in index.html)."""
    if pct is None:
        return "not enough history"
    if pct < 10:
        return "near its cheapest"
    if pct < 25:
        return "cheaper than usual"
    if pct <= 75:
        return "about usual"
    if pct <= 90:
        return "pricier than usual"
    return "near its priciest"


def percentile(current: float, history) -> float:
    """Share of history below `current` (ties count half), 0-100."""
    h = np.asarray([v for v in history if v is not None and np.isfinite(v)], dtype=float)
    if not len(h):
        return float("nan")
    return float(100.0 * ((h < current).sum() + 0.5 * (h == current).sum()) / len(h))


def ps_history(series: dict, close: pd.Series, asof, years: int = YEARS) -> pd.Series:
    """Weekly P/S (Friday closes) over the last `years`, point-in-time. NaN weeks dropped."""
    asof = pd.Timestamp(asof)
    c = close.dropna()
    c = c[(c.index <= asof) & (c.index > asof - pd.DateOffset(years=years))]
    if c.empty:
        return pd.Series(dtype=float)
    # each week's LAST TRADING DAY (not the Friday label: on a Friday holiday the price is
    # Thursday's, so filings must be checked as of Thursday too, or the history peeks a day ahead)
    wk = c.groupby(c.index.to_period("W-FRI")).tail(1)
    out = {}
    for d, p in wk.items():
        sy = sales_yield(series, d, float(p))          # same 'filed before' rule as the score
        if np.isfinite(sy) and sy > 0:
            out[d] = 1.0 / sy
    return pd.Series(out, dtype=float)


def one(series: dict | None, close: pd.Series | None, asof) -> dict | None:
    """{ps, pct, lo, med, hi, years, n, label} or None (no SEC data / no valid P/S today)."""
    if not series or close is None:
        return None
    asof = pd.Timestamp(asof)
    c = close[close.index <= asof].dropna()
    if c.empty:
        return None
    sy = sales_yield(series, asof, float(c.iloc[-1]))
    if not (np.isfinite(sy) and sy > 0):            # zero/negative sales, stale filings
        return None
    ps = 1.0 / sy
    h = ps_history(series, close, asof)
    years = (h.index[-1] - h.index[0]).days / 365.25 if len(h) > 1 else 0.0
    out = {"ps": round(ps, 3), "years": round(years, 1), "n": int(len(h)),
           "pct": None, "lo": None, "med": None, "hi": None}
    if years >= MIN_YEARS - 0.05 and len(h) >= MIN_POINTS:
        out.update(pct=round(percentile(ps, h.values), 1), lo=round(float(h.min()), 3),
                   med=round(float(h.median()), 3), hi=round(float(h.max()), 3))
    out["label"] = label(out["pct"])
    return out


def build(all_series: dict, close: pd.DataFrame, tickers: list[str], asof) -> dict:
    """{ticker: one(...)} for every ticker with a result."""
    out = {}
    for t in tickers:
        if t in close:
            r = one(all_series.get(t), close[t], asof)
            if r is not None:
                out[t] = r
    return out


def sentence(t: str, v: dict | None) -> str:
    """'MU: P/S 2.1x, 8th percentile of its 5-yr range (near its cheapest).'"""
    if not v:
        return f"{t}: no P/S (no SEC sales data)."
    if v.get("pct") is None:
        return f"{t}: P/S {_x(v['ps'])}x ({label(None)})."
    return f"{t}: P/S {_x(v['ps'])}x, {ordinal(v['pct'])} percentile of its {YEARS}-yr range ({v['label']})."


def _x(v: float) -> str:
    return f"{v:.2f}" if v < 1 else f"{v:.1f}"


def ordinal(p: float) -> str:
    n = int(np.floor(p + 0.5))       # round half up, like JS Math.round
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"
