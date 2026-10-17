"""
Sector rotation: which semis industry groups are leading?

For each group (Memory/Storage, Compute, Equipment, Analog/Power, Systems, ...):
  * an equal-weight price index (average of members' DAILY returns, compounded)
  * 1m / 3m / 6m return minus SOXX ("relative strength")
  * breadth: share of members trading above their 50-day average
  * the model's view: average composite score and how many members are in the top 10

Leadership rank = sorted by 3-month relative strength (best first).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONS = {"1m": 21, "3m": 63, "6m": 126}


def group_index(px: pd.DataFrame, members: list[str]) -> pd.Series:
    """Equal-weight index starting at 1.0: each day, the average return of the members that
    have a price that day (a member with no data simply doesn't count that day)."""
    cols = [t for t in members if t in px]
    if not cols:
        return pd.Series(dtype=float)
    has = px[cols].notna().any(axis=1)
    if not has.any():
        return pd.Series(dtype=float)
    # start on the first day ANY member traded: otherwise the days before a new listing count
    # as flat history, and a 3-month-old group would get a (fake) 6-month return
    sub = px.loc[has.idxmax():, cols]
    r = sub.pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0.0)
    return (1 + r).cumprod()


def breadth(px: pd.DataFrame, members: list[str], window: int = 50) -> float | None:
    """Share of members whose last price is above their own `window`-day average."""
    above, n = 0, 0
    for t in members:
        if t not in px:
            continue
        p = px[t].dropna()
        if len(p) < window:
            continue
        n += 1
        above += bool(p.iloc[-1] > p.iloc[-window:].mean())
    return above / n if n else None


def _ret(s: pd.Series, n: int) -> float | None:
    s = s.dropna()
    return float(s.iloc[-1] / s.iloc[-1 - n] - 1) if len(s) > n else None


def build(px: pd.DataFrame, bench: pd.DataFrame, meta: dict, ranked: pd.DataFrame | None = None,
          top_k: int = 10) -> dict:
    """{'groups': [...sorted by leadership], 'index': {group: [[date, value], ...]}, 'read': str}"""
    members: dict[str, list[str]] = {}
    for t, m in meta.items():
        members.setdefault(m.get("group", "Other"), []).append(t)
    soxx = bench["SOXX"].dropna() if bench is not None and "SOXX" in bench else None
    top = []
    if ranked is not None and len(ranked):
        top = list(ranked["score"].dropna().sort_values(ascending=False).index[:top_k])
    rows, idx_out = [], {}
    last_year = px.index[-252] if len(px) > 252 else px.index[0]
    for g, ts in members.items():
        idx = group_index(px, ts)
        if idx.empty:
            continue
        row = {"group": g, "n": sum(t in px for t in ts), "members": [t for t in ts if t in px]}
        for k, n in HORIZONS.items():
            gr, br = _ret(idx, n), (_ret(soxx, n) if soxx is not None else None)
            row[f"ret_{k}"] = gr
            row[f"rel_{k}"] = None if gr is None or br is None else gr - br
        row["breadth"] = breadth(px, ts)
        if ranked is not None and len(ranked):
            sc = ranked["score"].reindex([t for t in ts if t in ranked.index]).dropna()
            row["avg_score"] = float(sc.mean()) if len(sc) else None
        else:
            row["avg_score"] = None
        row["in_top"] = sum(t in top for t in ts)
        rows.append(row)
        one = idx.loc[last_year:]
        idx_out[g] = [[d.strftime("%Y-%m-%d"), round(float(v / one.iloc[0]), 4)]
                      for d, v in one.iloc[::5].items()]
    if soxx is not None:
        s = soxx.loc[last_year:]
        idx_out["SOXX"] = [[d.strftime("%Y-%m-%d"), round(float(v / s.iloc[0]), 4)] for d, v in s.iloc[::5].items()]
    rows.sort(key=lambda r: -(r["rel_3m"] if r["rel_3m"] is not None else -np.inf))
    for i, r in enumerate(rows, 1):
        r["leader_rank"] = i
    return {"groups": rows, "index": idx_out, "top_k": top_k, "read": read(rows, len(top))}


def read(rows: list[dict], n_top: int) -> str:
    """'Equipment leading, Memory/Storage lagging (3-month vs SOXX); the model's top 10 is 40% Equipment.'"""
    ok = [r for r in rows if r.get("rel_3m") is not None]
    if not ok:
        return "Not enough price history to compare groups yet."
    one = lambda r: " (1 stock)" if r["n"] == 1 else ""
    s = f"{ok[0]['group']}{one(ok[0])} leading ({ok[0]['rel_3m']:+.0%} vs SOXX over 3 months)"
    if len(ok) > 1:
        s += f", {ok[-1]['group']}{one(ok[-1])} lagging ({ok[-1]['rel_3m']:+.0%})"
    if n_top:
        heavy = max(rows, key=lambda r: r["in_top"])
        if heavy["in_top"]:
            s += f"; the model's top {n_top} is {heavy['in_top'] / n_top:.0%} {heavy['group']}"
    return s + "."
