"""
"Invest $X": turn today's top picks into a concrete share list.

This shows what the model's rules would do with a given amount (equal dollars
in each top pick). It is arithmetic, not advice. The dashboard runs the same
math in JavaScript (planOrders in docs/index.html), and tests/test_orders.py
checks that the two versions agree.
"""
from __future__ import annotations

import math

FRAC_STEP = 1e-4   # fractional shares are rounded DOWN to 4 decimals (never overspend)


def plan(picks: list[dict], amount: float, fractional: bool = True,
         weights: dict[str, float] | None = None) -> dict:
    """picks: [{"ticker", "price"}, ...] in rank order (price may be None).

    Equal dollars per pick that HAS a price, or `weights` ({ticker: w}, re-scaled
    over the priced picks) for e.g. calmer-weighted sizing. Whole-share mode buys
    floor(target / price) shares, then spends what's left one share at a time,
    always on the pick furthest BELOW its target that still fits (ties go to
    the better rank), so weights stay as even as whole shares allow.
    """
    priced = [p for p in picks if p.get("price") and p["price"] > 0]
    rows = [{"ticker": p["ticker"], "price": p.get("price"), "target": 0.0, "shares": 0.0,
             "cost": 0.0, "note": "" if p in priced else "no price — skipped"} for p in picks]
    if not priced or amount <= 0:
        return {"rows": rows, "invested": 0.0, "leftover": max(amount, 0.0), "fractional": fractional}
    live = [r for r in rows if not r["note"]]
    raw = [(weights or {}).get(r["ticker"], 0.0) if weights else 1.0 for r in live]
    tot = sum(raw) or len(live)
    if not sum(raw):
        raw = [1.0] * len(live)
    for r, w in zip(live, raw):
        r["target"] = amount * w / tot
        if fractional:
            r["shares"] = math.floor(r["target"] / r["price"] / FRAC_STEP) * FRAC_STEP
        else:
            r["shares"] = float(math.floor(r["target"] / r["price"]))
        r["cost"] = r["shares"] * r["price"]
    if not fractional:                     # spend the leftover on the most underweight pick
        left = amount - sum(r["cost"] for r in live)
        while True:
            fits = [r for r in live if r["price"] <= left + 1e-9]
            if not fits:
                break
            r = min(fits, key=lambda r: r["cost"] / r["target"] if r["target"] else float("inf"))   # min() keeps the first on ties
            r["shares"] += 1
            r["cost"] += r["price"]
            left -= r["price"]
        for r in live:
            if r["shares"] == 0:
                r["note"] = f"1 share costs ${r['price']:,.2f} — more than this budget allows"
    invested = sum(r["cost"] for r in rows)
    return {"rows": rows, "invested": invested, "leftover": amount - invested, "fractional": fractional}



def calmer_weights(picks: list[dict]) -> dict[str, float]:
    """Inverse-volatility weights from picks[i]["vol_63d"] (see sizing.py). Sums to 1.
    A pick with no volatility gets the average weight."""
    inv = {p["ticker"]: 1 / p["vol_63d"] for p in picks if p.get("vol_63d")}
    if not inv:
        return {p["ticker"]: 1 / len(picks) for p in picks} if picks else {}
    avg = sum(inv.values()) / len(inv)
    raw = {p["ticker"]: inv.get(p["ticker"], avg) for p in picks}
    tot = sum(raw.values())
    return {t: v / tot for t, v in raw.items()}


EARN_SOON = 7   # days


def earnings_note(days_until: int | None, earn_move: float | None, within: int = EARN_SOON) -> str:
    """Heads-up for a pick that reports soon: 'reports in ~3 days; typical earnings move ±6.1%'.
    Buying right before earnings is a coin-flip on a bigger-than-usual move."""
    if days_until is None or not 0 <= days_until <= within:
        return ""
    when = "today" if days_until == 0 else f"in ~{days_until} day{'s' if days_until != 1 else ''}"
    return f"reports {when}" + (f"; typical earnings move ±{earn_move:.1%}" if earn_move else "")


def compare(top: list[str], holdings: dict[str, int | None], n_ranked: int) -> dict:
    """How your holdings line up with the model's picks.
    holdings: ticker -> current rank (None if it can't be ranked)."""
    half = n_ranked / 2
    return {
        "owned_and_picked": [t for t in top if t in holdings],
        "picked_not_owned": [t for t in top if t not in holdings],
        "owned_bottom_half": sorted([t for t, r in holdings.items() if r is not None and r > half],
                                    key=lambda t: -holdings[t]),
        "owned_unranked": [t for t, r in holdings.items() if r is None],
    }
