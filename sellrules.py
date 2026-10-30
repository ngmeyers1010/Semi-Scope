"""
"When should I sell?" without guessing: only rules that WORKED on the universe's own history may alert.

THE IDEA
    Anyone can invent a sell rule ("sell if it drops 20%"). Most feel sensible and do nothing.
    So every rule here is tested first. The test, for each rule:

      * look at every stock in the universe on dates about a month apart (so windows don't overlap)
      * split the stocks into those where the rule WAS firing that day and those where it was not
      * measure what each group did over the NEXT 21 trading days, relative to the average stock
      * per date: (fired group's average) - (not-fired group's average). A negative gap means the
        stocks the rule flagged did WORSE afterwards, i.e. selling them would have helped.
      * t-test those per-date gaps (confidence.t_test): stocks in the same month rise and fall
        together, so each month counts once, not each stock

    Verdict: "worked" (gap < 0 and t <= -2.5), "hurt" (selling early gave up gains: gap > 0 and
    t >= 2.5), otherwise "no clear edge". The bar is 2.5, not 2, because six rules are tested
    and some would pass by luck at 2.

    Only rules with the verdict "worked" raise alerts. The others still show on the page as
    plain facts about a holding, clearly labelled as not validated.

POINT IN TIME
    Every rule looks only backwards from its date; the outcome is measured only afterwards.

Informational only. A flag means "a rule that has worked before fired", not "sell now".
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import bands
import confidence

HORIZON = 21           # trading days of "what happened next"
WARMUP = 260           # history needed before the first test date (the slowest rule needs ~257 days)
MIN_FIRED = 3          # stocks in each group on a date, or that date is skipped
MIN_DATES = 12         # test dates needed for a verdict (price rules)
MIN_QUARTERS = 8       # rebalances needed for a verdict (rank rules)
T_BAR = 2.5

STOP_DROP, STOP_WINDOW = 0.20, 126
TREND_WINDOW = 200
BREAK_DAYS, BREAK_LEVEL, SIGMA_WINDOW = 5, 0.9, 252
RUN_GAIN, RUN_WINDOW = 0.50, 126

RULES = {
    "stop":      {"label": "20% off its high",
                  "plain": "Closed at least 20% below its highest close of the last 6 months (a trailing stop)."},
    "trend":     {"label": "Below 200-day average",
                  "plain": "Closed below its average price of the last 200 trading days (a downtrend)."},
    "breakdown": {"label": "Unusual 5-day drop",
                  "plain": "Fell over 5 days by more than its 'almost always' 5-day swing (the 90% price net)."},
    "runup":     {"label": "Up 50% in 6 months",
                  "plain": "Gained 50% or more in 6 months (a profit target)."},
    "rank_drop": {"label": "Fell out of the top picks",
                  "plain": "Was a top pick at the last rebalance, and is not any more."},
    "bottom_half": {"label": "Ranked in the bottom half",
                    "plain": "Was a top pick at the last rebalance, and now ranks in the bottom half of the universe."},
}
PRICE_RULES = ("stop", "trend", "breakdown", "runup")
RANK_RULES = ("rank_drop", "bottom_half")


# ----------------------------------------------------------------------------- the rules, on prices
def _clean(px: pd.DataFrame) -> pd.DataFrame:
    return px.where(px > 0)


def price_flags(px: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """{rule: frame of 1.0 (firing) / 0.0 / NaN (not enough history)}. Backward-looking only."""
    px = _clean(px)
    hi = px.rolling(STOP_WINDOW, min_periods=STOP_WINDOW).max()
    ma = px.rolling(TREND_WINDOW, min_periods=TREND_WINDOW).mean()
    r1 = np.log(px).diff()
    sigma = r1.rolling(SIGMA_WINDOW, min_periods=SIGMA_WINDOW).std().shift(BREAK_DAYS)   # known before the window
    c = sigma * bands.kappa(BREAK_DAYS, BREAK_LEVEL)
    r5 = np.log(px / px.shift(BREAK_DAYS))
    run = px / px.shift(RUN_WINDOW) - 1
    return {
        "stop": (px <= (1 - STOP_DROP) * hi).astype(float).where(hi.notna() & px.notna()),
        "trend": (px < ma).astype(float).where(ma.notna() & px.notna()),
        "breakdown": (r5 < -c).astype(float).where(c.notna() & r5.notna()),
        "runup": (run >= RUN_GAIN).astype(float).where(run.notna()),
    }


def verdict(diffs: list[float], min_n: int = MIN_DATES) -> dict:
    tt = confidence.t_test(diffs)
    n, mean, t = tt["n"], tt["mean"], tt["t"]
    if n < max(2, min_n):
        v = "too few to tell"
    elif t is None:
        v = "no clear edge"
    elif mean < 0 and t <= -T_BAR:
        v = "worked"
    elif mean > 0 and t >= T_BAR:
        v = "hurt"
    else:
        v = "no clear edge"
    return {"n_dates": n, "diff": None if mean is None else round(mean, 5),
            "t": None if t is None else round(t, 2), "verdict": v}


def study_price(px: pd.DataFrame, horizon: int = HORIZON) -> dict[str, dict]:
    """For each price rule: what did flagged stocks do over the next `horizon` days vs the rest?"""
    px = _clean(px)
    fl = price_flags(px)
    fwd = px.shift(-horizon) / px - 1
    out = {}
    for rule, f in fl.items():
        diffs, fired_all, rest_all = [], [], []
        for i in range(WARMUP, len(px) - horizon, horizon):
            ex = fwd.iloc[i] - fwd.iloc[i].mean()                    # relative to the average stock that day
            ok = f.iloc[i].notna() & ex.notna()
            a, b = ex[ok & (f.iloc[i] == 1)], ex[ok & (f.iloc[i] == 0)]
            if len(a) >= MIN_FIRED and len(b) >= MIN_FIRED:
                diffs.append(float(a.mean() - b.mean()))
                fired_all += a.tolist()
                rest_all += b.tolist()
        out[rule] = {**verdict(diffs, MIN_DATES), "n_events": len(fired_all),
                     "fired": round(float(np.mean(fired_all)), 5) if fired_all else None,
                     "not_fired": round(float(np.mean(rest_all)), 5) if rest_all else None}
    return out


def study_rank(panel: list[dict], top_n: int) -> dict[str, dict]:
    """The same test for the score-based rules, one observation per quarterly rebalance. The group is
    last rebalance's top picks (what you would be holding); 'fired' = no longer a top pick / bottom half."""
    diffs = {k: [] for k in RANK_RULES}
    fired = {k: [] for k in RANK_RULES}
    rest = {k: [] for k in RANK_RULES}
    for prev, cur in zip(panel, panel[1:]):
        held = prev["score"].dropna().nlargest(top_n).index
        sc = cur["score"].dropna()
        fwd = cur["fwd"]
        if len(sc) < 2 * top_n or fwd.dropna().empty:
            continue
        ex = fwd - fwd.mean()
        rank = sc.rank(ascending=False, method="first")
        held = [t for t in held if t in sc.index and t in ex.index and pd.notna(ex[t])]
        flags = {"rank_drop": {t: rank[t] > top_n for t in held},
                 "bottom_half": {t: rank[t] > len(sc) / 2 for t in held}}
        for rule, fl in flags.items():
            a = [ex[t] for t in held if fl[t]]
            b = [ex[t] for t in held if not fl[t]]
            if a and b:
                diffs[rule].append(float(np.mean(a) - np.mean(b)))
            fired[rule] += a
            rest[rule] += b
    return {r: {**verdict(diffs[r], MIN_QUARTERS), "n_events": len(fired[r]),
                "fired": round(float(np.mean(fired[r])), 5) if fired[r] else None,
                "not_fired": round(float(np.mean(rest[r])), 5) if rest[r] else None} for r in RANK_RULES}


