"""
"What changed since last week" on the Rankings tab.

run.py scores the universe again as of 5 trading days ago and keeps only the ranks:
    data["week_ranks"] = {"asof": "2026-10-09", "ranks": {"MU": 3, ...}}     (~0.5 KB)
The dashboard compares that with today's rankings using weekDiff() in docs/index.html.
diff() below is the same logic in Python; tests/test_week_diff.py checks the two agree.

A rank going DOWN in number is good: #9 -> #4 is a climb of 5.

Round 80 adds rank streaks: run.py also scores 10, 15 and 20 trading days back, stored as
    data["rank_history"] = [{"asof": ..., "ranks": {...}}, ...]   oldest first (last = week_ranks)
and streak_of() counts how many snapshots in a row, ending today, a stock has been in the top N
(streakOf() in index.html is the JS twin). The Rankings table shows it as "3 wk in top 5".
"""
from __future__ import annotations

import pandas as pd

TRADING_DAYS = 5
N_MOVERS = 3
HISTORY_STEPS = (20, 15, 10, 5)          # trading days back, oldest first


def ranks_of(rows) -> dict:
    """{ticker: int rank} for ranked rows (a list of dicts or a scored DataFrame)."""
    if isinstance(rows, pd.DataFrame):
        rows = [{"ticker": t, "rank": r} for t, r in rows["rank"].items()]
    out = {}
    for r in rows or []:
        v = r.get("rank")
        if v is not None and v == v:
            out[r["ticker"]] = int(v)
    return out


def history(score_fn, px, asof, steps=HISTORY_STEPS) -> list:
    """[{asof, ranks}] for each step back that the price history reaches, oldest first."""
    out = []
    for k in steps:
        d = week_ago(px, asof, k)
        if d is None:
            continue
        ranks = ranks_of(score_fn(d))
        if ranks:
            out.append({"asof": d.strftime("%Y-%m-%d"), "ranks": dict(sorted(ranks.items()))})
    return out


def week_entry(hist, px, asof):
    """The history entry from exactly TRADING_DAYS sessions ago (what week_ranks has always been)."""
    d = week_ago(px, asof)
    key = d.strftime("%Y-%m-%d") if d is not None else None
    return next((h for h in hist or [] if h["asof"] == key), None)


def streak_of(hist, cur: dict, ticker: str, top_n: int) -> int:
    """Snapshots in a row, ending with today, with `ticker` ranked <= top_n. 0 if not in the top today.
    A snapshot where the ticker is missing (or ranked lower) ends the streak."""
    inn = lambda r: r is not None and r <= top_n
    if not inn((cur or {}).get(ticker)):
        return 0
    n = 1
    for snap in reversed(hist or []):
        if not inn((snap.get("ranks") or {}).get(ticker)):
            break
        n += 1
    return n


def streaks(hist, cur: dict, top_n: int) -> dict:
    """{ticker: streak} for every ticker in the top today."""
    return {t: streak_of(hist, cur, t, top_n) for t in sorted(cur or {}) if streak_of(hist, cur, t, top_n)}


def week_ago(px: pd.DataFrame, asof, days: int = TRADING_DAYS):
    """The trading day `days` sessions before asof (None if the history is too short)."""
    idx = px.index[px.index <= pd.Timestamp(asof)]
    return idx[-1 - days] if len(idx) > days else None


def build(score_fn, px, asof, tickers) -> dict | None:
    """score_fn(asof) -> scored DataFrame with a 'rank' column (factors.score bound to the data)."""
    d = week_ago(px, asof)
    if d is None:
        return None
    ranks = ranks_of(score_fn(d))
    return {"asof": d.strftime("%Y-%m-%d"), "ranks": dict(sorted(ranks.items()))} if ranks else None


def diff(prev: dict | None, cur: dict | None, top_n: int, n: int = N_MOVERS) -> dict | None:
    """Mirror of weekDiff() in index.html. None when there's nothing to compare with."""
    if not prev or not cur:
        return None
    inn = lambda r: r is not None and r <= top_n
    entered = sorted((t for t in cur if inn(cur[t]) and not inn(prev.get(t))), key=lambda t: cur[t])
    left = sorted((t for t in prev if inn(prev[t]) and not inn(cur.get(t))), key=lambda t: prev[t])
    both = [t for t in cur if t in prev and prev[t] != cur[t]]
    up = sorted((t for t in both if prev[t] > cur[t]), key=lambda t: (cur[t] - prev[t], cur[t], t))
    down = sorted((t for t in both if prev[t] < cur[t]), key=lambda t: (prev[t] - cur[t], cur[t], t))
    item = lambda t: {"ticker": t, "from": prev.get(t), "to": cur.get(t)}
    return {"entered": [item(t) for t in entered], "left": [item(t) for t in left],
            "up": [item(t) for t in up[:n]], "down": [item(t) for t in down[:n]],
            "new": sorted(t for t in cur if t not in prev)}
