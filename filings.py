"""
Earnings-season awareness: when will each company file next?

A company's fundamentals only change when it files a new 10-Q / 10-K. Companies
are creatures of habit — they file at roughly the same time each year — so the
best guess for the next filing is "a year after the matching filing last year".
When a new filing lands, that stock's fundamental factors refresh, which often
explains a sudden rank jump.
"""
from __future__ import annotations

import pandas as pd

from factors import _known

SOON_DAYS = 14


def filing_dates(series: dict | None, asof) -> list[pd.Timestamp]:
    """Distinct dates this company filed quarterly revenue, known as of `asof`."""
    rev = _known((series or {}).get("revenue"), pd.Timestamp(asof))
    if rev is None or rev.empty:
        return []
    return sorted(pd.to_datetime(rev["filed"]).dt.normalize().unique())


def estimate_next(dates: list[pd.Timestamp], asof) -> pd.Timestamp | None:
    """Next expected filing date after `asof`.

    1) Seasonal: the earliest (past filing + 1 year) that is still in the future and
       within ~4 months — companies repeat their calendar.
    2) Fallback: last filing + the median gap between recent filings.
    """
    asof = pd.Timestamp(asof).normalize()
    if not dates:
        return None
    dates = sorted(pd.Timestamp(d) for d in dates)
    one_year = pd.DateOffset(years=1)
    seasonal = [d + one_year for d in dates if asof < d + one_year <= asof + pd.Timedelta(days=125)]
    # ignore anniversaries of filings we've already seen repeated this year
    seasonal = [s for s in seasonal if not any(abs((x - s).days) < 30 for x in dates if x > asof - pd.Timedelta(days=60))]
    if seasonal:
        return min(seasonal)
    if len(dates) >= 3:
        gaps = pd.Series(dates).diff().dropna().dt.days.tail(8)
        gaps = gaps[(gaps > 30) & (gaps < 200)]
        if len(gaps):
            nxt = dates[-1] + pd.Timedelta(days=int(gaps.median()))
            while nxt <= asof:
                nxt += pd.Timedelta(days=int(gaps.median()))
            return nxt
    return None


def build(all_series: dict, tickers: list[str], asof) -> dict[str, dict]:
    """{ticker: {last_filed, next_filing, days_until, soon}} for every ticker with SEC data."""
    asof = pd.Timestamp(asof).normalize()
    out = {}
    for t in tickers:
        dates = filing_dates(all_series.get(t), asof)
        if not dates:
            continue
        nxt = estimate_next(dates, asof)
        days = int((nxt - asof).days) if nxt is not None else None
        out[t] = {
            "last_filed": pd.Timestamp(dates[-1]).strftime("%Y-%m-%d"),
            "next_filing": nxt.strftime("%Y-%m-%d") if nxt is not None else None,
            "days_until": days,
            "soon": days is not None and 0 <= days <= SOON_DAYS,
        }
    return out


def upcoming(filings: dict[str, dict], within: int = 30) -> list[dict]:
    """Filings expected in the next `within` days, soonest first."""
    rows = [{"ticker": t, **f} for t, f in filings.items()
            if f.get("days_until") is not None and 0 <= f["days_until"] <= within]
    return sorted(rows, key=lambda r: r["days_until"])
