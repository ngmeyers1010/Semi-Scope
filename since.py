"""
"Since your last visit / last run": what changed between two snapshots.

A snapshot is a tiny summary of data.json:
    {"asof": "2026-10-12", "top": ["NVDA", ...], "ranks": {"MU": 9, ...},
     "pnl": 1234.5, "paper": 0.081, "alerts": 17}

The dashboard keeps one in your browser (localStorage) and runs the SAME logic in
JavaScript (diffSnapshots in docs/index.html); run.py keeps one in
state/prev_snapshot.json so the digest can say what changed since the last run.
tests/test_since.py checks the two languages give identical text.
"""
from __future__ import annotations

import math

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def snapshot(data: dict) -> dict:
    """The few numbers worth comparing next time."""
    ranks, price_only = {}, []
    for h in data.get("holdings") or []:
        c = h.get("current") or {}
        r = c.get("rank") if c.get("rank") is not None else c.get("would_rank")
        if r is not None:
            ranks[h["ticker"]] = int(r)
            if c.get("rank") is None and h.get("in_universe", True) is not False:
                price_only.append(h["ticker"])        # ranked on price data only (never picked)
    top = [r["ticker"] for r in sorted((r for r in data.get("rankings") or [] if r.get("rank") is not None),
                                       key=lambda r: r["rank"])][:data.get("top_n", 5)]
    mt = (data.get("my_trades") or {}).get("totals") or {}
    pst = (((data.get("paper") or {}).get("stats") or {}).get("paper") or {})
    return {"asof": data.get("prices_asof"), "top": top, "ranks": ranks, "price_only": sorted(price_only),
            "pnl": mt.get("pnl"), "paper": pst.get("total_return"),
            "alerts": len(data.get("alert_log") or [])}


def _date(s: str) -> str:
    y, m, d = (int(x) for x in s[:10].split("-"))
    return f"{MONTHS[m - 1]} {d}"


def _money(v: float) -> str:
    return ("+" if v >= 0 else "−") + "$" + f"{int(abs(v) + 0.5):,}"   # half-up, same as JS


def _fixed1(x: float) -> str:
    """x with 1 decimal, rounding exact halves UP like JavaScript's toFixed(1)
    (Python's f"{x:.1f}" rounds them to even: 0.25 -> "0.2", JS -> "0.3")."""
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(x).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _num(v) -> bool:
    """A real, finite number (not None, NaN, inf or True/False)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def valid(s) -> bool:
    return isinstance(s, dict) and isinstance(s.get("asof"), str) and len(s["asof"]) >= 10 \
        and isinstance(s.get("top"), list) and isinstance(s.get("ranks"), dict)


def diff(prev, cur: dict) -> dict:
    """{first, items: [str], text, moved: {ticker: previous rank}}"""
    if not valid(prev):
        return {"first": True, "items": [], "moved": {},
                "text": "Welcome! Next time you open this, you'll see what changed since today."}
    since = _date(prev["asof"])
    if prev["asof"] == cur["asof"]:
        return {"first": False, "items": [], "moved": {}, "text": f"Up to date: nothing new since {since}."}
    items, moved = [], {}
    entered = [t for t in cur["top"] if t not in prev["top"]]
    left = [t for t in prev["top"] if t not in cur["top"]]
    if entered:
        items.append(f"{', '.join(entered)} entered the top {len(cur['top'])}")
    if left:
        items.append(f"{', '.join(left)} left the top {len(cur['top'])}")
    for t, r in cur["ranks"].items():
        p = prev["ranks"].get(t)
        if _num(p) and _num(r) and p != r:
            moved[t] = int(p)
            items.append(f"{t} {'rose' if r < p else 'fell'} #{int(p)} → #{r}")
    # a stock that lost (or regained) its full set of stats: same number, very different meaning
    if isinstance(prev.get("price_only"), list) and isinstance(cur.get("price_only"), list):
        for t in cur["ranks"]:
            now, before = t in cur["price_only"], t in prev["price_only"]
            if now and not before and t in prev["ranks"]:
                items.append(f"{t} now ranked on price data only")
            elif before and not now:
                items.append(f"{t} fully ranked again")
    gone = [t for t in prev["ranks"] if t not in cur["ranks"]]
    if gone:
        items.append("no longer tracking " + ", ".join(gone))
    if _num(prev.get("pnl")) and _num(cur.get("pnl")):
        d = cur["pnl"] - prev["pnl"]
        if abs(d) >= 1:
            items.append(f"your P&L {_money(d)}")
    if _num(prev.get("paper")) and _num(cur.get("paper")):
        d = (cur["paper"] - prev["paper"]) * 100
        if abs(d) >= 0.05:
            items.append(f"paper portfolio {'+' if d >= 0 else '−'}{_fixed1(abs(d))} pts")
    n = (cur.get("alerts") if _num(cur.get("alerts")) else 0) - (prev.get("alerts") if _num(prev.get("alerts")) else 0)
    if n > 0:
        items.append(f"{n} new alert{'s' if n != 1 else ''}")
    text = f"Since {since}: " + "; ".join(items) + "." if items else f"Nothing new since {since}."
    return {"first": False, "items": items, "moved": moved, "text": text}
