"""
Does a top-5 streak mean anything?

The Rankings tab now shows "5+ wk in top 5". Is a stock that STAYS in the picks any better
than one that just arrived? The backtest already answers it, with no extra scoring:

  * each quarterly rebalance has its picks and each pick's return over the next 3 months
  * a pick is a STAYER if it was also picked at the previous rebalance (held 2+ quarters in
    a row), and NEW otherwise. The first rebalance is skipped: we can't tell which it is.
  * excess = the pick's return minus the average stock's (equal-weight universe) that quarter

Point in time: whether a pick is a stayer uses only the previous and current picks, both known
on the rebalance day. Returns are only used to measure afterwards.

The test: for each quarter that has both kinds, (stayers' average excess − new picks' average
excess). t-test on those quarterly differences (confidence.t_test), because picks in the same
quarter rise and fall together and aren't independent of each other.
"""
from __future__ import annotations

import math

import confidence

MIN_N = 12           # picks per group below this: "too few to tell"


def classify(quarters: list[dict]) -> list[dict]:
    """[{date, stay: [excess...], new: [excess...]}] for each rebalance after the first."""
    out = []
    for prev, q in zip(quarters, quarters[1:]):
        u = q.get("universe")
        if not q.get("picks") or u is None or not math.isfinite(u):     # still-open quarter: no result yet
            continue
        before = set(prev.get("picks") or []) if prev.get("end") == q.get("date") else set()
        row = {"date": q["date"], "stay": [], "new": []}
        for t in q["picks"]:
            r = (q.get("pick_returns") or {}).get(t)
            if r is None or not math.isfinite(r):
                continue
            row["stay" if t in before else "new"].append(r - u)
        out.append(row)
    return out


def _r(v, k=5):
    return None if v is None else round(float(v), k)


def _group(xs: list[float]) -> dict:
    n = len(xs)
    return {"n": n, "avg_excess": _r(sum(xs) / n) if n else None, "hit_rate": _r(sum(x > 0 for x in xs) / n, 4) if n else None}


def build(quarters: list[dict] | None) -> dict | None:
    rows = classify(quarters or [])
    stay = [x for r in rows for x in r["stay"]]
    new = [x for r in rows for x in r["new"]]
    if not stay or not new:
        return None
    s, n = _group(stay), _group(new)
    diffs = [sum(r["stay"]) / len(r["stay"]) - sum(r["new"]) / len(r["new"]) for r in rows if r["stay"] and r["new"]]
    tt = confidence.t_test(diffs)
    out = {"stayers": s, "new": n, "diff": _r(s["avg_excess"] - n["avg_excess"]), "quarters": tt["n"],
           "diff_q": _r(tt["mean"]), "t": _r(tt["t"], 3)}
    out["read"] = read(out)
    return out


def read(r: dict) -> str:
    s, n = r["stayers"], r["new"]
    pp = lambda v: f"{v * 100:+.1f}%"
    base = (f"Stocks still picked from the previous quarter beat the average stock by {pp(s['avg_excess'])} a quarter "
            f"({s['n']} picks); newly picked ones by {pp(n['avg_excess'])} ({n['n']} picks).")
    if min(s["n"], n["n"]) < MIN_N or r["quarters"] < 4:
        return base + f" Too few to tell yet (want at least {MIN_N} of each)."
    t = r["t"]
    if t is None:
        return base + " The gap is the same every quarter, so there's no spread to test."
    who = "stayers" if r["diff_q"] > 0 else "new picks"
    if abs(t) >= 2:
        return base + f" Over {r['quarters']} quarters the {who} came out ahead (t {t:.1f}): a streak looks like it means something."
    return base + (f" Over {r['quarters']} quarters the gap could easily be luck (t {t:.1f}, want 2+): "
                   "a long streak is not, by itself, a reason to trust a pick more.")
