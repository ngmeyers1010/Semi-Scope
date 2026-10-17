"""
Performance attribution: WHO made (or lost) the money?

Each quarter the portfolio holds N stocks with equal starting weight w = 1/N and
buys-and-holds, so the quarter's return is exactly  sum(w * stock_return).
Each stock's *contribution* is its w * return. Adding contributions up across
quarters (in percentage points) shows which stocks and which industry groups
actually drove results — and whether the strategy depends on one lucky stock.
"""
from __future__ import annotations

import math

import pandas as pd


def _num(x) -> float:
    return 0.0 if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


def quarter_contributions(q: dict, meta: dict) -> dict:
    """{stocks: {ticker: contribution}, groups: {group: contribution}, total} for one quarter."""
    picks = q["picks"]
    w = 1 / len(picks) if picks else 0
    stocks = {t: w * _num(q["pick_returns"].get(t)) for t in picks}
    groups: dict[str, float] = {}
    for t, c in stocks.items():
        g = meta.get(t, {}).get("group", "Other")
        groups[g] = groups.get(g, 0.0) + c
    return {"stocks": stocks, "groups": groups, "total": sum(stocks.values())}


def build(quarters: list[dict], meta: dict, top: int = 10) -> dict:
    """Whole-backtest attribution by stock and by group."""
    rows = []
    for q in quarters:
        qc = quarter_contributions(q, meta)
        q["contrib"] = {k: round(v, 5) for k, v in qc["stocks"].items()}
        q["contrib_groups"] = {k: round(v, 5) for k, v in qc["groups"].items()}
        for t in q["picks"]:
            r = _num(q["pick_returns"].get(t))
            rows.append({"ticker": t, "group": meta.get(t, {}).get("group", "Other"),
                         "contrib": qc["stocks"][t], "ret": r,
                         "excess": r - _num(q.get("universe"))})
    if not rows:
        return {"stocks": [], "groups": [], "helpers": [], "hurters": []}
    df = pd.DataFrame(rows)
    by_stock = (df.groupby("ticker")
                  .agg(group=("group", "first"), contrib=("contrib", "sum"), times=("ret", "size"),
                       avg_ret=("ret", "mean"), hit=("excess", lambda s: float((s > 0).mean())))
                  .sort_values("contrib", ascending=False))
    by_group = (df.groupby("group")
                  .agg(contrib=("contrib", "sum"), picks=("ret", "size"), avg_ret=("ret", "mean"))
                  .sort_values("contrib", ascending=False))
    to_rows = lambda d: [{"ticker" if d.index.name == "ticker" else "group": i, **{k: v for k, v in r.items()}}
                         for i, r in d.iterrows()]
    stocks = to_rows(by_stock)
    total = float(df["contrib"].sum())
    top_share = float(by_stock["contrib"].head(3).sum() / total) if total > 0 else None
    return {
        "stocks": stocks,
        "groups": to_rows(by_group),
        "helpers": stocks[:top],
        "hurters": list(reversed(stocks))[:top],
        "total_contrib": total,
        "top3_share": top_share,  # share of all gains from the 3 biggest winners (concentration check)
    }


def paper(entries: list[dict], px: pd.DataFrame, meta: dict) -> list[dict]:
    """Contribution per pick for each logged paper period (to the next entry, or today)."""
    out = []
    for i, e in enumerate(entries):
        end = pd.Timestamp(entries[i + 1]["date"]) if i + 1 < len(entries) else px.index[-1]
        rets = {}
        for t in e["picks"]:
            s = px[t].loc[:end].dropna() if t in px else pd.Series(dtype=float)
            rets[t] = float(s.iloc[-1] / e["entry_prices"][t] - 1) if len(s) else 0.0
        qc = quarter_contributions({"picks": e["picks"], "pick_returns": rets}, meta)
        out.append({"date": e["date"], "end": end.strftime("%Y-%m-%d"),
                    "stocks": qc["stocks"], "groups": qc["groups"], "total": qc["total"]})
    return out
