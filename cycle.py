"""
Semis cycle view: how is each part of the chip industry doing, and where are we
in the boom/bust cycle?

Chip stocks move in cycles. A rough playbook:
- Recovery:  sales still shrinking YoY, but the decline is slowing (accelerating)
- Upswing:   sales growing AND growth speeding up — usually the best time to own semis
- Late cycle: sales growing but growth slowing — watch inventories
- Downturn:  sales shrinking and getting worse
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from factors import _known

PHASES = {
    "Recovery":   "Sales still down YoY but improving — historically an early-buy zone.",
    "Upswing":    "Sales growing and accelerating — the sweet spot for chip stocks.",
    "Late cycle": "Sales growing but slowing — be choosier; watch inventory build-up.",
    "Downturn":   "Sales shrinking and decelerating — defensive positioning.",
}


def classify(median_growth: float, accel_share: float) -> str:
    """Phase from median YoY revenue growth and the share of companies accelerating."""
    if median_growth is None or accel_share is None or np.isnan(median_growth) or np.isnan(accel_share):
        return "Unknown"
    if median_growth > 0:
        return "Upswing" if accel_share >= 0.5 else "Late cycle"
    return "Recovery" if accel_share >= 0.5 else "Downturn"


def _med(s) -> float | None:
    """Median of the numeric values in s, or None if there are none."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(s.median()) if len(s) else None


def growth_history(all_series: dict, tickers: list[str], asof, n: int = 12) -> pd.DataFrame:
    """YoY revenue growth per company per calendar quarter (known at asof)."""
    rows = []
    for t in tickers:
        rev = _known((all_series.get(t) or {}).get("revenue"), pd.Timestamp(asof))
        if rev is None or len(rev) < 5:
            continue
        s = rev.set_index("end")["val"]
        for end, v in s.items():
            prior = s[(s.index >= end - pd.Timedelta(days=385)) & (s.index <= end - pd.Timedelta(days=345))]
            if len(prior) and prior.iloc[0] > 0:
                rows.append({"ticker": t, "q": pd.Period(end, "Q").strftime("%YQ%q"),
                             "g": v / prior.iloc[0] - 1})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    keep = sorted(df["q"].unique())[-n:]
    return df[df["q"].isin(keep)]


def build(ranked: pd.DataFrame, all_series: dict, universe: dict, asof) -> dict:
    """Cycle phase overall and per group, plus 12 quarters of group sales growth."""
    tickers = list(ranked.index)
    groups = {}
    for t in tickers:
        groups.setdefault(universe.get(t, {}).get("group", "Other"), []).append(t)

    hist = growth_history(all_series, tickers, asof)
    out_groups = []
    for g, members in groups.items():
        sub = ranked.loc[members]
        h = []
        if not hist.empty:
            gh = hist[hist["ticker"].isin(members)].groupby("q")["g"].median()
            h = [[q, round(float(v), 4)] for q, v in gh.items()]
        out_groups.append({
            "group": g, "n": len(members), "members": members,
            "score": _med(sub["score"]), "rev_growth": _med(sub["rev_growth"]),
            "rev_accel": _med(sub["rev_accel"]), "inv_days_change": _med(sub["inv_days_change"]),
            "momentum": _med(sub["momentum"]),
            "phase": classify(_med(sub["rev_growth"]) if _med(sub["rev_growth"]) is not None else np.nan,
                              float((pd.to_numeric(sub["rev_accel"], errors="coerce").dropna() > 0).mean())
                              if pd.to_numeric(sub["rev_accel"], errors="coerce").notna().any() else np.nan),
            "growth_history": h,
        })
    out_groups.sort(key=lambda x: -(x["score"] if x["score"] is not None else -9))

    acc = pd.to_numeric(ranked["rev_accel"], errors="coerce").dropna()
    inv = pd.to_numeric(ranked["inv_days_change"], errors="coerce").dropna()
    med_g = _med(ranked["rev_growth"])
    accel_share = float((acc > 0).mean()) if len(acc) else np.nan
    phase = classify(med_g if med_g is not None else np.nan, accel_share)
    overall_hist = []
    if not hist.empty:
        overall_hist = [[q, round(float(v), 4)] for q, v in hist.groupby("q")["g"].median().items()]
    return {
        "phase": phase, "phase_text": PHASES.get(phase, "Not enough data."),
        "median_growth": med_g,
        "accel_share": None if np.isnan(accel_share) else accel_share,
        "lean_share": float((inv < 0).mean()) if len(inv) else None,
        "groups": out_groups, "growth_history": overall_hist,
    }
