"""
Is the strategy just piling into the hot industry group?

The model ranks ~30 stocks on growth, margins, momentum... and stocks in the same group
(Equipment, Memory, Compute, ...) tend to move together through the chip cycle. So the top 5
can easily be 3-4 stocks from ONE group, which is really one bet, not five.

Two checks:
  * capped_picks(): walk down the ranking, skip a stock once its group already has `cap`
    picks. robustness.py backtests this as "Max 2 per group": if CAGR holds up, the edge is
    stock picking; if it collapses, it was mostly group timing.
  * build(): how concentrated today's picks are, vs the backtest's past picks.
"""
from __future__ import annotations

from collections import Counter

from config import TOP_N, UNIVERSE

CAP = 2
UNKNOWN = "Other"


def group_of(ticker: str, universe: dict | None = None) -> str:
    u = UNIVERSE if universe is None else universe
    g = (u.get(ticker) or {}).get("group") if isinstance(u.get(ticker), dict) else None
    return g or UNKNOWN


def capped_picks(ranked: list[str], n: int = TOP_N, cap: int = CAP, universe: dict | None = None) -> list[str]:
    """Top n of `ranked` (best first) with at most `cap` per group. Unknown tickers count as
    their own one-stock groups, so a missing label can't block a pick. If the cap leaves fewer
    than n (too few groups), the best skipped stocks fill the rest, keeping n picks."""
    picks, counts, skipped = [], Counter(), []
    for t in ranked:
        if len(picks) == n:
            break
        g = group_of(t, universe)
        key = g if g != UNKNOWN else f"{UNKNOWN}:{t}"
        if counts[key] < cap:
            picks.append(t)
            counts[key] += 1
        else:
            skipped.append(t)
    return picks + skipped[: n - len(picks)]


def biggest_group(picks: list[str], universe: dict | None = None) -> tuple[str | None, int]:
    c = Counter(group_of(t, universe) for t in picks)
    if not c:
        return None, 0
    g, k = max(c.items(), key=lambda kv: (kv[1], kv[0] != UNKNOWN, kv[0]))
    return g, k


def build(today: list[str], quarters: list[dict], universe: dict | None = None) -> dict | None:
    """data['concentration']: today's picks vs the backtest's past picks."""
    if not today:
        return None
    g, k = biggest_group(today, universe)
    past = [biggest_group(q.get("picks") or [], universe)[1] for q in quarters or [] if q.get("picks")]
    avg = sum(past) / len(past) if past else None
    out = {"group": g, "count": k, "n": len(today), "past_avg": avg,
           "past_3plus": (sum(x >= 3 for x in past) / len(past)) if past else None,
           "groups": dict(Counter(group_of(t, universe) for t in today))}
    out["text"] = text(out)
    return out


def cap_read(robust: list[dict] | None) -> dict | None:
    """Baseline vs the 'Max 2 per group' backtest, from robustness.run() rows."""
    rows = {r.get("name"): r for r in robust or []}
    b, c = rows.get("Baseline"), rows.get(f"Max {CAP} per group")
    if not b or not c or b.get("cagr") is None or c.get("cagr") is None:
        return None
    d = c["cagr"] - b["cagr"]
    if d >= -0.02:
        verdict = "so the edge is mostly picking stocks, not just riding one group."
    elif d >= -0.05:
        verdict = "so part of the edge comes from loading up on the leading group."
    else:
        verdict = "so much of the edge is group timing: the picks work best when bunched in one group."
    return {"base_cagr": b["cagr"], "cap_cagr": c["cagr"], "diff": d,
            "text": f"Backtest with at most {CAP} per group: {c['cagr']:.1%} a year vs {b['cagr']:.1%} uncapped, {verdict}"}


def text(c: dict) -> str:
    head = (f"{c['count']} of {c['n']} picks are {c['group']}." if c["count"] >= 2
            else f"All {c['n']} picks are from different groups.")
    if c.get("past_avg") is None:
        return head
    tail = f" Past picks averaged {c['past_avg']:.1f} from one group"
    if c.get("past_3plus") is not None:
        tail += f" ({c['past_3plus']:.0%} of rebalances had 3 or more)"
    tail += "."
    if c["count"] >= 3:
        tail += " That's one big bet on the group, not several separate ones."
    return head + tail
