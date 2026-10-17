"""
Next-rebalance preview for the paper portfolio.

The paper portfolio buys the model's top picks in equal amounts on the first trading day of
Mar/Jun/Sep/Dec, then holds. Between rebalances the weights DRIFT: winners grow, losers
shrink. This module answers, without touching the real portfolio:

  * when is the next rebalance?            (same calendar rule as the backtest)
  * how far have the weights drifted?      (current weight vs the equal target)
  * if it rebalanced today, what changes?  (sell / buy / keep, using today's ranking)
  * how much trading would that be?        (share replaced, and cost at COST_BPS per side)

Informational only: paper.update() still records picks only on real rebalance dates.
"""
from __future__ import annotations

import math

import pandas as pd

from backtest import rebalance_dates
from config import COST_BPS, TOP_N

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def next_date(asof) -> pd.Timestamp:
    """First weekday of the next rebalance month after `asof` (holidays not known in advance,
    so this can be a day early: shown as '≈')."""
    a = pd.Timestamp(asof).normalize()
    # the calendar must start at the beginning of this month: rebalance_dates() takes the FIRST
    # day it sees in each month, so starting mid-December would wrongly call Dec 16 a rebalance
    days = pd.bdate_range(a.replace(day=1), a + pd.Timedelta(days=130))
    return rebalance_dates(days, a + pd.Timedelta(days=1))[0]


def drift(entry: dict, prices: dict) -> dict[str, float]:
    """Current weight of each pick, starting from equal weights at entry prices.
    A pick with no current price counts as flat (its entry price)."""
    picks = entry.get("picks") or []
    if not picks:
        return {}
    ep = entry.get("entry_prices") or {}
    grown = {}
    for t in picks:
        e, p = ep.get(t), prices.get(t)
        ok = lambda x: x is not None and isinstance(x, (int, float)) and math.isfinite(x) and x > 0
        grown[t] = (p / e) if ok(e) and ok(p) else 1.0
    tot = sum(grown.values())
    return {t: g / tot for t, g in grown.items()}


def preview(entry: dict | None, prices: dict, ranked: list[str], asof, top_n: int = TOP_N,
            cost_bps: float = COST_BPS) -> dict | None:
    """Everything the card shows, or None before the paper portfolio has started.
    `ranked`: today's tickers, best first (ranked stocks only)."""
    if not entry or not entry.get("picks"):
        return None
    w_now = drift(entry, prices)
    new = list(ranked[:top_n])
    w_new = {t: 1 / len(new) for t in new} if new else {}
    held = list(w_now)
    sell = [t for t in held if t not in w_new]
    buy = [t for t in new if t not in w_now]
    keep = [t for t in held if t in w_new]
    turnover = sum(abs(w_new.get(t, 0) - w_now.get(t, 0)) for t in set(w_now) | set(w_new))  # both sides
    nd = next_date(asof)
    out = {
        "next_date": nd.strftime("%Y-%m-%d"),
        "days": int((nd - pd.Timestamp(asof).normalize()).days),
        "since": entry.get("date"),
        "weights": [{"ticker": t, "now": round(w, 4), "target": round(1 / len(held), 4)} for t, w in w_now.items()],
        "sell": sell, "buy": buy, "keep": keep,
        "replaced": round(turnover / 2, 4),            # share of the portfolio that changes hands
        "cost": round(turnover * cost_bps / 1e4, 5),   # same formula the backtest charges
    }
    out["text"] = sentence(out)
    return out


def sentence(p: dict) -> str:
    """'Next rebalance ≈Dec 1 (in 47 days). If it were today: sell INTC, buy KLAC; 1 of 5 change …'"""
    d = pd.Timestamp(p["next_date"])
    head = f"Next rebalance ≈{MONTHS[d.month - 1]} {d.day} (in {p['days']} days)."
    n = len(p["keep"]) + len(p["sell"])
    if not p["sell"] and not p["buy"]:
        if p["replaced"] < 0.005:
            return head + f" If it were today: no changes. The same {n} picks, already at equal weights."
        return head + f" If it were today: the same {n} picks, trimmed back to equal weights " \
                      f"({p['replaced']:.0%} of the portfolio, ~{p['cost']:.2%} cost)."
    parts = []
    if p["sell"]:
        parts.append("sell " + ", ".join(p["sell"]))
    if p["buy"]:
        parts.append("buy " + ", ".join(p["buy"]))
    return head + (f" If it were today: {'; '.join(parts)}; {len(p['sell'])} of {n} change "
                   f"({p['replaced']:.0%} of the portfolio, ~{p['cost']:.2%} cost).")
