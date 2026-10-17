"""
Biggest score moves since the last run, and WHICH stat caused each one.

explain.explain_all() already splits every stock's score change into per-factor pieces that
add up exactly to the change (see explain.py). This module just picks the headlines:

  * only stocks whose score moved at least MIN_DELTA (0.15 ≈ a noticeable jump in rank)
  * the biggest N moves, up or down
  * one plain sentence each: "MU +0.42 (#9 → #4): mostly Revenue growth YoY +12.0% → +31.0% (+0.30)"

"Mostly" is used only when one stat explains at least half the move; otherwise the sentence
names the top two, because a move spread across several stats is a different story
(often: the other stocks changed, not this one).
"""
from __future__ import annotations

import explain

MIN_DELTA = 0.15
TOP_N_MOVES = 5


def _label(labels: dict, f: str) -> str:
    return (labels.get(f) or f).split(" (")[0]


def _what(d: dict) -> str:
    if d["status"] == "new":
        return "now available"
    if d["status"] == "dropped":
        return "no longer available"
    return f"{explain._fmt_raw(d['factor'], d['raw_prev'])} → {explain._fmt_raw(d['factor'], d['raw_now'])}"


def _rank(r) -> str | None:
    return None if r is None else f"#{int(r)}"


def sentence(m: dict, labels: dict) -> str:
    rk = ""
    if m.get("rank_prev") is not None and m.get("rank_now") is not None and int(m["rank_prev"]) != int(m["rank_now"]):
        rk = f" ({_rank(m['rank_prev'])} → {_rank(m['rank_now'])})"
    ds = m["drivers"]
    head = f"{m['ticker']} {m['delta']:+.2f}{rk}: "
    if not ds:
        return head + "no single stat stands out."
    top = ds[0]
    if abs(top["contrib"]) >= 0.5 * abs(m["delta"]) and (top["contrib"] > 0) == (m["delta"] > 0):
        return head + f"mostly {_label(labels, top['factor'])} {_what(top)} ({top['contrib']:+.2f})."
    parts = [f"{_label(labels, d['factor'])} {_what(d)} ({d['contrib']:+.2f})" for d in ds[:2]]
    return head + "spread out: " + "; ".join(parts) + "."


def build(run_expl: dict | None, labels: dict, min_delta: float = MIN_DELTA, n: int = TOP_N_MOVES) -> list[dict]:
    """run_expl: data['explain']['run'] (ticker -> explain_change() result + rank_prev/now).
    Empty on the first run, or when nothing moved enough."""
    out = []
    for t, e in (run_expl or {}).items():
        d = e.get("delta")
        if d is None or abs(d) < min_delta:
            continue
        m = {"ticker": t, "delta": d, "score_prev": e.get("score_prev"), "score_now": e.get("score_now"),
             "rank_prev": e.get("rank_prev"), "rank_now": e.get("rank_now"),
             "drivers": [x for x in e.get("drivers") or [] if abs(x.get("contrib") or 0) > 1e-9][:3]}
        m["text"] = sentence(m, labels)
        out.append(m)
    out.sort(key=lambda m: (-abs(m["delta"]), m["ticker"]))
    return out[:n]
