"""
Up/down capture: how much of the benchmark's good months and bad months the strategy catches.

Using month-end prices:
  up-capture   = average strategy return in months the benchmark ROSE
                 ÷ average benchmark return in those same months
  down-capture = the same for months the benchmark FELL

  Up 120%, down 80%  -> gains more when it's up AND loses less when it's down (the dream)
  Up 120%, down 130% -> a leveraged version of the benchmark: bigger swings both ways
  Up  90%, down 70%  -> a defensive strategy: wins by falling less

Months where the benchmark was exactly flat are left out (no direction to capture).
"""
from __future__ import annotations

import pandas as pd

MIN_MONTHS = 6          # the paper portfolio needs at least this many months
BENCHES = ("SPY", "SOXX")


def monthly(curve: pd.Series) -> pd.Series:
    s = curve.dropna()
    return s.resample("ME").last().pct_change().dropna() if len(s) else pd.Series(dtype=float)


def capture(strat: pd.Series, bench: pd.Series) -> dict | None:
    """Both are price/equity curves. Uses only months both cover."""
    s, b = monthly(strat), monthly(bench)
    both = pd.concat([s.rename("s"), b.rename("b")], axis=1, sort=True).dropna()
    if len(both) < MIN_MONTHS:
        return None
    up, dn = both[both["b"] > 0], both[both["b"] < 0]
    out = {"months": len(both), "up_months": len(up), "down_months": len(dn)}
    out["up"] = float(up["s"].mean() / up["b"].mean()) if len(up) else None
    out["down"] = float(dn["s"].mean() / dn["b"].mean()) if len(dn) else None
    out["beat_up"] = float((up["s"] > up["b"]).mean()) if len(up) else None
    out["beat_down"] = float((dn["s"] > dn["b"]).mean()) if len(dn) else None
    return out


def read(name: str, c: dict) -> str:
    up, dn = c.get("up"), c.get("down")
    if up is None or dn is None:
        return f"Not enough up and down months in {name} yet."
    head = f"Catches {up:.0%} of {name}'s up months and {dn:.0%} of its down months"
    if up >= 1 and dn < 1:
        tail = ": more of the gains, less of the losses."
    elif up >= 1 and dn >= 1:
        tail = (": bigger swings both ways, like a leveraged " + name + "." if dn >= up
                else ": bigger swings both ways, but more on the way up.")
    elif up < 1 and dn < 1:
        tail = ": it wins by falling less." if dn < up else ": smaller swings, and it lags on the way up."
    else:
        tail = ": less of the gains and more of the losses. That's the worst combination."
    return head + tail


def build(curves: dict, bench: pd.DataFrame | None, paper_curve: pd.Series | None = None) -> dict | None:
    """data['capture']: {backtest: {SPY: {...}, SOXX: {...}}, paper: {...} | None, paper_note}"""
    strat = (curves or {}).get("strategy")
    if strat is None or bench is None:
        return None
    def for_curve(curve):
        res = {}
        for b in BENCHES:
            if b in bench:
                c = capture(curve, bench[b])
                if c:
                    c["read"] = read(b, c)
                    res[b] = c
        return res or None
    out = {"backtest": for_curve(strat), "paper": None}
    if out["backtest"] is None:
        return None
    if paper_curve is not None and len(monthly(paper_curve)) >= MIN_MONTHS:
        out["paper"] = for_curve(paper_curve)
    n = 0 if paper_curve is None else len(monthly(paper_curve))
    out["paper_note"] = None if out["paper"] else (
        f"The paper portfolio has {n} full month{'s' if n != 1 else ''}; capture needs at least {MIN_MONTHS}. "
        "Until then, these numbers are the backtest's.")
    return out
