"""
Factor report card: does each stat actually predict next-quarter returns?

For every completed backtest quarter we compare each factor's ranking of the
universe with the stocks' actual next-quarter returns.

- IC (information coefficient): rank correlation between factor and forward
  return. Above ~0.05 on average is useful in practice; 0 = noise.
- IC t-stat: mean IC / its standard error. |t| > 2 suggests it's not luck.
- Hit rate: % of quarters with a positive IC.
- Top-minus-bottom: avg return of the best third minus the worst third.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ic(x: pd.Series, y: pd.Series) -> float:
    """Spearman rank correlation of x and y (NaN if fewer than 8 pairs)."""
    m = x.notna() & y.notna()
    if m.sum() < 8:
        return np.nan
    return x[m].rank().corr(y[m].rank())


def _spread(x: pd.Series, y: pd.Series) -> float:
    """Average y of the top third by x minus average y of the bottom third."""
    m = x.notna() & y.notna()
    if m.sum() < 9:
        return np.nan
    x, y = x[m], y[m]
    q = x.rank(pct=True)
    return y[q > 2 / 3].mean() - y[q <= 1 / 3].mean()


def report_card(panel: list[dict], factor_names: list[str]) -> tuple[dict, dict]:
    """Per-factor IC stats and the per-quarter IC series."""
    rows, ic_series = {}, {}
    cols = list(factor_names) + ["score"]
    for f in cols:
        ics, spreads, dates = [], [], []
        for p in panel:
            x = p["score"] if f == "score" else (p["z"][f] if f in p["z"] else None)
            if x is None:
                continue
            x = x.reindex(p["fwd"].index)
            ics.append(_ic(x, p["fwd"]))
            spreads.append(_spread(x, p["fwd"]))
            dates.append(p["date"].strftime("%Y-%m-%d"))
        ic = pd.Series(ics, index=dates, dtype=float)
        sp = pd.Series(spreads, index=dates, dtype=float)
        n = ic.notna().sum()
        mean = ic.mean()
        t = mean / (ic.std() / np.sqrt(n)) if n > 2 and ic.std() > 0 else np.nan
        rows[f] = {"mean_ic": mean, "ic_t": t, "hit_rate": (ic > 0).sum() / n if n else np.nan,
                   "spread": sp.mean(), "quarters": int(n),
                   "ic_recent": ic.tail(8).mean(),
                   "verdict": verdict(mean, t)}
        ic_series[f] = [[d, None if pd.isna(v) else round(float(v), 4)] for d, v in ic.items()]
    return rows, ic_series


def verdict(mean: float, t: float) -> str:
    """Plain-English grade for a factor from its mean IC and t-stat."""
    if pd.isna(t):
        return "not enough data"
    if mean > 0 and t > 2:
        return "works"
    if mean > 0 and t > 1:
        return "promising"
    if mean < 0 and t < -2:
        return "backwards"
    return "noise"


# ---------------------------------------------------------------------------
# Out-of-sample check
#
# The factor weights were chosen by looking at the whole history, so the full
# backtest is partly "graded on the homework it studied." Splitting at a fixed
# date shows whether each stat kept working on years it wasn't tuned on.
# ---------------------------------------------------------------------------
def split_quarters(dates: list[str], split: str) -> tuple[list[str], list[str]]:
    """In-sample = quarters whose whole holding period ends on/before `split`.
    Out-of-sample = quarters starting on/after `split`. A quarter that straddles
    the split is dropped, so no day's return counts in both periods."""
    s = pd.Timestamp(split)
    ins, oos = [], []
    for i, d in enumerate(dates):
        nxt = pd.Timestamp(dates[i + 1]) if i + 1 < len(dates) else None
        if pd.Timestamp(d) >= s:
            oos.append(d)
        elif nxt is not None and nxt <= s:
            ins.append(d)
    return ins, oos


