"""
Weekly review: a one-screen summary for a study session, plus 3 questions to think about.

The questions are built from this week's data so they're always about something real:
  * a holding whose rank moved a lot since the last rebalance  -> which stat drove it?
  * a stock at an extreme of its own P/S range                 -> what would make it cheap/pricey?
  * the strategy's worst 1-year stretch vs SPY                 -> would you have held?
  * a holding reporting earnings soon                          -> what's priced in?
  * the leading / lagging industry group                       -> rotation or noise?
  * 3+ of the top picks from one industry group                -> one bet or several?
  * the edge fading faster / lasting longer than the 3-month hold -> rebalance more / less often?
  * the newest stock in the top N this week                    -> why did it climb?

Plus a one-line "This week in the rankings" summary (rankings_week) from week_diff.py: who
joined / left the top N since 5 trading days ago, and the longest top-N streak.

Each question has a link that opens the right spot on the dashboard (index.html#stock=MU,
#tab=bt&card=steady-card scrolls to that card, ...). weekly.html renders data["weekly"] plus a few blocks it reads directly.
Pure function of the data dict: no I/O, easy to test.
"""
from __future__ import annotations

import valuation
import week_diff

N_QUESTIONS = 3


def _rank_mover(data: dict) -> dict | None:
    """Holding whose rank moved most since the last quarterly rebalance (explain.py's numbers,
    so the hint below explains exactly that move)."""
    ex = data.get("explain") or {}
    reb, since = ex.get("rebalance") or {}, ex.get("rebalance_date")
    best = None
    for h in data.get("holdings") or []:
        e = reb.get(h["ticker"]) or {}
        r0, r1 = e.get("rank_prev"), e.get("rank_now")
        if r0 is None or r1 is None or int(r0) == int(r1):
            continue
        if best is None or abs(r1 - r0) > abs(best["to"] - best["from"]):
            best = {"ticker": h["ticker"], "from": int(r0), "to": int(r1)}
    if not best:
        return None
    verb = "fell" if best["to"] > best["from"] else "rose"
    q = (f"{best['ticker']} {verb} from #{best['from']} to #{best['to']} since the {since} rebalance. "
         f"Which stat drove it, and do you think that change will last?")
    return {"kind": "mover", "q": q, "hint": (ex.get("rebalance_text") or {}).get(best["ticker"]),
            "link": f"index.html#stock={best['ticker']}"}


def _rank(r):
    return "unranked" if r is None else f"#{r}"


def _week(data: dict):
    """(diff, streaks, history, top_n) from week_diff, or None without last week's ranks."""
    w = data.get("week_ranks") or {}
    cur, top_n = week_diff.ranks_of(data.get("rankings") or []), int(data.get("top_n") or 5)
    d = week_diff.diff(w.get("ranks"), cur, top_n)
    if d is None:
        return None
    hist = data.get("rank_history") or []
    return d, week_diff.streaks(hist, cur, top_n), hist, top_n


def _names(xs: list) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _move(x: dict) -> str:
    return f"{x['ticker']} ({_rank(x['from'])} → {_rank(x['to'])})"


def rankings_week(data: dict) -> dict | None:
    """One line for the weekly review, e.g. 'MPWR (#6 → #4) joined the top 5; AVGO (#4 → #6) dropped
    out. Longest streak: ANET, AAPL and INTC (5+ weeks in the top 5).' None without last week's ranks."""
    got = _week(data)
    if not got:
        return None
    d, st, hist, top_n = got
    parts = []
    if d["entered"]:
        parts.append(f"{_names([_move(x) for x in d['entered']])} joined the top {top_n}")
    if d["left"]:
        parts.append(f"{_names([_move(x) for x in d['left']])} dropped out")
    text = ("; ".join(parts) + ".") if parts else f"Same top {top_n} as last week."
    longest = max(st.values()) if st else 0
    if longest >= 2:
        cur = week_diff.ranks_of(data.get("rankings") or [])
        who = sorted((t for t in st if st[t] == longest), key=lambda t: (cur[t], t))
        plus = "+" if longest == len(hist) + 1 else ""
        text += f" Longest streak: {_names(who)} ({longest}{plus} weeks in the top {top_n})."
    return {"asof": (data.get("week_ranks") or {}).get("asof"), "text": text,
            "link": "index.html#tab=rank&card=week-card"}


def _entered(data: dict) -> dict | None:
    """The best-ranked stock that joined the top N this week: why did it climb?"""
    got = _week(data)
    if not got or not got[0]["entered"]:
        return None
    e, top_n = got[0]["entered"][0], got[3]
    t = e["ticker"]
    frm = "from outside the rankings" if e["from"] is None else f"from #{e['from']}"
    q = (f"{t} joined the top {top_n} this week ({frm} to #{e['to']}). Which stat moved it up, and is it the "
         f"kind of change that lasts a quarter, or a few good days of price?")
    ex = data.get("explain") or {}
    run, reb = (ex.get("run_text") or {}).get(t), (ex.get("rebalance_text") or {}).get(t)
    if run:
        hint = f"Since the last update ({ex.get('run_date')}): {run}"
    elif reb:
        hint = f"Since the {ex.get('rebalance_date')} rebalance: {reb}"
    else:
        hint = "Open it and compare its stats with the stock it replaced."
    return {"kind": "entered", "q": q, "hint": hint, "link": f"index.html#tab=rank&card=week-card&stock={t}"}


