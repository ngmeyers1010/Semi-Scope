"""
Data health: is the data behind each score complete, fresh and sane?

Garbage in, garbage out. This module checks every company's SEC data and flags:
- STALE:   no new filing in > STALE_FILING_DAYS (missed a 10-Q? delisted? ticker change?)
- ODD:     values that are probably data errors rather than real business changes
- MISSING: foreign filers / no SEC data (scored on price factors only)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from factors import _known

SERIES = ["revenue", "cogs", "inventory", "opinc", "rd", "cfo", "capex", "shares"]
STALE_FILING_DAYS = 120
JUMP = 3.0   # a quarter-over-quarter change bigger than 3x (either way) is suspicious


def _jumps(s: pd.DataFrame | None, n: int = 12) -> int:
    """How many consecutive-quarter ratios in the last n quarters exceed JUMP (or 1/JUMP)."""
    if s is None or len(s) < 2:
        return 0
    v = s["val"].tail(n).astype(float).values
    prev, cur = v[:-1], v[1:]
    ok = (prev > 0) & (cur > 0)
    ratio = cur[ok] / prev[ok]
    return int(((ratio > JUMP) | (ratio < 1 / JUMP)).sum())


def company_health(series: dict | None, asof) -> dict:
    """Coverage, freshness and odd-value flags for ONE company as of `asof`."""
    asof = pd.Timestamp(asof)
    if not series:
        return {"status": "missing", "coverage": {}, "flags": ["No SEC quarterly data (foreign filer?)"],
                "latest_quarter": None, "last_filed": None, "days_since_filing": None, "stale": False}
    known = {k: _known(series.get(k), asof) for k in SERIES}
    coverage = {k: (0 if v is None else int(len(v))) for k, v in known.items()}
    filed = [v["filed"].max() for v in known.values() if v is not None and len(v)]
    last_filed = max(filed) if filed else None
    days = int((asof - last_filed).days) if last_filed is not None else None
    rev, cogs = known["revenue"], known["cogs"]

    flags = []
    stale = days is None or days > STALE_FILING_DAYS
    if stale:
        flags.append(f"No new filing in {days} days" if days is not None else "No filings found")
    if rev is not None and len(rev) and (rev["val"].tail(12) < 0).any():
        flags.append("Negative revenue reported")
    if rev is not None and cogs is not None and len(rev) and len(cogs):
        m = rev.tail(8).merge(cogs, on="end", suffixes=("_r", "_c"))
        m = m[m["val_r"] > 0]
        gm = 1 - m["val_c"] / m["val_r"]
        bad = gm[(gm < -0.5) | (gm > 0.95)]
        if len(bad):
            flags.append(f"Gross margin out of range ({bad.iloc[-1]:.0%})")
    if _jumps(rev):
        flags.append(f"Revenue jumped >{JUMP:.0f}x quarter-over-quarter ({_jumps(rev)}x in 3 yrs)")
    if _jumps(known["shares"]):
        flags.append("Share count jumped >3x (not a split — check for a merger or data error)")
    for k in ("revenue", "cogs", "inventory"):
        if coverage[k] < 6:
            flags.append(f"Only {coverage[k]} quarters of {k}")

    return {
        "status": "warn" if flags else "ok",
        "coverage": coverage,
        "flags": flags,
        "latest_quarter": rev["end"].iloc[-1].strftime("%Y-%m-%d") if rev is not None and len(rev) else None,
        "last_filed": last_filed.strftime("%Y-%m-%d") if last_filed is not None else None,
        "days_since_filing": days,
        "stale": bool(stale),
    }


def build(all_series: dict, tickers: list[str], ranked: pd.DataFrame, asof, meta: dict,
          failures: dict | None = None, stale_px: dict | None = None, sanity: dict | None = None) -> dict:
    """Health rows for every ticker plus summary counts for the dashboard.
    `failures` (ticker -> reason) marks downloads that failed this run."""
    failures = failures or {}
    rows = []
    for t in list(tickers) + [t for t in failures if t not in tickers]:
        h = company_health(all_series.get(t), asof)
        if t in failures:
            h["flags"] = [f"Download failed this run: {failures[t]}"] + (
                [] if t not in tickers else [x for x in h["flags"] if not x.startswith("No SEC")])
            h["status"] = "warn"
        if (stale_px or {}).get(t):
            h["flags"] = [f"No price for the last {stale_px[t]} trading day(s); using the last known one"] + h["flags"]
            h["status"] = "warn"
        sf = (sanity or {}).get(t) or []
        if sf:                                       # sanity.py: impossible SEC numbers (hard ones were dropped)
            h["sanity"] = [x["text"] for x in sf]
            h["flags"] = h["flags"] + h["sanity"]
            h["status"] = "warn" if h["status"] == "ok" else h["status"]
        nf = ranked.loc[t, "n_factors"] if t in ranked.index and "n_factors" in ranked else None
        rows.append({"ticker": t, "name": meta.get(t, {}).get("name", t),
                     "n_factors": None if nf is None or pd.isna(nf) else int(nf), **h})
    order = {"warn": 0, "missing": 1, "ok": 2}
    rows.sort(key=lambda r: (order[r["status"]], r["ticker"]))
    nfs = [r["n_factors"] for r in rows if r["n_factors"] is not None]
    return {
        "rows": rows,
        "summary": {
            "n": len(rows),
            "ok": sum(r["status"] == "ok" for r in rows),
            "warn": sum(r["status"] == "warn" for r in rows),
            "missing": sum(r["status"] == "missing" for r in rows),
            "stale": sum(r["stale"] for r in rows),
            "failed": sum(r["ticker"] in failures for r in rows),
            "stale_price": sorted(t for t, n in (stale_px or {}).items() if n),
            "sanity": sorted((sanity or {}).keys()),
            "avg_factors": float(np.mean(nfs)) if nfs else None,
        },
        "stale_days": STALE_FILING_DAYS,
    }
