"""
How long were you underwater?

"Max drawdown −49%" says how deep the worst drop was, not how long it hurt. This module finds
every drawdown EPISODE in an equity curve:

  peak      the last high before the drop
  trough    the lowest point
  recovery  the first day back at (or above) the old high; None if still underwater
  depth     trough / peak − 1
  days      calendar days peak→trough (falling), trough→recovery (climbing back), and total

"Underwater" = below a previous high. The underwater line is equity / running max − 1:
0 at every new high, negative otherwise. Its lowest point is the max drawdown.
"""
from __future__ import annotations

import pandas as pd

TOP = 5
MIN_DEPTH = 0.02          # ignore wiggles smaller than 2%
DEEP = 0.10               # 'deep underwater' = more than 10% below the high
EPS = 1e-12


def underwater(curve: pd.Series) -> pd.Series:
    s = curve.dropna()
    return s / s.cummax() - 1


def episodes(curve: pd.Series, min_depth: float = MIN_DEPTH) -> list[dict]:
    """All drawdown episodes deeper than min_depth, in time order."""
    s = curve.dropna()
    if len(s) < 2:
        return []
    uw = underwater(s)
    out, start = [], None
    for i, (d, v) in enumerate(uw.items()):
        if v < -EPS and start is None:
            start = i - 1                              # the peak is the day before going under
        elif v >= -EPS and start is not None:
            out.append(_episode(s, uw, start, i))
            start = None
    if start is not None:
        out.append(_episode(s, uw, start, None))
    return [e for e in out if -e["depth"] >= min_depth]


def _episode(s: pd.Series, uw: pd.Series, i_peak: int, i_rec: int | None) -> dict:
    window = uw.iloc[i_peak:(i_rec if i_rec is not None else len(uw))]
    trough = window.idxmin()
    peak, rec = s.index[i_peak], (s.index[i_rec] if i_rec is not None else None)
    end = rec if rec is not None else s.index[-1]
    return {"peak": peak.strftime("%Y-%m-%d"), "trough": trough.strftime("%Y-%m-%d"),
            "recovery": rec.strftime("%Y-%m-%d") if rec is not None else None,
            "depth": float(window.min()),
            "days_down": int((trough - peak).days),
            "days_up": int((rec - trough).days) if rec is not None else None,
            "days_total": int((end - peak).days), "recovered": rec is not None}


def summary(curve: pd.Series) -> dict | None:
    s = curve.dropna() if curve is not None else pd.Series(dtype=float)
    if len(s) < 2:
        return None
    eps = episodes(s)
    uw = underwater(s)
    top = sorted(eps, key=lambda e: e["depth"])[:TOP]
    longest = max(eps, key=lambda e: e["days_total"]) if eps else None
    return {"top": top, "n": len(eps), "max_depth": float(uw.min()),
            "longest": longest, "share_underwater": float((uw < -EPS).mean()),
            "share_deep": float((uw < -DEEP).mean()), "now": float(uw.iloc[-1])}


def _months(days: int | None) -> str:
    if days is None:
        return "not yet"
    m = round(days / 30.44)
    return f"{m} month{'s' if m != 1 else ''}" if m >= 1 else f"{days} days"


def _ym(d: str) -> str:
    return d[:7]


def read(strat: dict, bench: dict | None, bench_name: str = "SOXX") -> str:
    if not strat or not strat["top"]:
        return "No drawdowns deeper than 2%."
    w = strat["top"][0]
    rec = (f"took {_months(w['days_total'])} to get back to the old high" if w["recovered"]
           else f"is still underwater after {_months(w['days_total'])}")
    text = f"The worst drop (−{-w['depth']:.0%}, {_ym(w['peak'])} to {_ym(w['trough'])}) {rec}"
    if bench and bench.get("top"):
        b = next((e for e in bench["top"] if e["peak"] <= w["trough"] and
                  (e["recovery"] or "9999") >= w["peak"]), None)     # the benchmark's overlapping drop
        if b:
            btxt = (f"{_months(b['days_total'])}" if b["recovered"] else f"still not back after {_months(b['days_total'])}")
            text += (f"; {bench_name} fell {-b['depth']:.0%} in the same stretch and took {btxt}" if b["recovered"]
                     else f"; {bench_name} fell {-b['depth']:.0%} in the same stretch and is {btxt}")
    text += f". It spent {strat['share_deep']:.0%} of all days more than {DEEP:.0%} below its previous high."
    return text


def build(curves: dict, bench: pd.DataFrame | None, bench_name: str = "SOXX") -> dict | None:
    strat = (curves or {}).get("strategy")
    if strat is None or len(strat.dropna()) < 2:
        return None
    s = summary(strat)
    b_curve = bench[bench_name].loc[strat.dropna().index[0]:] if bench is not None and bench_name in bench else None
    b = summary(b_curve) if b_curve is not None else None
    # no chart data here: the dashboard draws the underwater line from backtest.curves (already in
    # data.json) with the same formula, underwaterPts() in index.html (tests/test_drawdowns.py)
    return {"strategy": s, "bench": b, "bench_name": bench_name, "read": read(s, b, bench_name)}