def _valuation_extreme(data: dict) -> dict | None:
    """Owned stock or current pick sitting at the cheap or pricey end of its own P/S range."""
    owned = {h["ticker"] for h in data.get("holdings") or []}
    top_n = data.get("top_n", 5)
    cands = []
    for r in (data.get("rankings") or []) + (data.get("watchlist") or []):
        v = r.get("valuation") or {}
        p = v.get("pct")
        if p is None:
            continue
        mine = r["ticker"] in owned or (r.get("rank") is not None and r["rank"] <= top_n)
        if mine and (p >= valuation.EXTREME_HI or p <= valuation.EXTREME_LO):
            cands.append((abs(p - 50), r["ticker"], p, v.get("ps")))
    if not cands:
        return None
    _, t, p, ps = max(cands)
    if p >= valuation.EXTREME_HI:
        q = (f"{t} trades at {ps:.1f}× sales, the {valuation.ordinal(p)} percentile of its own 5-year range. "
             f"What would have to be true for that price to still be cheap?")
    else:
        q = (f"{t} trades at {ps:.1f}× sales, the {valuation.ordinal(p)} percentile of its own 5-year range. "
             f"Is it cheap, or is the market expecting sales to fall?")
    return {"kind": "valuation", "q": q, "hint": "Look at its revenue trend in the stock details.",
            "link": f"index.html#stock={t}"}


def _worst_year(data: dict) -> dict | None:
    st = data.get("steady") or {}
    s = st.get("paper") if (st.get("paper") or {}).get("available") else st.get("backtest")
    if not s or not s.get("available") or (s.get("worst") or {}).get("excess", 0) >= 0:
        return None
    w = s["worst"]
    q = (f"The strategy's worst 1-year stretch ({w['start'][:7]} to {w['end'][:7]}) trailed SPY by "
         f"{abs(w['excess']):.0%}. Would you have kept following it through that year? What would make you quit?")
    return {"kind": "steady", "q": q, "hint": "Is the edge steady? card on the Backtest tab.", "link": "index.html#tab=bt&card=steady-card"}


def _earnings_soon(data: dict) -> dict | None:
    rows = [r for r in ((data.get("earnings_cal") or {}).get("rows") or [])
            if r.get("owned") and r.get("move") and 0 <= r.get("days", 99) <= 21]
    if not rows:
        return None
    r = min(rows, key=lambda x: (x["days"], -x["move"]))
    q = (f"{r['ticker']} reports in about {r['days']} days and usually moves ±{r['move'] * 100:.1f}% the next day. "
         f"Would a move that size change your plan for it?")
    return {"kind": "earnings", "q": q, "hint": "Earnings coming up, on the My stocks tab.", "link": "index.html#tab=mine&card=ecal-card"}


def _groups(data: dict) -> dict | None:
    rows = [g for g in ((data.get("groups") or {}).get("groups") or []) if g.get("rel_3m") is not None]
    if len(rows) < 2:
        return None
    lead, lag = rows[0], rows[-1]
    q = (f"{lead['group']} is leading SOXX by {lead['rel_3m']:+.0%} over 3 months and {lag['group']} lags at "
         f"{lag['rel_3m']:+.0%}. Is that a real rotation, or one or two stocks moving the average?")
    return {"kind": "groups", "q": q, "hint": "Check each group's breadth and member count.", "link": "index.html#tab=rank&card=groups-card"}


def _decay(data: dict) -> dict | None:
    """Only when the signal-decay study says the 3-month hold might be the wrong pace."""
    k = (data.get("research") or {}).get("decay") or {}
    if k.get("suggest") not in ("faster", "slower"):
        return None
    pace = "more often" if k["suggest"] == "faster" else "less often"
    q = (f"{k['read']} Would you rebalance {pace}? What would the extra or saved trading cost, "
         f"and how would you test it without fooling yourself?")
    return {"kind": "decay", "q": q, "hint": "How long does a pick's edge last? card on the Factor report card tab.",
            "link": "index.html#tab=res&card=decay-card"}


def _concentration(data: dict) -> dict | None:
    c = data.get("concentration") or {}
    if (c.get("count") or 0) < 3 or not c.get("group"):
        return None
    q = (f"{c['count']} of the {c['n']} top picks are {c['group']}. If that group has a bad quarter, they "
         f"probably all fall together. Is that one bet or {c['count']}? Would you cap it?")
    return {"kind": "concentration", "q": q, "hint": (c.get("cap") or {}).get("text") or "Group concentration card.",
            "link": "index.html#tab=paper&card=conc-card"}


def questions(data: dict, n: int = N_QUESTIONS) -> list[dict]:
    """Up to n distinct questions, most specific first. Never raises on missing data."""
    out = []
    for make in (_rank_mover, _entered, _concentration, _valuation_extreme, _decay, _worst_year, _earnings_soon, _groups):
        try:
            q = make(data)
        except (KeyError, TypeError, ValueError, IndexError, AttributeError):
            q = None                                  # odd data: skip that question, keep the rest
        if q and q["q"] not in {x["q"] for x in out}:
            out.append(q)
        if len(out) == n:
            break
    return out


def build(data: dict) -> dict:
    try:
        rw = rankings_week(data)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        rw = None
    return {"asof": data.get("prices_asof"), "questions": questions(data), "rankings_week": rw}
