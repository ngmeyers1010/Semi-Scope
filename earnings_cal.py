"""
Earnings season, planned: when each of your stocks (and the model's picks) reports next,
and how much it has usually moved the day after.

Everything comes from data the pipeline already has, no new downloads:
  * filings.build()        -> next_filing: the expected next 10-Q/10-K date (an ESTIMATE from the
                              company's usual filing rhythm; the earnings call is often the same
                              day or a little earlier)
  * earnings_moves.build() -> avg_abs: the average size of the first-day move after the last
                              8 filings, pct_up, and each past reaction

"Expected-move band" = last price × (1 ± avg_abs). It says how BIG a typical reaction is,
never which WAY: past direction doesn't predict the next one.
"""
from __future__ import annotations

import math

import pandas as pd

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DIGEST_DAYS = 14


def bucket(asof, when) -> str:
    """'This week' / 'Next week' / 'Later', with weeks running Monday-Sunday around `asof`."""
    a, w = pd.Timestamp(asof).normalize(), pd.Timestamp(when).normalize()
    monday = a - pd.Timedelta(days=a.weekday())
    if w < monday + pd.Timedelta(days=7):
        return "This week"
    if w < monday + pd.Timedelta(days=14):
        return "Next week"
    return "Later"


def band(price, move) -> list[float] | None:
    """[low, high] = price × (1 ± move), or None without a price or a usable move."""
    if price is None or move is None or not (price > 0) or not math.isfinite(move) or move <= 0:
        return None
    return [round(price * (1 - move), 2), round(price * (1 + move), 2)]


def sentence(r: dict) -> str:
    """'NVDA ≈Nov 4 (in 20 days): usually moves ±6.1% the next day (≈$170–$192); up 5 of last 8.'"""
    d = pd.Timestamp(r["date"])
    when = f"{MONTHS[d.month - 1]} {d.day}"
    days = r["days"]
    rel = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days" if days > 1 else "any day now"
    s = f"{r['ticker']} ≈{when} ({rel})"
    if r.get("move") is None:
        return s + ": no earnings-day history yet."
    s += f": usually moves ±{r['move'] * 100:.1f}% the next day"
    if r.get("band"):
        lo, hi = r["band"]
        # same style both ends; whole dollars round halves UP, like the page's Math.round
        fmt = (lambda x: f"${int(math.floor(x + 0.5)):,}") if lo >= 100 else (lambda x: f"${x:,.2f}")
        s += f" (≈{fmt(lo)}–{fmt(hi)})"
    if r.get("n"):
        s += f"; up {r['ups']} of last {r['n']}"
    return s + "."


def build(rows: list[dict], asof, owned: set[str], picks: set[str]) -> dict:
    """rows: stock records with ticker, last_price, filing {next_filing, days_until} and
    earnings {avg_abs, n, pct_up, events}. Returns {'asof', 'rows': [...sorted by date]}."""
    out, seen = [], set()
    for rec in rows:
        t = rec.get("ticker")
        if t in seen or t not in owned | picks:
            continue
        f = rec.get("filing") or {}
        if not f.get("next_filing") or f.get("days_until") is None:
            continue                                   # no estimate: nothing to put on a calendar
        seen.add(t)
        e = rec.get("earnings") or {}
        move = e.get("avg_abs")
        move = float(move) if move is not None and math.isfinite(move) and move > 0 else None
        ev = [x for x in e.get("events") or [] if x.get("ret") is not None]
        big = max(ev, key=lambda x: abs(x["ret"])) if ev else None
        row = {"ticker": t, "date": f["next_filing"], "days": int(f["days_until"]),
               "week": bucket(asof, f["next_filing"]), "owned": t in owned, "pick": t in picks,
               "move": None if move is None else round(move, 4),
               "band": band(rec.get("last_price"), move),
               "n": len(ev) or None, "ups": sum(x["ret"] > 0 for x in ev) if ev else None,
               "biggest": None if big is None else {"day": big.get("day"), "ret": round(big["ret"], 4)}}
        row["text"] = sentence(row)
        out.append(row)
    out.sort(key=lambda r: (r["date"], r["ticker"]))
    return {"asof": str(pd.Timestamp(asof).date()), "rows": out}


def digest_items(cal: dict | None, days: int = DIGEST_DAYS) -> list[str]:
    """Plain-text lines for the next `days` days (empty list = no digest section)."""
    return [r["text"] for r in ((cal or {}).get("rows") or []) if 0 <= r["days"] <= days]