# ----------------------------------------------------------------------------- today, for your holdings
def _detail(rule: str, t: str, px: pd.DataFrame, rank: int | None, n: int | None, top_n: int) -> str:
    s = px[t].dropna()
    if rule == "stop":
        return f"{(s.iloc[-1] / s.iloc[-STOP_WINDOW:].max() - 1) * 100:.0f}% from its 6-month high"
    if rule == "trend":
        return f"{(s.iloc[-1] / s.iloc[-TREND_WINDOW:].mean() - 1) * 100:.1f}% under its 200-day average"
    if rule == "breakdown":
        return f"{(s.iloc[-1] / s.iloc[-1 - BREAK_DAYS] - 1) * 100:.1f}% in {BREAK_DAYS} days"
    if rule == "runup":
        return f"up {(s.iloc[-1] / s.iloc[-1 - RUN_WINDOW] - 1) * 100:.0f}% in 6 months"
    if rule == "rank_drop":
        return f"now ranked {rank}"
    return f"now ranked {rank} of {n}"


def now_flags(px: pd.DataFrame, holdings: list[str], ranks: dict, last_picks: list[str] | None,
              top_n: int, n_ranked: int | None, study: dict) -> dict[str, list[dict]]:
    """{ticker: [{rule, label, detail, validated}]} for the rules firing today."""
    fl = price_flags(px)
    out = {}
    for t in holdings:
        if t not in px.columns or px[t].dropna().empty:
            continue
        hits = []
        for rule in PRICE_RULES:
            v = fl[rule][t].iloc[-1] if t in fl[rule].columns else np.nan
            if v == 1.0:
                hits.append(rule)
        r = ranks.get(t)
        if r is not None and last_picks and t in last_picks and n_ranked:
            if r > top_n:
                hits.append("rank_drop")
            if r > n_ranked / 2:
                hits.append("bottom_half")
        if hits:
            out[t] = [{"rule": h, "label": RULES[h]["label"], "detail": _detail(h, t, px, r, n_ranked, top_n),
                       "validated": study.get(h, {}).get("verdict") == "worked"} for h in hits]
    return out