def _ic_stats(v: pd.Series) -> tuple[float, float, int]:
    v = v.dropna()
    n = len(v)
    t = v.mean() / (v.std() / np.sqrt(n)) if n > 2 and v.std() > 0 else np.nan
    return (v.mean() if n else np.nan), t, n


def oos_verdict(ins: float, oos: float) -> str:
    """Did the factor's in-sample IC survive out of sample?
    ICs are already sign-adjusted (positive = the stat points the right way)."""
    if pd.isna(ins) or pd.isna(oos):
        return "not enough data"
    if abs(ins) < 0.01:
        return "no in-sample edge"
    if ins < 0:   # pointed the WRONG way before the split
        return "backwards in both" if oos <= -0.01 else "turned positive" if oos >= 0.01 else "faded to zero"
    if oos <= -0.01:
        return "flipped"
    return "held up" if oos >= 0.5 * ins else "weakened"


def _period_stats(curve: pd.Series, spy: pd.Series | None, lo, hi) -> dict:
    from backtest import stats
    c = curve.loc[lo:hi].dropna()
    if len(c) < 20:
        return {}
    s = stats(c / c.iloc[0])
    if spy is not None:
        sp = spy.loc[c.index[0]:c.index[-1]].dropna()
        if len(sp) > 20:
            s["spy_cagr"] = stats(sp / sp.iloc[0]).get("cagr")
            s["excess"] = s["cagr"] - s["spy_cagr"]
    s["start"], s["end"] = c.index[0].strftime("%Y-%m-%d"), c.index[-1].strftime("%Y-%m-%d")
    return s


def oos_check(ic_series: dict, curves: dict, split: str, weights: dict, labels: dict | None = None) -> dict:
    """Per-factor IC before/after `split`, plus the strategy's results in each period."""
    any_f = next(iter(ic_series.values()))
    dates = [d for d, _ in any_f]
    ins_d, oos_d = split_quarters(dates, split)
    rows = []
    for f, pts in ic_series.items():
        ic = pd.Series({d: (np.nan if v is None else v) for d, v in pts}, dtype=float)
        mi, ti, ni = _ic_stats(ic.reindex(ins_d))
        mo, to, no = _ic_stats(ic.reindex(oos_d))
        rows.append({"factor": f, "scored": f == "score" or weights.get(f, 0) > 0,
                     "ic_in": mi, "t_in": ti, "n_in": ni, "ic_out": mo, "t_out": to, "n_out": no,
                     "verdict": oos_verdict(mi, mo)})
    strat, spy = curves.get("strategy"), curves.get("SPY")
    s = pd.Timestamp(split)
    periods = {"in_sample": _period_stats(strat, spy, None, s - pd.Timedelta(days=1)),
               "out_of_sample": _period_stats(strat, spy, s, None)}
    scored = [r for r in rows if r["scored"] and r["factor"] != "score"]
    held = sum(r["verdict"] == "held up" for r in scored)
    flipped = [r["factor"] for r in scored if r["verdict"] == "flipped"]
    backwards = [r["factor"] for r in scored if r["verdict"] == "backwards in both"]
    comp = next((r for r in rows if r["factor"] == "score"), {})
    o = periods["out_of_sample"]
    parts = [f"{held} of {len(scored)} scored stats held up after {split[:4]}."]
    if flipped:
        parts.append(f"Flipped: {', '.join((labels or {}).get(f, f) for f in flipped)}.")
    if backwards:
        parts.append(f"Pointing the wrong way in both periods (consider weight 0): "
                     f"{', '.join((labels or {}).get(f, f) for f in backwards)}.")
    if comp.get("verdict"):
        parts.append(f"Combined score: {comp['verdict']}.")
    if o.get("excess") is not None:
        parts.append(f"Strategy {'beat' if o['excess'] > 0 else 'trailed'} SPY by "
                     f"{abs(o['excess']):.1%}/yr out of sample.")
    return {"split": split, "n_in": len(ins_d), "n_out": len(oos_d), "factors": rows,
            "periods": periods, "summary": " ".join(parts)}
