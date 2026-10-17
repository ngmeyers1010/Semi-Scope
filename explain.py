"""
Why did a stock's score change? Break the move into each factor's share.

The composite score is a weighted average of the factor z-scores a stock has:

    score = Σ w_f · z_f / W        (W = sum of weights of the factors it HAS)

so each factor's contribution to the change is

    c_f = w_f · z_f(now) / W_now  −  w_f · z_f(before) / W_before

and the contributions add up EXACTLY to the score change, even when a factor
appears (new data) or disappears (missing data) and W changes.
When the factor set doesn't change this is simply w_f · Δz_f / W.
"""
from __future__ import annotations

import math


def _num(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def explain_change(z_prev: dict, z_now: dict, weights: dict, raw_prev: dict | None = None,
                   raw_now: dict | None = None) -> dict:
    """z_prev/z_now: factor -> z-score (None/NaN = missing) for ONE stock.
    weights: factor -> weight (factors with weight 0 are ignored).
    Returns {delta, drivers: [...sorted by |contribution|]}."""
    w = {f: wt for f, wt in weights.items() if wt > 0}
    zp = {f: _num(z_prev.get(f)) for f in w}
    zn = {f: _num(z_now.get(f)) for f in w}
    Wp = sum(w[f] for f in w if zp[f] is not None)
    Wn = sum(w[f] for f in w if zn[f] is not None)
    drivers = []
    for f in w:
        before = w[f] * zp[f] / Wp if zp[f] is not None and Wp else 0.0
        after = w[f] * zn[f] / Wn if zn[f] is not None and Wn else 0.0
        status = ("new" if zp[f] is None and zn[f] is not None else
                  "dropped" if zp[f] is not None and zn[f] is None else
                  "missing" if zp[f] is None else "changed")
        if status == "missing":
            continue
        drivers.append({"factor": f, "contrib": after - before, "z_prev": zp[f], "z_now": zn[f],
                        "raw_prev": _num((raw_prev or {}).get(f)), "raw_now": _num((raw_now or {}).get(f)),
                        "status": status})
    drivers.sort(key=lambda d: -abs(d["contrib"]))
    s_prev = sum(w[f] * zp[f] for f in w if zp[f] is not None) / Wp if Wp else None
    s_now = sum(w[f] * zn[f] for f in w if zn[f] is not None) / Wn if Wn else None
    delta = (s_now - s_prev) if s_prev is not None and s_now is not None else None
    return {"delta": delta, "score_prev": s_prev, "score_now": s_now, "drivers": drivers}


def _fmt_raw(f: str, v: float | None) -> str:
    if v is None:
        return "—"
    if f in ("inv_days_change",):
        return f"{v:+.0f}d"
    if f == "low_vol":
        return f"{v:.0%}"
    return f"{v:+.1%}" if abs(v) < 5 else f"{v:,.1f}"


def sentence(exp: dict, labels: dict, n: int = 2) -> str:
    """'Inventory-days change +4d → +27d (−0.42); Momentum ... (+0.10)'"""
    parts = []
    for d in exp["drivers"][:n]:
        lab = labels.get(d["factor"], d["factor"]).split(" (")[0]
        if d["status"] == "new":
            what = "now available"
        elif d["status"] == "dropped":
            what = "no longer available"
        else:
            what = f"{_fmt_raw(d['factor'], d['raw_prev'])} → {_fmt_raw(d['factor'], d['raw_now'])}"
        parts.append(f"{lab} {what} ({d['contrib']:+.2f})")
    return "; ".join(parts)


def explain_all(prev_rows: list[dict], cur_rows: list[dict], weights: dict) -> dict:
    """ticker -> explanation, for every stock present in both snapshots.
    Rows are dashboard rows with 'z', 'raw', 'rank' / 'would_rank'."""
    prev = {r["ticker"]: r for r in prev_rows}
    out = {}
    for r in cur_rows:
        p = prev.get(r["ticker"])
        if not p:
            continue
        e = explain_change(p.get("z") or {}, r.get("z") or {}, weights, p.get("raw"), r.get("raw"))
        if e["delta"] is None:
            continue
        e["rank_prev"] = p.get("rank") or p.get("would_rank")
        e["rank_now"] = r.get("rank") or r.get("would_rank")
        out[r["ticker"]] = e
    return out


def compare(rec_a: dict, rec_b: dict, factors: dict, n: int = 3) -> dict:
    """Why does A score above (or below) B? Same math as explain_change, with B as
    'before' and A as 'now', so the gaps add up EXACTLY to score_A − score_B.
    rec_*: rows from data.json (need 'ticker' and 'z'). factors: config FACTORS."""
    weights = {f: c["weight"] for f, c in factors.items()}
    e = explain_change(rec_b.get("z") or {}, rec_a.get("z") or {}, weights)
    gaps = [{"factor": d["factor"], "gap": d["contrib"], "z_a": d["z_now"], "z_b": d["z_prev"]}
            for d in e["drivers"]]
    return {"a": rec_a["ticker"], "b": rec_b["ticker"], "diff": e["delta"], "gaps": gaps,
            "top": gaps[:n], "sentence": compare_sentence(rec_a["ticker"], rec_b["ticker"], e["delta"], gaps[:n],
                                                           {f: c["label"] for f, c in factors.items()})}


def compare_sentence(a: str, b: str, diff: float | None, top: list[dict], labels: dict) -> str:
    """'AAPL scores 0.42 above MU, mostly from Price momentum (+0.21) and Volatility (+0.10).'"""
    if diff is None:
        return f"Can't compare {a} and {b}: one of them has no score."
    if abs(diff) < 0.005:
        return f"{a} and {b} score about the same."
    hi, lo = (a, b) if diff > 0 else (b, a)
    sign = 1 if diff > 0 else -1
    helps = [g for g in top if g["gap"] * sign > 0]
    hurts = [g for g in top if g["gap"] * sign < 0]
    lab = lambda g: f"{labels.get(g['factor'], g['factor']).split(' (')[0]} ({abs(g['gap']):.2f})"
    s = f"{hi} scores {abs(diff):.2f} above {lo}"
    if helps:
        s += ", mostly from " + " and ".join(lab(g) for g in helps)
    if hurts:
        s += f"; {lo} is better on " + " and ".join(lab(g) for g in hurts)
    return s + "."
