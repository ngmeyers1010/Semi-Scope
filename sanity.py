"""
Sanity checks on SEC numbers BEFORE they reach the rankings.

XBRL data from the SEC is mostly right, but real-world errors happen: a quarter reported in
thousands instead of dollars (1,000× off), a full year tagged as one quarter (~4× off),
negative revenue, the same number copied forward for a year. One bad quarter can push a
stock to #1 on "revenue growth".

Rules (per company, per series, one row = one quarter):
  HARD (the quarter is dropped from scoring, and flagged):
    a. revenue ≤ 0
    b. a value ≥ 8× or ≤ 1/8 of the median of the up-to-4 quarters BEFORE it (revenue, cogs,
       inventory). Only earlier quarters are used, so a backtest can't see the future: on the
       day a bad quarter is filed, you'd already know it looks wrong.
  SOFT (flagged only, still used):
    c. gross margin outside −50%..100%
    d. the same value 4+ quarters in a row (a stale or copied fact)

Normal chip-cycle swings (revenue −60% over a year, +80% in a boom) are nowhere near 8× in
one quarter, so they pass.
"""
from __future__ import annotations

import pandas as pd

JUMP = 8.0
LOOKBACK = 4
REPEAT = 4
RATIO_SERIES = ("revenue", "cogs", "inventory")
REPEAT_SERIES = ("revenue", "cogs", "opinc", "inventory", "cfo", "capex")
LABEL = {"revenue": "revenue", "cogs": "cost of goods", "inventory": "inventory", "opinc": "operating income",
         "cfo": "operating cash flow", "capex": "capex"}


def _q(d) -> str:
    d = pd.Timestamp(d)
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


def _ratio_text(r: float) -> str:
    """2 significant figures: 1,048 -> '1,000', 9.3 -> '9.3'."""
    if r >= 10:
        from math import floor, log10
        k = 10 ** (floor(log10(r)) - 1)
        return f"{round(r / k) * k:,.0f}"
    return f"{r:.1f}"


def check_series(name: str, df: pd.DataFrame | None) -> tuple[list[int], list[dict]]:
    """(row positions to drop, flags) for one series DataFrame with columns end/val/filed."""
    if df is None or not len(df):
        return [], []
    v = df["val"].astype(float).reset_index(drop=True)
    ends = df["end"].reset_index(drop=True)
    drop, flags = [], []
    for i, x in enumerate(v):
        if pd.isna(x):
            continue
        if name == "revenue" and x <= 0:
            drop.append(i)
            flags.append({"series": name, "end": str(pd.Timestamp(ends[i]).date()), "rule": "nonpositive", "hard": True,
                          "text": f"{_q(ends[i])} revenue is {x:,.0f}: impossible, ignored"})
            continue
        if name in RATIO_SERIES:
            prev = v.iloc[max(0, i - LOOKBACK):i]
            prev = prev[[j not in drop for j in prev.index]].dropna()
            prev = prev[prev > 0]
            if len(prev) >= 2 and x > 0:
                med = float(prev.median())
                r = x / med
                if r >= JUMP or r <= 1 / JUMP:
                    drop.append(i)
                    big = r >= JUMP
                    what = (f"about {_ratio_text(r)}× the quarters before it" if big
                            else f"about 1/{_ratio_text(1 / r)} of the quarters before it")
                    why = "probably a units error" if (big and r >= 500) or (not big and r <= 1 / 500) else "probably a period or units error"
                    flags.append({"series": name, "end": str(pd.Timestamp(ends[i]).date()), "rule": "jump", "hard": True,
                                  "text": f"{_q(ends[i])} {LABEL[name]} is {what}: {why}, ignored"})
    if name in REPEAT_SERIES:
        run = 1
        for i in range(1, len(v)):
            same = pd.notna(v[i]) and v[i] == v[i - 1] and v[i] != 0
            run = run + 1 if same else 1
            if run == REPEAT:
                flags.append({"series": name, "end": str(pd.Timestamp(ends[i]).date()), "rule": "repeat", "hard": False,
                              "text": f"{LABEL[name].capitalize()} is exactly the same for {REPEAT}+ quarters in a row "
                                      f"(to {_q(ends[i])}): possibly a copied or stale number"})
    return sorted(set(drop)), flags


def check_margin(rev: pd.DataFrame | None, cogs: pd.DataFrame | None) -> list[dict]:
    if rev is None or cogs is None or not len(rev) or not len(cogs):
        return []
    m = rev[["end", "val"]].merge(cogs[["end", "val"]], on="end", suffixes=("_r", "_c"))
    m = m[m["val_r"] > 0]
    gm = 1 - m["val_c"] / m["val_r"]
    out = []
    for end, g in zip(m["end"], gm):
        if g < -0.5 or g > 1.0:
            out.append({"series": "cogs", "end": str(pd.Timestamp(end).date()), "rule": "margin", "hard": False,
                        "text": f"{_q(end)} gross margin is {g:.0%}: outside the possible range, check the filing"})
    return out


def clean(all_series: dict) -> tuple[dict, dict]:
    """(cleaned copy of all_series, {ticker: [flags]}). Hard errors are removed from the copy;
    stocks with no problems are passed through untouched (same objects)."""
    out, flags = {}, {}
    for t, series in (all_series or {}).items():
        if not series:
            out[t] = series
            continue
        new, f = dict(series), []
        for name in set(RATIO_SERIES) | set(REPEAT_SERIES):
            df = series.get(name)
            drop, fl = check_series(name, df)
            f += fl
            if drop:
                new[name] = df.drop(df.index[drop]).reset_index(drop=True)
        f += check_margin(new.get("revenue"), new.get("cogs"))
        if f:
            f.sort(key=lambda x: (x["end"], x["series"]))
            flags[t] = f
        out[t] = new if any(new.get(k) is not series.get(k) for k in new) else series
    return out, flags
