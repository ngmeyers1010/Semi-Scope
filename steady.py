"""
"Is the edge steady?" — how the strategy's lead over SPY behaves one year at a time.

A great average can hide a terrible year. Before trusting a strategy with real money,
know what its bad years look like, because one will come. From a daily equity curve
and SPY:

  * rolling 1-year excess   = strategy's 252-day return − SPY's 252-day return (each compounded)
  * tracking error           = std of daily (strategy − SPY) returns × √252
                               "how far, typically, it wanders from SPY in a year"
  * information ratio (IR)   = annualized mean daily excess ÷ tracking error
                               "edge per unit of wandering" (like a Sharpe ratio vs SPY)
  * share of 1-year windows that beat SPY, and the worst 1-year stretch

Informational only: nothing here changes the picks or the backtest.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

WINDOW = 252          # trading days in a year
PERIODS = 252
MIN_TE = 1e-8         # below this the strategy is SPY in disguise: IR undefined
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _mon(d: pd.Timestamp) -> str:
    return f"{MONTHS[d.month - 1]} {d.year}"


def analyze(curve: pd.Series | None, bench: pd.Series | None, label: str = "backtest",
            step: int = 10) -> dict:
    """Summary dict; {'available': False, 'reason': ...} when there isn't a year of data."""
    if curve is None or bench is None:
        return {"available": False, "label": label, "reason": "no strategy or SPY series"}
    df = pd.concat({"s": curve, "b": bench}, axis=1, sort=True).dropna()
    df = df[(df > 0).all(axis=1)]
    if len(df) <= WINDOW:
        return {"available": False, "label": label,
                "reason": f"needs more than a year of daily data ({len(df)} days so far)"}
    r = df.pct_change().dropna()
    ex_d = r["s"] - r["b"]
    te = float(ex_d.std(ddof=1) * math.sqrt(PERIODS))
    mean_ann = float(ex_d.mean() * PERIODS)
    ir = None if te < MIN_TE else mean_ann / te

    roll = (df["s"] / df["s"].shift(WINDOW)) - (df["b"] / df["b"].shift(WINDOW))
    roll = roll.dropna()
    beat = float((roll > 0).mean())
    worst_end = roll.idxmin()
    worst_start = df.index[df.index.get_loc(worst_end) - WINDOW]
    best_end = roll.idxmax()
    out = {
        "available": True, "label": label, "n_days": int(len(df)), "n_windows": int(len(roll)),
        "tracking_error": te, "excess_ann": mean_ann, "info_ratio": ir,
        "pct_windows_beat": beat, "median_1y": float(roll.median()),
        "worst": {"start": worst_start.strftime("%Y-%m-%d"), "end": worst_end.strftime("%Y-%m-%d"),
                  "excess": float(roll.loc[worst_end])},
        "best": {"end": best_end.strftime("%Y-%m-%d"), "excess": float(roll.loc[best_end])},
        # every 2 weeks (keeps the last day) for the chart: plenty for a phone, small for data.json
        "rolling": [[d.strftime("%Y-%m-%d"), round(float(v), 3)]
                    for d, v in roll.iloc[::-1].iloc[::step].iloc[::-1].items()],
    }
    out["read"] = read(out)
    return out


def _pct_half_up(x: float) -> str:
    """Whole percent, exact halves rounded UP like the page's Math.round (Python's
    f"{x:.0%}" rounds them to even, so the tile and this sentence could disagree)."""
    return f"{int(math.floor(x * 100 + 0.5))}%"


def _signed(x: float) -> str:
    """'+12%', '−28%', or one decimal under 1 point ('−0.4%') so a small loss isn't '-0%'."""
    v = abs(x) * 100
    body = f"{math.floor(v * 10 + 0.5) / 10:.1f}" if v < 1 else f"{int(math.floor(v + 0.5))}"
    return ("+" if x >= 0 else "−") + body + "%"


def read(s: dict) -> str:
    """'Beat SPY in 71% of 1-year windows; worst stretch Mar 2022–Mar 2023 at −18% vs SPY. …'"""
    if not s.get("available"):
        return f"Not enough history yet: {s.get('reason', '')}."
    w, b = s["worst"], s.get("best") or {}
    what = "the paper portfolio" if s.get("label") == "paper" else "the backtest"
    if abs(w["excess"]) < 0.005 and abs(b.get("excess", 0)) < 0.005:
        return ("Moved in step with SPY: no 1-year window was more than half a point ahead or behind. "
                "There's no edge to measure.")
    a, z = _mon(pd.Timestamp(w["start"])), _mon(pd.Timestamp(w["end"]))
    txt = (f"Beat SPY in {_pct_half_up(s['pct_windows_beat'])} of 1-year windows; "
           f"worst stretch {a}–{z} at {_signed(w['excess'])} vs SPY.")
    if w["excess"] < 0:
        txt += " Expect at least one year like that."
    elif s.get("label") == "paper":
        txt += " It hasn't trailed SPY over any full year yet. Give it time: most strategies eventually do."
    else:
        txt += f" It never trailed SPY over a full year in {what}, which is rare. Be suspicious of a backtest that looks this smooth."
    if s["info_ratio"] is not None:
        txt += f" Information ratio {s['info_ratio']:.2f}"
        txt += (" (above 0.5 is good for a stock picker)." if s["info_ratio"] >= 0.5 else
                " (positive but modest)." if s["info_ratio"] > 0 else " (no edge per unit of risk).")
    return txt


def build(curves: dict, bench: pd.DataFrame, paper_curve: pd.Series | None = None) -> dict:
    """{'backtest': analyze(...), 'paper': analyze(...) or None}."""
    spy = bench["SPY"] if bench is not None and "SPY" in bench else None
    out = {"backtest": analyze(curves.get("strategy"), spy, "backtest")}
    if paper_curve is not None and len(paper_curve.dropna()) >= 63:
        out["paper"] = analyze(paper_curve, spy, "paper")
    else:
        out["paper"] = None
    return out