def _read(rules: list[dict]) -> str:
    worked = [r for r in rules if r["verdict"] == "worked"]
    if worked:
        names = ", ".join(f"\"{r['label']}\"" for r in worked)
        return (f"{len(worked)} of {len(rules)} rules passed the test: {names}. Stocks they flagged did worse "
                f"than the rest over the next {HORIZON} trading days. Only these can raise an alert.")
    return (f"None of the {len(rules)} rules passed the test (flagged stocks did not do reliably worse afterwards), "
            "so no alerts are raised. Flags below are shown for information only.")


def build(px: pd.DataFrame, panel: list[dict], holdings: list[str], ranks: dict, last_picks: list[str] | None,
          top_n: int, n_ranked: int | None, tickers: list[str] | None = None) -> dict:
    """The 'sell_rules' block for data['research']. `tickers` limits the price study to the universe."""
    if px is None or px.empty or len(px) < WARMUP + HORIZON + 40:
        return {"available": False, "reason": f"needs about {WARMUP + HORIZON + 40} days of prices"}
    upx = px[[t for t in tickers if t in px.columns]] if tickers else px
    study = {**study_price(upx), **study_rank(panel or [], top_n)}
    rules = [{"key": k, "label": RULES[k]["label"], "plain": RULES[k]["plain"], **study[k]}
             for k in (*PRICE_RULES, *RANK_RULES)]
    return {"available": True, "asof": px.index[-1].strftime("%Y-%m-%d"), "horizon": HORIZON, "t_bar": T_BAR,
            "rules": rules, "validated": [r["key"] for r in rules if r["verdict"] == "worked"],
            "now": now_flags(px, holdings, ranks, last_picks, top_n, n_ranked, study), "read": _read(rules)}


# ----------------------------------------------------------------------------- alerts
def alerts_for(cur: dict | None, prev: dict | None) -> list[dict]:
    """Alerts for validated rules that are firing now and weren't last run (change-only, like the rest)."""
    c = ((cur or {}).get("research") or {}).get("sell_rules") or {}
    p = ((prev or {}).get("research") or {}).get("sell_rules") or {}
    before = {(t, h["rule"]) for t, hits in (p.get("now") or {}).items() for h in hits}
    out = []
    for t, hits in (c.get("now") or {}).items():
        for h in hits:
            if h.get("validated") and (t, h["rule"]) not in before:
                out.append({"level": "warning", "kind": "sell",
                            "text": f"{t}: sell rule \"{h['label']}\" fired ({h['detail']}). "
                                    f"In past tests, stocks flagged by this rule did worse than the rest over the next month."})
    return out
