"""
Big price moves: was today's move unusual FOR THIS STOCK?

A 5% day is routine for a volatile chip stock and rare for a calm one, so every
move is also expressed as a "z-move": the move divided by the stock's own typical
daily move over the past year (scaled by sqrt(days) for multi-day moves).
3σ means "about 3x bigger than a normal day for this stock".
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

YEAR = 252


def biggest_since(r: pd.Series, today_move: float) -> str | None:
    """Last date BEFORE today with a same-direction daily move at least as big.
    None means it's the biggest in the whole history."""
    past = r.iloc[:-1].dropna()
    hit = past[past <= today_move] if today_move < 0 else past[past >= today_move]
    return hit.index[-1].strftime("%Y-%m-%d") if len(hit) else None


def one(p: pd.Series, avg_cost: float | None = None) -> dict | None:
    """Move stats for one price series ending on the as-of day."""
    p = p.dropna()
    if len(p) < 30:
        return None
    r = p.pct_change()
    sigma = float(r.iloc[-YEAR - 1:-1].std())          # typical daily move, EXCLUDING today
    if not sigma or math.isnan(sigma):
        return None
    out = {"price": float(p.iloc[-1]), "sigma_daily": sigma}
    for k, n in (("1d", 1), ("5d", 5), ("1m", 21)):
        if len(p) > n:
            ret = float(p.iloc[-1] / p.iloc[-1 - n] - 1)
            out[f"r_{k}"], out[f"z_{k}"] = ret, ret / (sigma * math.sqrt(n))
    yr = p.iloc[-YEAR:]
    prior = p.iloc[-YEAR:-1]
    out["dist_52w_high"] = float(p.iloc[-1] / yr.max() - 1)
    out["dist_52w_low"] = float(p.iloc[-1] / yr.min() - 1)
    out["new_52w_high"] = bool(len(prior) and p.iloc[-1] > prior.max())
    out["new_52w_low"] = bool(len(prior) and p.iloc[-1] < prior.min())
    out["biggest_since"] = biggest_since(r, out["r_1d"]) if "r_1d" in out else None
    if avg_cost:
        out["vs_cost"] = float(p.iloc[-1] / avg_cost - 1)
    return out


def price_moves(px: pd.DataFrame, tickers: list[str], asof=None, avg_cost: dict | None = None) -> dict:
    """ticker -> move stats as of `asof` (default: last date)."""
    hist = px if asof is None else px.loc[:pd.Timestamp(asof)]
    out = {}
    for t in dict.fromkeys(tickers):
        if t in hist:
            m = one(hist[t], (avg_cost or {}).get(t))
            if m:
                # last bar older than the as-of date: the "today" numbers are really an older day's
                v = hist[t].notna().to_numpy()
                m["stale_days"] = int(len(v) - 1 - v.nonzero()[0][-1]) if v.any() else len(v)
                out[t] = m
    return out


def alert_text(t: str, m: dict) -> str:
    """'NVDA −9.4% today (a 3.1σ move, biggest drop since 2025-03-10)'"""
    r, z = m["r_1d"], m["z_1d"]
    word = "drop" if r < 0 else "gain"
    since = f"biggest {word} since {m['biggest_since']}" if m.get("biggest_since") else f"biggest {word} on record"
    pct = f"{'−' if r < 0 else '+'}{abs(r):.1%}"
    s = f"{t} {pct} today (a {abs(z):.1f}σ move, {since})"
    if m.get("new_52w_high"):
        s += " · new 52-week high"
    if m.get("new_52w_low"):
        s += " · new 52-week low"
    if m.get("vs_cost") is not None:
        s += f" · {m['vs_cost']:+.0%} vs your cost"
    return s


def alerts_for(moves: dict, tickers: list[str], z_threshold: float) -> list[dict]:
    """Alerts for big moves or new 52-week extremes among `tickers` (your holdings + the picks).
    A big move gets its own line. New 52-week highs (or lows) on an ordinary day are grouped
    into ONE line, e.g. "New 52-week highs: AMD, AMZN, INTC (+1.9% to +2.7% today)", so a
    strong market day doesn't produce five near-identical alerts."""
    out, highs, lows = [], [], []
    for t in dict.fromkeys(tickers):
        m = moves.get(t)
        if not m or "z_1d" not in m or m.get("stale_days"):
            continue                       # no fresh price today: don't repeat an old move as "today"
        if abs(m["z_1d"]) >= z_threshold:
            out.append({"level": "warning" if m["r_1d"] < 0 else "good", "kind": "move",
                        "text": alert_text(t, m), "ticker": t})
        elif m.get("new_52w_high"):
            highs.append((t, m["r_1d"]))
        elif m.get("new_52w_low"):
            lows.append((t, m["r_1d"]))
    for group, word, level in ((highs, "high", "good"), (lows, "low", "warning")):
        if not group:
            continue
        group.sort()
        rs = [r for _, r in group]
        if len(group) == 1:
            t, r = group[0]
            txt = f"{t} hit a new 52-week {word} ({r:+.1%} today)"
        else:
            span = f"{min(rs):+.1%} to {max(rs):+.1%}" if min(rs) != max(rs) else f"{rs[0]:+.1%}"
            txt = f"New 52-week {word}s: {', '.join(t for t, _ in group)} ({span} today)"
        out.append({"level": level, "kind": "move", "text": txt, "ticker": group[0][0],
                    "tickers": [t for t, _ in group]})
    return out
