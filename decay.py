"""
Signal decay: how long does a pick's edge last?

The strategy picks its top stocks on the first trading day of Mar/Jun/Sep/Dec and holds them
for 3 months. Is 3 months right? For every historical rebalance, this measures how the picks
did against the average stock (equal-weight universe) 1, 2, 3, 6, 9 and 12 months later:

  * mean excess   average of (picks' return − universe return) at that horizon
  * per month     mean excess ÷ months, so a 1-month and a 12-month number compare fairly
  * hit rate      share of rebalances where the picks beat the universe
  * t-stat        mean ÷ (std ÷ √n), shrunk for overlap: picks made every 3 months and held 6
                  share half their days with the next set, so they aren't independent
                  (t ÷ √(months ÷ 3) is a rough, conservative fix)

Point in time: the picks are the backtest's own (scored with data known on that date). Only
prices AFTER the date are used to measure, and a horizon that hasn't finished yet is skipped.
"""
from __future__ import annotations

import math

import pandas as pd

HORIZONS = (1, 2, 3, 6, 9, 12)
MIN_OBS = 4          # fewer finished rebalances than this at a horizon: not reported


def _end(index: pd.DatetimeIndex, d: pd.Timestamp, months: int) -> pd.Timestamp | None:
    """First trading day on/after d + months, or None if the data doesn't reach it yet."""
    target = d + pd.DateOffset(months=months)
    i = index.searchsorted(target)
    return index[i] if i < len(index) else None


def _ret(px: pd.DataFrame, names: list[str], d, e) -> float | None:
    names = [t for t in names if t in px.columns]
    if not names:
        return None
    a, b = px.loc[d, names], px.loc[e, names]
    r = (b / a - 1)[(a > 0) & a.notna() & b.notna()]
    return float(r.mean()) if len(r) else None


def observations(px: pd.DataFrame, schedule: list[tuple], universe: list[str],
                 horizons=HORIZONS) -> list[dict]:
    """One row per (rebalance date, horizon): {date, months, pick, universe, excess}."""
    out = []
    for d, picks in schedule:
        d = pd.Timestamp(d)
        if d not in px.index or not picks:
            continue
        for h in horizons:
            e = _end(px.index, d, h)
            if e is None:
                continue
            p, u = _ret(px, list(picks), d, e), _ret(px, universe, d, e)
            if p is None or u is None:
                continue
            out.append({"date": d.strftime("%Y-%m-%d"), "months": h, "pick": p, "universe": u, "excess": p - u})
    return out


def summarize(obs: list[dict], horizons=HORIZONS, step_months: int = 3) -> list[dict]:
    rows = []
    for h in horizons:
        x = [o["excess"] for o in obs if o["months"] == h]
        n = len(x)
        if n < MIN_OBS:
            continue
        m = sum(x) / n
        sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
        t = m / (sd / math.sqrt(n)) if sd > 0 else 0.0
        t /= math.sqrt(max(1.0, h / step_months))               # overlapping windows
        rows.append({"months": h, "n": n, "mean": m, "per_month": m / h,
                     "hit": sum(v > 0 for v in x) / n, "t": t})
    return rows


def read(rows: list[dict], hold: int = 3) -> tuple[str, str]:
    """(sentence, suggestion) where suggestion is 'fits', 'faster', 'slower' or 'none'."""
    by = {r["months"]: r for r in rows}
    if hold not in by or not rows:
        return "Not enough finished rebalances yet to see how long the edge lasts.", "none"
    if all(r["mean"] <= 0 for r in rows):
        return ("The picks didn't beat the average stock at any horizon from 1 to 12 months: "
                "no edge to time."), "none"
    peak = max(rows, key=lambda r: r["mean"])
    h3 = by[hold]
    one = by.get(1)
    if one and one["per_month"] > 2 * max(h3["per_month"], 0) and one["mean"] > 0 and one["t"] >= 1:
        return (f"Most of the edge shows up in the first month ({one['mean']:+.1%}) and then slows: "
                f"monthly rebalancing might capture more, but trades 3× as often."), "faster"
    later = [r for r in rows if r["months"] > hold]
    # "slower" only if the edge never turns negative later: a reversal makes holding longer risky
    if (later and all(r["mean"] > 0 for r in later) and peak["months"] > hold
            and peak["mean"] > 1.5 * max(h3["mean"], 0) and peak["t"] >= 1):
        return (f"The edge keeps building after {hold} months (peaks at {peak['months']} months, "
                f"{peak['mean']:+.1%}): holding longer might work as well with less trading."), "slower"
    text = f"The edge builds to {h3['mean']:+.1%} by {hold} months"
    if peak["months"] != hold:
        text += f" ({peak['mean']:+.1%} at {peak['months']}" + (", less certain)" if peak["t"] < 1 else ")")
    gone = [r for r in later if r["mean"] < 0]
    if gone:
        worst = min(gone, key=lambda r: r["mean"])
        text += (f", then reverses: {worst['mean']:+.1%} by {worst['months']} months. Rebalancing every {hold} "
                 f"months fits; holding picks much longer would have given the edge back.")
    else:
        text += f": rebalancing every {hold} months fits."
    return text, "fits"


def build(px: pd.DataFrame, quarters: list[dict], universe: list[str], hold: int = 3) -> dict | None:
    """data['research']['decay'] from the backtest's own quarterly picks."""
    schedule = [(q["date"], q.get("picks") or []) for q in quarters]
    rows = summarize(observations(px, schedule, universe))
    if not rows:
        return None
    text, suggest = read(rows, hold)
    return {"rows": rows, "read": text, "suggest": suggest, "hold": hold, "n_rebalances": len(schedule)}
