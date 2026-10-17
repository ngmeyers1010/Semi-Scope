"""Mistake-spotting for check.py: the usual wrong answers (as code) and the hint for each."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from _cases import _same  # noqa: F401

HERE = Path(__file__).parent


def _ex28_variants():
    """Wrong luminance() versions people write, with the hint for each."""
    def ch(h, scale=255):
        h = str(h).strip().lstrip("#")
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        return [int(h[i:i + 2], 16) / scale for i in (0, 2, 4)]
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    mix = lambda r, g, b: 0.2126 * r + 0.7152 * g + 0.0722 * b
    return [(lambda h: mix(*(lin(c) for c in ch(h, 1))), "divide each channel by 255 first: int('ff', 16) is 255, but the formula wants 0..1."),
            (lambda h: mix(*ch(h, 1)), "divide each channel by 255 first: int('ff', 16) is 255, but the formula wants 0..1."),
            (lambda h: mix(*ch(h)), "linearize each channel (c / 12.92 or ((c + 0.055) / 1.055) ** 2.4) before mixing."),
            (lambda h: sum(lin(c) for c in ch(h)) / 3, "weight the channels 0.2126 R + 0.7152 G + 0.0722 B: green looks much brighter than blue."),
            (lambda h: sum(ch(h)) / 3, "a plain average of R, G, B isn't luminance: linearize, then weight 0.2126 / 0.7152 / 0.0722.")]


def _hint28(got, colour):
    try:
        g = float(got)
    except (TypeError, ValueError):
        return ""
    for wrong, msg in _ex28_variants():
        try:
            if abs(wrong(colour) - g) < 1e-9:
                return f"\n    Hint: {msg}"
        except (TypeError, ValueError):
            pass
    return ""


def _ex29_variant(prev, cur, top_n, n=3, mode=""):
    """Wrong versions people write."""
    if not prev or not cur:
        if mode != "none":
            return None
        prev, cur = prev or {}, cur or {}
    big = 10 ** 9
    inn = (lambda r: r is not None and r < top_n) if mode == "lt" else (lambda r: r is not None and r <= top_n)
    entered = sorted((t for t in cur if inn(cur[t]) and not inn(prev.get(t))), key=lambda t: cur[t])
    left = sorted((t for t in prev if inn(prev[t]) and not inn(cur.get(t))), key=lambda t: prev[t])
    p = (lambda t: prev.get(t, big)) if mode == "newup" else (lambda t: prev[t])
    both = [t for t in cur if (mode == "newup" or t in prev) and p(t) != cur[t]]
    key = (lambda m: (lambda t: (-m(t),))) if mode == "tie" else (lambda m: (lambda t: (-m(t), cur[t], t)))
    up = sorted((t for t in both if cur[t] < p(t)), key=key(lambda t: p(t) - cur[t]))
    down = sorted((t for t in both if cur[t] > p(t)), key=key(lambda t: cur[t] - p(t)))
    if mode == "swap":
        up, down = down, up
    k = None if mode == "all" else n
    item = lambda t: {"ticker": t, "from": prev.get(t), "to": cur.get(t)}
    return {"entered": [item(t) for t in entered], "left": [item(t) for t in left],
            "up": [item(t) for t in up[:k]], "down": [item(t) for t in down[:k]],
            "new": sorted(t for t in cur if t not in prev)}


EX29_HINTS = [("none", "if prev or cur is empty (or None) there's nothing to compare: return None."),
              ("all", "show at most n movers each way: up[:n] and down[:n]."),
              ("swap", "a SMALLER rank number is better, so #9 -> #4 is a climb (cur < prev means up)."),
              ("newup", "a ticker that's not in prev is new, not a climber: only compare tickers in BOTH dicts."),
              ("lt", "'in the top 5' means rank <= top_n (rank 5 counts), not < top_n."),
              ("tie", "on a tie, sort by the new rank, then ticker: key=lambda t: (-move, cur[t], t).")]


def _hint29(got, prev, cur, top_n, n=3):
    for mode, msg in EX29_HINTS:
        try:
            if got == _ex29_variant(prev, cur, top_n, n, mode):
                return f"\n    Hint: {msg}"
        except Exception:  # noqa: BLE001
            pass
    return ""


def _ex30_classify_variant(quarters, mode):
    out = []
    pairs = list(zip([None] + quarters[:-1], quarters)) if mode == "first" else list(zip(quarters, quarters[1:]))
    for prev, q in pairs:
        if not q.get("picks") or q.get("universe") is None:
            continue
        ok = prev is not None and (mode == "nocont" or prev.get("end") == q.get("date"))
        before = set(prev.get("picks") or []) if ok else set()
        uni = 0.0 if mode == "nouni" else q["universe"]
        row = {"date": q["date"], "stay": [], "new": []}
        for t in q["picks"]:
            r = (q.get("pick_returns") or {}).get(t)
            if r is not None:
                row["stay" if t in before else "new"].append(r - uni)
        out.append(row)
    return out


def _ex30_gap_variant(rows, mode):
    import math
    if mode == "pool":
        s = [x for r in rows for x in r["stay"]]
        n = [x for r in rows for x in r["new"]]
        if len(s) < 2 or len(n) < 2:
            return None
        ms, mn = sum(s) / len(s), sum(n) / len(n)
        vs = sum((x - ms) ** 2 for x in s) / (len(s) - 1)
        vn = sum((x - mn) ** 2 for x in n) / (len(n) - 1)
        return (ms - mn) / math.sqrt(vs / len(s) + vn / len(n)) if vs + vn else None
    gaps = [sum(r["stay"]) / len(r["stay"]) - sum(r["new"]) / len(r["new"]) for r in rows if r["stay"] and r["new"]]
    k = len(gaps)
    if k < 2:
        return None
    m = sum(gaps) / k
    sd = math.sqrt(sum((g - m) ** 2 for g in gaps) / k)          # ddof=0
    return m / (sd / math.sqrt(k)) if sd > 1e-12 else None


def _rows_close(a, b) -> bool:
    if not isinstance(a, list) or len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if not isinstance(x, dict) or x.get("date") != y["date"]:
            return False
        for k in ("stay", "new"):
            g = x.get(k)
            if not isinstance(g, list) or len(g) != len(y[k]) or any(abs(float(p) - q) > 1e-9 for p, q in zip(g, y[k])):
                return False
    return True


EX30_CLASSIFY_HINTS = [
    ("first", "skip the first quarter: with nothing before it, you can't tell a stayer from a new pick."),
    ("nocont", "a stayer needs prev['end'] == q['date'] too: after a gap in the calendar, everyone is new."),
    ("nouni", "excess = the pick's return MINUS q['universe'] (the average stock that quarter)."),
]


def _ex27_variant(values, mode):
    import statistics
    v, d = list(values), []
    ok = lambda x: x is not None and not (isinstance(x, float) and np.isnan(x))
    for i, x in enumerate(v):
        if not ok(x) or x <= 0:
            continue
        if mode == "prev":
            js = [i - 1] if i >= 1 else []
        elif mode == "look":
            js = list(range(max(0, i - 4), i)) + list(range(i + 1, min(len(v), i + 5)))
        else:
            js = list(range(max(0, i - 4), i))
        b = [v[j] for j in js if (mode == "noskip" or j not in d) and ok(v[j]) and v[j] > 0]
        if len(b) < (1 if mode == "prev" else 2):
            continue
        m = (sum(b) / len(b)) if mode == "mean" else statistics.median(b)
        r = x / m
        if (r > 8 or r < 1 / 8) if mode == "gt" else (r >= 8 or r <= 1 / 8):
            d.append(i)
    return d


def _hint27(got, values):
    if not isinstance(got, list):
        return ""
    for mode, msg in (("look", "only look at quarters BEFORE this one (range(i - lookback, i)); later ones didn't exist yet."),
                      ("mean", "use the MEDIAN of the earlier quarters: one odd quarter drags a mean around."),
                      ("noskip", "leave out quarters you already dropped, or one bad number makes the next bad one look normal."),
                      ("gt", "exactly 8x counts as a jump: use >= jump (and <= 1 / jump)."),
                      ("prev", "compare with the median of up to 4 earlier quarters (need at least 2), not just the previous one.")):
        try:
            if [int(x) for x in got] == _ex27_variant(values, mode):
                return f"\n    Hint: {msg}"
        except (TypeError, ValueError):
            return ""
    return ""


def _buggy_drawdowns():
    return [lambda p: float(p.min() / p.iloc[0] - 1),            # measures from the FIRST price
            lambda p: float(-(p / p.cummax() - 1).min())]          # forgets the minus sign


def _hint17(got, history, today):
    h = history.dropna()
    try:
        g = float(got)
    except (TypeError, ValueError):
        return ""
    if len(h) and abs(g - 100 * (h <= today).sum() / len(h)) < 1e-6:
        return "\n    Hint: looks like weeks EQUAL to today counted fully. They should count half."
    if abs(g - 100 * ((h < today).sum() + 0.5 * (h == today).sum()) / len(history)) < 1e-6:
        return "\n    Hint: looks like NaN weeks were counted. Drop them first with .dropna()."
    return ""


def _hint18(got, ticker, download):
    if isinstance(got, float) and np.isnan(got):
        return "\n    Hint: you returned NaN. Drop missing days with .dropna() and return None if nothing is left."
    return ""


def _hint19(got, strat, spy):
    if not isinstance(got, pd.Series):
        return ""
    summed = (strat.pct_change().rolling(252).sum() - spy.pct_change().rolling(252).sum()).dropna()
    if len(got) == len(summed) and np.allclose(got.to_numpy(float), summed.to_numpy(float), equal_nan=True):
        return "\n    Hint: looks like daily returns were ADDED. Returns compound: use p / p.shift(252) - 1."
    off = ((strat / strat.shift(251) - 1) - (spy / spy.shift(251) - 1)).dropna()
    if len(got) == len(off) and np.allclose(got.to_numpy(float), off.to_numpy(float), equal_nan=True):
        return "\n    Hint: off by one day. A year is 252 trading days back: .shift(252), not 251."
    return ""


def _hint20(got, old, new, date):
    if not isinstance(got, list) or not got:
        return ""
    dates = [a.get("date") for a in got]
    if dates == sorted(dates) and dates != sorted(dates, reverse=True):
        return "\n    Hint: the newest entries should come FIRST."
    todays = [a.get("text") for a in got if a.get("date") == date]
    if len(set(todays)) > len({a["text"] for a in new}):
        return "\n    Hint: the old entries for that day are still there. A re-run REPLACES the day."
    pairs = [(a.get("date"), a.get("text")) for a in got]
    if len(pairs) != len(set(pairs)):
        return "\n    Hint: there are duplicate (date, text) pairs. Keep a set of the ones you've seen."
    return ""


def _hint21(got, data, ticker):
    try:
        g = float(got)
    except (TypeError, ValueError):
        return ""
    rec = next(r for r in data["rankings"] if r["ticker"] == ticker)

    def variant(clip=True, flip=True, all_weights=False):
        num = den = 0.0
        for f, c in data["factors"].items():
            x, s = (rec.get("raw") or {}).get(f), data["z_stats"].get(f)
            if c["weight"] <= 0:
                continue
            if x is None or not s:
                den += c["weight"] if all_weights else 0
                continue
            v = min(max(x, s["lo"]), s["hi"]) if clip else x
            num += c["weight"] * (v - s["mean"]) / s["sd"] * (c["sign"] if flip else 1)
            den += c["weight"]
        return num / den
    for kw, msg in (({"clip": False}, "clip each raw value into [lo, hi] before the z-score"),
                    ({"flip": False}, "multiply z by the factor's sign (-1 = lower is better)"),
                    ({"all_weights": True}, "only add the weights of the stats the stock HAS")):
        if abs(g - variant(**kw)) < 1e-6:
            return f"\n    Hint: {msg}."
    return ""


def _hint22(got, px, date, picks, universe, months):
    start = pd.Timestamp(date)
    i = px.index.searchsorted(start + pd.DateOffset(months=months))
    if i >= len(px.index):
        return "\n    Hint: the data doesn't reach date + months yet: return None."
    try:
        g = float(got)
    except (TypeError, ValueError):
        return ""
    end = px.index[i]
    r = lambda names, e=end: (px.loc[e, names] / px.loc[start, names] - 1)
    prev = px.index[px.index.searchsorted(start + pd.DateOffset(months=months), side="right") - 1]
    if abs(g - float(r(picks, prev).mean() - r(universe, prev).dropna().mean())) < 1e-9:
        return "\n    Hint: use the first trading day ON OR AFTER the target (searchsorted), not the one before."
    if abs(g - float(r(picks).mean() - r(universe).dropna().sum())) < 1e-9:
        return "\n    Hint: the universe return is the AVERAGE (.mean()), not the sum."
    if abs(g - float(r(picks).mean() - r(universe).fillna(0).mean())) < 1e-9:
        return "\n    Hint: skip stocks with a missing price (.dropna()) instead of counting them as 0%."
    return ""


def _hint23(got, z_prev, z_now, weights):
    if not isinstance(got, dict):
        return ""
    w = {f: x for f, x in weights.items() if x > 0}
    keys = [f for f in w if z_prev.get(f) is not None or z_now.get(f) is not None]
    if any(f not in w for f in got):
        return "\n    Hint: skip factors whose weight is 0."
    W_all = sum(w.values())
    Wp = sum(w[f] for f in w if z_prev.get(f) is not None)
    Wn = sum(w[f] for f in w if z_now.get(f) is not None)
    z = lambda d, f: d.get(f) if d.get(f) is not None else 0.0
    def same(alt):
        return set(got) == set(alt) and all(abs(got[k] - alt[k]) < 1e-9 for k in alt)
    if same({f: w[f] * (z(z_now, f) - z(z_prev, f)) / W_all for f in keys}):
        return "\n    Hint: divide by the weights of the factors the stock HAS (W_prev, W_now), not all of them."
    if same({f: w[f] * (z(z_now, f) - z(z_prev, f)) / Wn for f in keys}) or \
            same({f: w[f] * (z(z_now, f) - z(z_prev, f)) / Wp for f in keys}):
        return ("\n    Hint: w * (z_now - z_prev) / W breaks when a factor appears or disappears, because W changes too. "
                "Use w*z_now/W_now - w*z_prev/W_prev.")
    total = sum(got.values())
    sp = sum(w[f] * z(z_prev, f) for f in w) / Wp if Wp else 0
    sn = sum(w[f] * z(z_now, f) for f in w) / Wn if Wn else 0
    if abs(total - (sn - sp)) > 1e-9:
        return f"\n    Hint: your contributions add up to {total:+.4f}, but the score changed by {sn - sp:+.4f}."
    return ""


def _hint24(got, strat, bench):
    try:
        g = tuple(float(x) for x in got)
    except (TypeError, ValueError):
        return ""
    def variant(monthly=True, ge=False, flip=False, per_month=False):
        m = (lambda p: p.resample("ME").last().pct_change().dropna()) if monthly else (lambda p: p.pct_change().dropna())
        both = pd.concat([m(strat).rename("s"), m(bench).rename("b")], axis=1, sort=True).dropna()
        up = both[both["b"] >= 0] if ge else both[both["b"] > 0]
        dn = both[both["b"] < 0]
        if per_month:
            return float((up["s"] / up["b"]).mean()), float((dn["s"] / dn["b"]).mean())
        if flip:
            return float(up["b"].mean() / up["s"].mean()), float(dn["b"].mean() / dn["s"].mean())
        return float(up["s"].mean() / up["b"].mean()), float(dn["s"].mean() / dn["b"].mean())
    close = lambda a, b: all(abs(x - y) < 1e-9 for x, y in zip(a, b))
    for kw, msg in (({"monthly": False}, "use MONTHLY returns: resample('ME').last() before pct_change()."),
                    ({"ge": True}, "flat months (benchmark exactly 0) are neither up nor down: use > 0, not >= 0."),
                    ({"flip": True}, "strategy on top: strategy mean / benchmark mean."),
                    ({"per_month": True}, "average the strategy and the benchmark separately, then divide "
                                          "(a ratio of averages, not an average of monthly ratios).")):
        try:
            if close(g, variant(**kw)):
                return f"\n    Hint: {msg}"
        except ZeroDivisionError:
            continue
    return ""


def _hint26(got, returns, years, n_paths):
    import numpy as _np
    r, q, b = _np.asarray(returns, dtype=float), 4 * years, 4
    nb = -(-q // b)
    def paths(high, single=False, cum="prod", scale=1000.0):
        rng = _np.random.default_rng(42)
        if single:
            idx = rng.integers(0, len(r), size=(n_paths, q))
        else:
            st = rng.integers(0, high, size=(n_paths, nb))
            idx = (st[:, :, None] + _np.arange(b)).reshape(n_paths, -1)[:, :q]
        x = r[idx]
        return scale * (_np.cumprod(1 + x, axis=1) if cum == "prod" else 1 + _np.cumsum(x, axis=1))
    g = _np.asarray(got, dtype=float)
    for kw, msg in (({"high": len(r) - b}, "integers' upper bound is exclusive: use n - block + 1, or the last block is never picked."),
                    ({"high": len(r) - b + 1, "single": True}, "sample BLOCKS of consecutive quarters (start positions), not single quarters."),
                    ({"high": len(r) - b + 1, "cum": "sum"}, "returns compound: np.cumprod(1 + r), not a cumulative sum."),
                    ({"high": len(r) - b + 1, "scale": 1.0}, "multiply by 1000: each path is the value of $1,000.")):
        try:
            alt = paths(**kw)
        except ValueError:
            continue
        if alt.shape == g.shape and _np.allclose(alt, g):
            return f"\n    Hint: {msg}"
    return ""


def _hint25(got, want, curve):
    """got/want already normalized. Compare with the usual wrong versions."""
    if not want:
        return ""
    if len(got) == len(want) - 1 and want[-1]["recovery"] is None and got == want[:-1]:
        return "\n    Hint: the data ends while still underwater. Close that last episode with recovery = None."
    if got == []:
        return "\n    Hint: no episodes at all. The running HIGH is curve.cummax() (cummin is the running low)."
    if len(got) == len(want) and all(g["peak"] != w["peak"] for g, w in zip(got, want)) and \
            [g["recovery"] for g in got] == [w["recovery"] for w in want]:
        return "\n    Hint: the peak is the day BEFORE the curve goes underwater (start = i - 1), not the first day below."
    if len(got) > len(want) and all(w in got for w in want):
        return "\n    Hint: drop small wiggles: keep an episode only if -depth >= min_depth."
    return ""


# The usual wrong answers to exercises 1-16 (not 12, which grades a test), each as code that makes
# the same mistake.
# If your answer matches one exactly, the checker says what that mistake was.
def _ex02_wrong_shift(px):
    return (px / px.shift(-1) - 1).iloc[1:]


SLIPS = {
    1: [(lambda px, t: float(px[t].iloc[0]),
         "that's the FIRST row, and it's empty (the stock wasn't trading yet). Drop missing values with "
         ".dropna(), then take the LAST one with .iloc[-1]."),
        (lambda px, t: float(px[t].dropna().iloc[0]),
         "that's the first price on record. The most recent one is the last row: .iloc[-1]."),
        (lambda px, t: float(px[t].max()), "that's the highest price ever, not the most recent one (.iloc[-1]).")],
    2: [(lambda px: px.pct_change(), "the first row has no day before it, so it's all NaN. Drop it: .iloc[1:]."),
        (lambda px: px.diff().iloc[1:], ".diff() gives the change in DOLLARS. A return is the change in percent: .pct_change()."),
        (_ex02_wrong_shift, "shift(-1) looks at TOMORROW. A daily return compares today with yesterday: .pct_change().")],
    3: [(lambda px, t, a, b: float(px.loc[a:b, t].dropna().iloc[0] / px.loc[a:b, t].dropna().iloc[-1] - 1),
         "upside down: it's END / START - 1 (s.iloc[-1] / s.iloc[0] - 1)."),
        (lambda px, t, a, b: float(px.loc[a:b, t].dropna().iloc[-1] / px.loc[a:b, t].dropna().iloc[0]),
         "that's the growth factor (1.25 = +25%). Subtract 1 to get the return."),
        (lambda px, t, a, b: float(px[t].dropna().iloc[-1] / px[t].dropna().iloc[0] - 1),
         "that's the whole history. Slice the dates first: px.loc[start:end, ticker].")],
    4: [(lambda px, days=252: str((px.iloc[-1] / px.iloc[-days] - 1).dropna().idxmin()),
         ".idxmin() finds the WORST stock. The best is .idxmax()."),
        (lambda px, days=252: str((px.iloc[-1] / px.iloc[days] - 1).dropna().idxmax()),
         "px.iloc[days] counts from the START of the data. 'days ago' counts from the end: px.iloc[-days]."),
        (lambda px, days=252: str(px.iloc[-1].idxmax()),
         "that's the stock with the highest PRICE today. Compare each stock's return over the period instead.")],
    5: [(lambda px, t, days=126: float(px[t].pct_change().dropna().tail(days).std()),
         "that's DAILY volatility. Annualize it: multiply by sqrt(252) (252 trading days a year)."),
        (lambda px, t, days=126: float(px[t].pct_change().dropna().tail(days).std() * 252),
         "multiply by the SQUARE ROOT of 252 (252 ** 0.5), not 252: spread grows with the square root of time."),
        (lambda px, t, days=126: float(px[t].dropna().tail(days).std() * 252 ** 0.5),
         "that's the spread of PRICES. Volatility is the spread of daily RETURNS: .pct_change() first.")],
    6: [(lambda p: float(-(p / p.cummax() - 1).min()),
         "a drawdown is a fall, so it's NEGATIVE (-0.35 = 35% below the peak). Drop the minus sign."),
        (lambda p: float(p.min() / p.iloc[0] - 1),
         "that measures from the FIRST price. A drawdown is measured from the running high: p / p.cummax() - 1."),
        (lambda p: float((p / p.cummax() - 1).max()),
         "the worst point is the .min() of p / p.cummax() - 1 (.max() is always 0, at a new high).")],
    7: [(lambda px, t: px[t].dropna().resample("ME").last().pct_change().dropna(),
         "right numbers, but the labels should be months like 2021-03, not dates: group by s.index.to_period('M')."),
        (lambda px, t: (lambda s: s.groupby(s.index.to_period("M")).first().pct_change().dropna())(px[t].dropna()),
         "use each month's LAST price (.last()), not its first."),
        (lambda px, t: (lambda s: s.groupby(s.index.to_period("M")).last().pct_change())(px[t].dropna()),
         "the first month has nothing before it (NaN). Drop it with .dropna().")],
    8: [(lambda tb: tb.groupby("group")["rev_growth"].mean().sort_values(ascending=False),
         "use the MEDIAN (.median()): one wild company drags a mean around."),
        (lambda tb: tb.groupby("group")["rev_growth"].median(),
         "sort it, biggest first: .sort_values(ascending=False)."),
        (lambda tb: tb.groupby("group")["rev_growth"].median().sort_values(),
         "biggest first: .sort_values(ascending=False).")],
    9: [(lambda r, c: (lambda m: m.assign(gross_margin=m["val_cogs"] / m["val_rev"])[["end", "gross_margin"]]
                       .sort_values("end").reset_index(drop=True))(r.merge(c, on="end", suffixes=("_rev", "_cogs"))),
         "that's cost as a share of sales. Gross margin is what's LEFT: 1 - cogs / revenue."),
        (lambda r, c: (lambda m: m.assign(gross_margin=1 - m["val_rev"] / m["val_cogs"])[["end", "gross_margin"]]
                       .sort_values("end").reset_index(drop=True))(r.merge(c, on="end", suffixes=("_rev", "_cogs"))),
         "flipped: it's 1 - cogs / revenue (divide by revenue)."),
        (lambda r, c: (lambda m: m.assign(gross_margin=m["val_rev"] - m["val_cogs"])[["end", "gross_margin"]]
                       .sort_values("end").reset_index(drop=True))(r.merge(c, on="end", suffixes=("_rev", "_cogs"))),
         "that's gross PROFIT in dollars. Margin is a share of sales: 1 - cogs / revenue.")],
    10: [(lambda px: (lambda m: ((m - m.mean()) / m.std()).sort_values(ascending=False))((px.iloc[-1] / px.iloc[-126] - 1).dropna()),
          "skip the most recent month: end at px.iloc[-21], not px.iloc[-1] (last month's move tends to reverse)."),
         (lambda px: (lambda m: ((m - m.mean()) / m.std(ddof=0)).sort_values(ascending=False))((px.iloc[-21] / px.iloc[-126] - 1).dropna()),
          "use pandas' default .std() (sample, divides by n - 1), not ddof=0."),
         (lambda px: (lambda m: ((m - m.mean()) / m.std()))((px.iloc[-21] / px.iloc[-126] - 1).dropna()),
          "sort it, highest first: .sort_values(ascending=False).")],
}


def _ex11(px, start, end, k=3, upto=None, skip=-21, pick="nlargest", agg="mean"):
    # (skipping vs not skipping the last month picks the same stocks on these cases, so that slip
    # can't be told apart and isn't listed)
    past = px.loc[:upto or start]
    mom = (past.iloc[skip] / past.iloc[-126] - 1).dropna()
    picks = getattr(mom, pick)(k).index
    window = px.loc[start:end, picks]
    r = window.iloc[-1] / window.iloc[0] - 1
    return float(getattr(r, agg)())


def _ex13(prices, n=1, window=slice(-253, -1), scale=True, of="returns"):
    p = prices.dropna()
    r = p.pct_change()
    sigma = (r if of == "returns" else p).iloc[window].std()
    ret = p.iloc[-1] / p.iloc[-1 - n] - 1
    return float(ret / (sigma * (np.sqrt(n) if scale else 1)))


def _ex14(lots, shares, price, sell_date, order=1, boundary="gt", gain="gain"):
    left, short, long_ = shares, 0.0, 0.0
    for buy_date, n, buy_price in lots[::order]:
        if left <= 0:
            break
        take = min(n, left)
        g = take * (price - buy_price) if gain == "gain" else take * price
        days = (pd.Timestamp(sell_date) - pd.Timestamp(buy_date)).days
        if days > 365 if boundary == "gt" else days >= 365:
            long_ += g
        else:
            short += g
        left -= take
    return pd.Series({"short": short, "long": long_})


def _ex15(excess, ddof=1, root=True):
    import math
    x = pd.Series(excess, dtype=float)
    mean, sd, n = x.mean(), x.std(ddof=ddof), len(x)
    t = mean / (sd / math.sqrt(n)) if root else mean / sd
    need = math.ceil((2 * sd / mean) ** 2) if mean > 0 else float("nan")
    return pd.Series({"mean": mean, "sd": sd, "t": t, "quarters_needed": need})


def _ex16(px, tickers, lookback=63, power=1, normalize=True, inverse=True):
    vol = px[tickers].tail(lookback + 1).pct_change().std() * np.sqrt(252)
    w = (1 / vol ** power) if inverse else vol
    return w / w.sum() if normalize else w


SLIPS.update({
    11: [(lambda px, a, b, k=3: _ex11(px, a, b, k, upto=b),
          "LOOK-AHEAD: you ranked the stocks with prices from after the start date. Only use px.loc[:start] to pick."),
         (lambda px, a, b, k=3: _ex11(px, a, b, k, pick="nsmallest"), "those are the WORST k: use .nlargest(k)."),
         (lambda px, a, b, k=3: _ex11(px, a, b, k, agg="sum"),
          "equal weight means the AVERAGE of the picks' returns (.mean()), not the total.")],
    13: [(lambda p, n=1: _ex13(p, n, window=slice(-252, None)),
          "today's move is inside its own volatility window. Measure sigma on the year BEFORE today: r.iloc[-253:-1]."),
         (lambda p, n=1: _ex13(p, n, scale=False),
          "an n-day move is bigger than a 1-day one: compare it with sigma * sqrt(n)."),
         (lambda p, n=1: _ex13(p, n, of="prices"), "use the spread of daily RETURNS (p.pct_change()), not of prices.")],
    14: [(lambda lots, sh, pr, d: _ex14(lots, sh, pr, d, order=-1),
          "that sells the NEWEST shares first (LIFO). FIFO = first in, first out: oldest lot first."),
         (lambda lots, sh, pr, d: _ex14(lots, sh, pr, d, boundary="ge"),
          "long-term means held MORE than 365 days (> 365). Exactly 365 is still short-term."),
         (lambda lots, sh, pr, d: _ex14(lots, sh, pr, d, gain="proceeds"),
          "that's the sale proceeds. The gain is shares * (sell price - buy price).")],
    15: [(lambda x: _ex15(x, ddof=0), "use the SAMPLE sd: pandas' .std() (divides by n - 1), not ddof=0 / numpy's default."),
         (lambda x: _ex15(x, root=False), "t = mean / (sd / sqrt(n)): divide sd by the square root of the sample size first.")],
    16: [(lambda px, t, lb=63: _ex16(px, t, lb, power=2),
          "that's 1 / variance. Inverse-VOLATILITY weights are 1 / vol (vol = std * sqrt(252))."),
         (lambda px, t, lb=63: _ex16(px, t, lb, normalize=False),
          "weights must add up to 1: divide by their sum (inv / inv.sum())."),
         (lambda px, t, lb=63: _ex16(px, t, lb, inverse=False),
          "that gives MORE weight to the jumpiest stock. Use 1 / vol, so calmer stocks get more.")],
})


def _beta_positional(s, m):
    a, b = s.dropna().to_numpy(), m.dropna().to_numpy()
    k = min(len(a), len(b))
    a, b = a[-k:], b[-k:]
    return float(np.cov(a, b)[0, 1] / np.var(b, ddof=1))


SLIPS[31] = [
    (lambda s, m: float(pd.concat([s, m], axis=1, sort=True).dropna().corr().iloc[0, 1]),
     "that's the CORRELATION (how closely they move, -1..1). Beta also scales by size: cov(stock, market) / var(market)."),
    (lambda s, m: (lambda j: float(j.iloc[:, 0].cov(j.iloc[:, 1]) / j.iloc[:, 0].var()))(pd.concat([s, m], axis=1, sort=True).dropna()),
     "divide by the MARKET's variance, not the stock's: beta = cov(stock, market) / var(market)."),
    (lambda s, m: (lambda j: float(j.iloc[:, 0].cov(j.iloc[:, 1]) / j.iloc[:, 1].var(ddof=0)))(pd.concat([s, m], axis=1, sort=True).dropna()),
     "cov and var must use the same n: pandas' .cov() divides by n - 1, so use .var() (not ddof=0 or np.var)."),
    (_beta_positional,
     "line the two up by DATE first (pd.concat([s, m], axis=1, sort=True).dropna()). Dropping NaN from each separately shifts one against the other."),
]


VAR_SLIPS = [
    (lambda r, amt: float(np.percentile(pd.Series(r, dtype=float).dropna(), 95) * amt),
     "that's the 95th percentile (a GOOD day). A bad day is the 5th: np.percentile(r, 5)."),
    (lambda r, amt: float(np.percentile(pd.Series(r, dtype=float).dropna(), 5) * amt),
     "return the loss as a POSITIVE number: -np.percentile(r, 5) * amount."),
    (lambda r, amt: float(-np.percentile(pd.Series(r, dtype=float).dropna(), 5)),
     "that's the loss as a fraction (0.031 = 3.1%). Multiply by `amount` to get dollars."),
    (lambda r, amt: float(-pd.Series(r, dtype=float).dropna().mean() * amt),
     "that's the average day. VaR is a bad day: the 5th percentile, not the mean."),
]


def _r32(c):
    return c.pct_change().dropna()


SLIPS[32] = [
    (lambda c: float(_r32(c).mean() / _r32(c).std()),
     "that's the DAILY Sharpe. Annualize: average daily return * 252, and std * sqrt(252)."),
    (lambda c: float(_r32(c).mean() / _r32(c).std() * 252),
     "volatility grows with the SQUARE ROOT of time: std * sqrt(252), while the average return * 252."),
    (lambda c: float(c.mean() * 252 / (c.std() * np.sqrt(252))),
     "use daily RETURNS (curve.pct_change().dropna()), not the curve's values."),
    (lambda c: float((c.iloc[-1] ** (1 / ((c.index[-1] - c.index[0]).days / 365.25)) - 1) / (_r32(c).std() * np.sqrt(252))),
     "SemiScope's Sharpe uses the AVERAGE daily return * 252 on top, not the CAGR."),
]


def _eb(r, w, mode):
    wv = pd.Series(w, dtype=float).reindex(r.columns).fillna(0)
    if mode == "equal":
        wv = pd.Series(1.0, index=r.columns)
    wv = wv / wv.sum()
    cov = (r.corr() if mode == "corr" else r.cov()).values
    sig = np.diag(cov) if mode == "var" else np.sqrt(np.diag(cov))
    port = float(np.sqrt(wv.values @ cov @ wv.values))
    x = wv.values @ sig / port
    return float(x if mode == "nosq" else x ** 2)


EB_SLIPS = [
    (lambda r, w: _eb(r, w, "var"), "the top uses each stock's STD (sqrt of the diagonal), not its variance."),
    (lambda r, w: _eb(r, w, "nosq"), "square it: effective bets = (sum(w * sigma) / portfolio std) ** 2."),
    (lambda r, w: _eb(r, w, "corr"), "use the COVARIANCE matrix (r.cov()), not the correlation matrix."),
    (lambda r, w: _eb(r, w, "equal"), "use the weights you were given (reindexed to r's columns), not equal weights."),
]


# (forgetting to normalize the weights is harmless here: the ratio doesn't change with their scale)
def _paper(entries, px, cost_bps=10, mode=""):
    daily = px.pct_change()
    value, prev_w = 1.0, pd.Series(dtype=float)
    ents = [dict(e, picks=entries[0]["picks"]) for e in entries] if mode == "first" else entries
    for i, e in enumerate(ents):
        d = pd.Timestamp(e["date"])
        end = pd.Timestamp(ents[i + 1]["date"]) if i + 1 < len(ents) else px.index[-1]
        picks = [t for t in e["picks"] if t in px] if mode == "dropmissing" else e["picks"]
        if mode == "price":
            last = px.loc[:d].ffill().iloc[-1].reindex(picks).fillna(0)
            w = last / last.sum()
        else:
            w = pd.Series(1 / len(picks), index=picks)
        if mode != "nocost":
            value *= 1 - w.subtract(prev_w, fill_value=0).abs().sum() * cost_bps / 1e4
        lo = daily.index >= d if mode == "peek" else daily.index > d
        period = daily.loc[lo & (daily.index <= end)].reindex(columns=picks)
        period = period.dropna(axis=1, how="any") if mode == "dropmissing" else period.fillna(0)
        if mode == "dropmissing":
            w = w.reindex(period.columns)
            w = w / w.sum()
        if len(period):
            growth = (1 + period).cumprod()
            drifted = growth.iloc[-1] * w
            value = value * drifted.sum()
            prev_w = drifted / drifted.sum()
        else:
            prev_w = w
    return float(value - 1)


SLIPS[33] = [
    (lambda e, p, c=10: _paper(e, p, c, "first"),
     "each entry REPLACES the picks: use that entry's own picks for its period, not the first entry's forever."),
    (lambda e, p, c=10: _paper(e, p, c, "price"),
     "equal weight: 1 / len(picks) each, not weights by price."),
    (lambda e, p, c=10: _paper(e, p, c, "peek"),
     "start the day AFTER the entry date (daily.index > d): the picks were made with that day's close, so its move already happened."),
    (lambda e, p, c=10: _paper(e, p, c, "dropmissing"),
     "a pick with no price counts as 0% that day (.reindex(columns=picks).fillna(0)); don't drop it and re-weight the rest."),
    (lambda e, p, c=10: _paper(e, p, c, "nocost"),
     "charge the trading cost at each entry: value *= 1 - turnover * cost_bps / 10000."),
]


EARLY_SLIPS = SLIPS            # older name (round 87)


def _slip_hint(n):
    def hint(got, *args):
        for wrong, msg in EARLY_SLIPS[n]:
            try:
                w = wrong(*args)
                both_nan = isinstance(w, float) and np.isnan(w) and isinstance(got, (int, float)) and np.isnan(float(got))
                if both_nan or _same(got, w) is None:
                    return f"\n    Hint: {msg}"
            except Exception:  # noqa: BLE001  (a slip that can't run on this case just doesn't match)
                pass
        return ""
    return hint


HINTS = {**{n: _slip_hint(n) for n in SLIPS}, 17: _hint17, 18: _hint18, 19: _hint19, 20: _hint20, 21: _hint21, 22: _hint22, 23: _hint23, 24: _hint24,
         27: _hint27, 28: _hint28}  # 29 compares its own way (see check())
