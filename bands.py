"""
Price nets: how far could a stock stray from today's price? Five ways to guess, compared fairly.

THE QUESTION
    For a stock and a horizon of h trading days, find a half-width c so that, with probability
    `level` (say 90%), the price never moves more than c (as a log-return) away from today's
    price at ANY point in the next h days. The "net" is  price x exp(-c)  to  price x exp(+c).
    That is the "estimated max change": the largest swing during the window, not just where the
    price ends up. (For 1 day with closing prices only, it is simply the size of the move.)

    Formally, with S_k = log(P[t+k] / P[t]):    M = max over k = 1..h of |S_k|
    and c is the `level` quantile of M. "90% net" means: M <= c about 90% of the time.

THE METHODS (each one predicts c from past daily log-returns only; no look-ahead)
    normal     bell-curve volatility over the last year. Simple, but real tails are fatter.
    quantile   look at what the stock really did: M over every past h-day window (3 years).
    ewma       like normal, but recent days count more (RiskMetrics, lambda = 0.94), so it
               reacts when volatility changes.
    bootstrap  resample 5-day chunks of the stock's own history thousands of times and read c
               off the simulated paths (keeps volatility clusters intact).
    range      (Parkinson) bell curve with volatility measured from daily high-low ranges.
               Needs daily highs and lows, which the pipeline does not download yet, so it is
               tested but not used on live data.

HOW THEY ARE JUDGED (walk-forward: at every past date use only what was known that day)
    coverage   how often the realized M stayed inside c. A 90% net should hold ~90% of the time.
    loss       "pinball" loss for a quantile forecast: punishes a net that is too narrow
               (M escaped) and, more gently, one that is too wide. Lower is better.
    The BLEND weights each method by its past loss (shrunk halfway to equal weights, because
    weights fitted to a short history overfit), optionally using only past days with the same
    market mood (calm vs stormy: is the universe's recent volatility in its top quarter?).

Informational only: nothing here changes the picks, the backtest or the paper portfolio.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache
from statistics import NormalDist

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

HORIZONS = (1, 5, 21)          # trading days: tomorrow, next week, next month
LEVELS = (0.5, 0.9)            # "typical" and "almost always"
LOOKBACK = 756                 # ~3 years of daily returns for the data-hungry methods
SIGMA_WINDOW = 252             # ~1 year for the plain bell-curve volatility
MIN_HISTORY = 252              # a year of returns before any forecast
MIN_WINDOWS = 60               # the quantile method needs at least this many past h-day windows
EWMA_LAMBDA = 0.94
BLOCK = 5                      # bootstrap chunk length (a trading week)
N_SIMS = 400
METHODS = ("normal", "quantile", "ewma", "bootstrap")
LABELS = {"normal": "Bell curve", "quantile": "Past windows", "ewma": "Recent-weighted",
          "bootstrap": "Resampled", "range": "High-low range",
          "equal": "Equal average", "perf": "Weighted blend", "regime": "Mood-weighted blend"}
SHRINK = 0.5                   # 0 = equal weights, 1 = fully by past loss
POWER = 2                      # weight ~ loss ** -POWER
KEEP = 120                     # most recent evaluation dates used for weights
MIN_OBS = 20                   # fewer known dates than this: equal weights
MIN_REGIME_OBS = 25            # fewer same-mood dates than this: use all dates
STORM_Q = 0.75


# ----------------------------------------------------------------------------- the shared yardstick
@lru_cache(maxsize=None)
def kappa(h: int, level: float, n: int = 100_000, seed: int = 7) -> float:
    """`level` quantile of the largest |swing| of a standard random walk over h steps."""
    if h == 1:
        return NormalDist().inv_cdf(0.5 + level / 2)           # exact: half-normal
    z = np.random.default_rng(seed).standard_normal((n, h)).cumsum(axis=1)
    return float(np.quantile(np.abs(z).max(axis=1), level))


def parkinson_sigma(high, low) -> float:
    """Daily volatility from high-low ranges: sqrt(mean(ln(H/L)^2) / (4 ln 2))."""
    h, l = np.asarray(high, float), np.asarray(low, float)
    ok = np.isfinite(h) & np.isfinite(l) & (h > 0) & (l > 0) & (h >= l)
    if ok.sum() < 20:
        return float("nan")
    return float(math.sqrt(np.mean(np.log(h[ok] / l[ok]) ** 2) / (4 * math.log(2))))


# ----------------------------------------------------------------------------- the methods
# Each takes r (past daily log-returns, oldest first, all finite) and returns {(h, level): c}.
def net_normal(r: np.ndarray, hs=HORIZONS, levels=LEVELS) -> dict:
    sigma = float(np.std(r[-SIGMA_WINDOW:], ddof=1))
    return {(h, l): sigma * kappa(h, l) for h in hs for l in levels}


def net_range(r: np.ndarray, hs=HORIZONS, levels=LEVELS, sigma: float | None = None) -> dict:
    """Bell curve with a volatility measured from high-low ranges (pass sigma=parkinson_sigma(...))."""
    if sigma is None or not math.isfinite(sigma):
        return {(h, l): float("nan") for h in hs for l in levels}
    return {(h, l): sigma * kappa(h, l) for h in hs for l in levels}


def net_ewma(r: np.ndarray, hs=HORIZONS, levels=LEVELS) -> dict:
    x = r[-LOOKBACK:]
    var = float(pd.Series(x ** 2).ewm(alpha=1 - EWMA_LAMBDA, adjust=False).mean().iloc[-1])
    sigma = math.sqrt(var)
    return {(h, l): sigma * kappa(h, l) for h in hs for l in levels}


def net_quantile(r: np.ndarray, hs=HORIZONS, levels=LEVELS) -> dict:
    x = r[-LOOKBACK:]
    cs = np.concatenate([[0.0], np.cumsum(x)])
    out = {}
    for h in hs:
        if len(cs) - h < MIN_WINDOWS:
            for l in levels:
                out[(h, l)] = float("nan")
            continue
        win = sliding_window_view(cs, h + 1)
        m = np.abs(win[:, 1:] - win[:, [0]]).max(axis=1)
        for l in levels:
            out[(h, l)] = float(np.quantile(m, l))
    return out


def net_bootstrap(r: np.ndarray, hs=HORIZONS, levels=LEVELS, n_sims: int = N_SIMS, seed: int = 11) -> dict:
    x = r[-LOOKBACK:]
    hmax = max(hs)
    nblk = -(-hmax // BLOCK)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(x) - BLOCK + 1, size=(n_sims, nblk))
    idx = (starts[:, :, None] + np.arange(BLOCK)).reshape(n_sims, nblk * BLOCK)[:, :hmax]
    paths = np.cumsum(x[idx], axis=1)
    out = {}
    for h in hs:
        m = np.abs(paths[:, :h]).max(axis=1)
        for l in levels:
            out[(h, l)] = float(np.quantile(m, l))
    return out


FUNCS = {"normal": net_normal, "quantile": net_quantile, "ewma": net_ewma, "bootstrap": net_bootstrap}


def nets_at(r: np.ndarray, hs=HORIZONS, levels=LEVELS, methods=METHODS) -> dict:
    """{method: {(h, level): c}} from past returns r, or all-NaN when there is too little history."""
    r = r[np.isfinite(r)]
    if len(r) < MIN_HISTORY:
        return {m: {(h, l): float("nan") for h in hs for l in levels} for m in methods}
    return {m: FUNCS[m](r, hs, levels) for m in methods}


# ----------------------------------------------------------------------------- scoring
def pinball(realized: np.ndarray, forecast: np.ndarray, level: float) -> np.ndarray:
    """Quantile loss: (y - q) * (level - [y < q]). Zero-mean-optimal at the true `level` quantile."""
    d = realized - forecast
    return d * (level - (d < 0))


def forward_max_swing(px: pd.DataFrame, h: int) -> np.ndarray:
    """(T, N) array: for each date i, max over k=1..h of |log(P[i+k] / P[i])|; NaN when unknown."""
    lp = np.log(px.where(px > 0)).values
    T = lp.shape[0]
    m = np.zeros_like(lp)
    for k in range(1, h + 1):
        m[: T - k] = np.maximum(m[: T - k], np.abs(lp[k:] - lp[: T - k]))
        # np.maximum propagates NaN, so a gap anywhere in the window makes it unknown
    m[max(T - h, 0):] = np.nan
    return m


def market_mood(px: pd.DataFrame, window: int = 21, q: float = STORM_Q) -> pd.Series:
    """'stormy' when the universe's recent volatility is above its own past q-quantile, else 'calm'."""
    r = np.log(px.where(px > 0)).diff()
    vol = r.mean(axis=1).rolling(window, min_periods=window).std()
    thr = vol.expanding(min_periods=MIN_HISTORY).quantile(q).shift(1)
    stormy = (vol > thr) & thr.notna()
    return stormy.map({True: "stormy", False: "calm"})


def blend_weights(loss_hist: np.ndarray, power: float = POWER, shrink: float = SHRINK) -> np.ndarray:
    """Weights per method from a (n_dates, n_methods) history of losses; equal when too little data."""
    n_m = loss_hist.shape[1] if loss_hist.ndim == 2 else 0
    equal = np.full(n_m, 1.0 / n_m) if n_m else np.array([])
    if loss_hist.ndim != 2 or len(loss_hist) < MIN_OBS:
        return equal
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(loss_hist, axis=0)
    if not np.all(np.isfinite(mean)) or np.any(mean <= 0):
        return equal
    perf = mean ** -power
    perf /= perf.sum()
    return shrink * perf + (1 - shrink) * equal


# ----------------------------------------------------------------------------- the walk-forward study
def evaluate(px: pd.DataFrame, hs=HORIZONS, levels=LEVELS, methods=METHODS, step: int = 10,
             max_dates: int | None = 200, power: float = POWER, shrink: float = SHRINK) -> dict:
    """Run every method at past dates (every `step` trading days) and score it against what happened.

    Returns the comparison table, the blend weights now, and the arrays behind them."""
    px = px.where(px > 0)
    T, N = px.shape
    r = np.log(px).diff().values
    first = MIN_HISTORY + 1
    pos = list(range(first, T - 1, step))
    if max_dates:
        pos = pos[-max_dates:]
    mood_series = market_mood(px)
    mood = mood_series.reindex(px.index).fillna("calm").values
    swing = {h: forward_max_swing(px, h) for h in hs}

    # C[m][(h, l)] : (n_dates, N) forecasts
    C = {m: {(h, l): np.full((len(pos), N), np.nan) for h in hs for l in levels} for m in methods}
    for oi, i in enumerate(pos):
        for j in range(N):
            col = r[: i + 1, j]
            col = col[np.isfinite(col)]
            if len(col) < MIN_HISTORY:
                continue
            res = nets_at(col, hs, levels, methods)
            for m in methods:
                for key, v in res[m].items():
                    C[m][key][oi, j] = v

    pos_arr = np.array(pos)
    table, weights_now, series = {}, {}, {}
    for h in hs:
        real = swing[h][pos_arr]                                             # (n_dates, N)
        for l in levels:
            stack = np.stack([C[m][(h, l)] for m in methods])                # (M, n_dates, N)
            valid = np.isfinite(real) & np.all(np.isfinite(stack), axis=0)
            loss = np.stack([np.where(valid, pinball(real, C[m][(h, l)], l), np.nan) for m in methods])
            with warnings.catch_warnings():                                  # a date with no valid stock is just NaN
                warnings.simplefilter("ignore", RuntimeWarning)
                origin_loss = np.nanmean(np.where(valid[None], loss, np.nan), axis=2).T   # (n_dates, M)

            def weights_for(oi):                                             # only outcomes known by date oi
                known = [k for k in range(oi) if pos[k] + h <= pos[oi]][-KEEP:]
                w_all = blend_weights(origin_loss[known], power, shrink) if known else blend_weights(np.empty((0, len(methods))))
                same = [k for k in known if mood[pos[k]] == mood[pos[oi]]]
                w_reg = blend_weights(origin_loss[same], power, shrink) if len(same) >= MIN_REGIME_OBS else w_all
                return w_all, w_reg

            perf_c = np.full_like(real, np.nan)
            reg_c = np.full_like(real, np.nan)
            equal_c = np.mean(stack, axis=0)
            for oi in range(len(pos)):
                w_all, w_reg = weights_for(oi)
                perf_c[oi] = np.tensordot(w_all, stack[:, oi, :], axes=1)
                reg_c[oi] = np.tensordot(w_reg, stack[:, oi, :], axes=1)

            rows = []
            cand = [(m, C[m][(h, l)]) for m in methods] + [("equal", equal_c), ("perf", perf_c), ("regime", reg_c)]
            for name, f in cand:
                ok = valid & np.isfinite(f)
                if not ok.any():
                    continue
                rows.append({"m": name, "cov": float((real[ok] <= f[ok]).mean()), "width": float(f[ok].mean()),
                             "loss": float(pinball(real[ok], f[ok], l).mean()), "n": int(ok.sum())})
            table[(h, l)] = rows
            series[(h, l)] = {"real": real, "valid": valid, "stack": stack, "equal": equal_c, "perf": perf_c,
                              "regime": reg_c, "pos": pos_arr}            # kept so tests can prove nothing looks ahead

            # blend weights for TODAY: every outcome that is known by the end of the data
            last = T - 1
            known = [k for k in range(len(pos)) if pos[k] + h <= last][-KEEP:]
            w_all = blend_weights(origin_loss[known], power, shrink) if known else blend_weights(np.empty((0, len(methods))))
            now_mood = str(mood_series.iloc[-1]) if T else "calm"
            w_by = {"all": w_all}
            for md in ("calm", "stormy"):
                same = [k for k in known if mood[pos[k]] == md]
                w_by[md] = blend_weights(origin_loss[same], power, shrink) if len(same) >= MIN_REGIME_OBS else w_all
            weights_now[(h, l)] = {"mood": now_mood,
                                   **{k: {m: float(w) for m, w in zip(methods, v)} for k, v in w_by.items()}}
    return {"table": table, "weights": weights_now, "methods": list(methods), "n_dates": len(pos),
            "first": px.index[pos[0]] if pos else None, "last": px.index[pos[-1]] if pos else None,
            "mood": str(mood_series.iloc[-1]), "_series": series}


# ----------------------------------------------------------------------------- today's nets
def current_nets(px: pd.DataFrame, tickers, weights: dict, hs=HORIZONS, levels=LEVELS,
                 methods=METHODS, mood: str = "calm") -> dict:
    """{ticker: {(h, level): {'blend': c, 'lo': min over methods, 'hi': max over methods}}}"""
    out = {}
    for t in tickers:
        if t not in px.columns:
            continue
        r = np.log(px[t].where(px[t] > 0)).diff().values
        r = r[np.isfinite(r)]
        res = nets_at(r, hs, levels, methods)
        d = {}
        for h in hs:
            for l in levels:
                vals = np.array([res[m][(h, l)] for m in methods])
                if not np.all(np.isfinite(vals)):
                    continue
                w = weights.get((h, l), {})
                wm = w.get(mood) or w.get("all")
                if not wm:
                    wv = np.full(len(methods), 1.0 / len(methods))
                else:
                    wv = np.array([wm[m] for m in methods])
                d[(h, l)] = {"blend": float(wv @ vals), "lo": float(vals.min()), "hi": float(vals.max()),
                             "c": {m: float(v) for m, v in zip(methods, vals)}}
        if d:
            out[t] = d
    return out


# ----------------------------------------------------------------------------- did the price escape its net?
def track(px: pd.DataFrame, cur: dict, prev_track: dict | None, hs=HORIZONS, levels=LEVELS) -> dict:
    """Remember each net from the day it was set and watch whether the price breaks out of it.

    {ticker: {h: {'active': A, 'last': A or None}}} where A = {date, ref, age, up, down, c: {level: {method: c}}}
      date/ref  the day the net was set and that day's close (the centre of the net)
      age       trading days since (capped at h: after h days the window is over)
      up/down   the biggest rise / fall (as log-returns from ref) seen so far inside the window
    A net stays fixed for its h-day window, then is judged ('last') and replaced by a fresh one set at
    the latest close. This is what lets a page say "this stock has left the net it had on Oct 21".
    Only closing prices are used, so an intraday spike that closed back inside is not counted.
    """
    out = {}
    for t, d in cur.items():
        if t not in px.columns:
            continue
        s = px[t].where(px[t] > 0).dropna()
        if s.empty:
            continue
        for h in hs:
            if not all((h, l) in d for l in levels):
                continue
            old = ((prev_track or {}).get(t) or {}).get(str(h)) or ((prev_track or {}).get(t) or {}).get(h) or {}
            act, last = old.get("active"), old.get("last")
            if act:
                after = s[s.index > pd.Timestamp(act["date"])].iloc[:h]
                mv = np.log(after.values / act["ref"]) if len(after) else np.array([0.0])
                act = {**act, "age": int(len(after)),
                       "up": round(float(max(mv.max(), 0.0)), 5), "down": round(float(min(mv.min(), 0.0)), 5)}
                if act["age"] >= h:                       # window over: judge it and start a new net
                    last, act = act, None
            if not act:
                act = {"date": s.index[-1].strftime("%Y-%m-%d"), "ref": round(float(s.iloc[-1]), 4), "age": 0,
                       "up": 0.0, "down": 0.0,
                       "c": {str(l): {m: round(v, 5) for m, v in d[(h, l)]["c"].items()} for l in levels}}
            out.setdefault(t, {})[str(h)] = {"active": act, "last": last}
    return out


# ----------------------------------------------------------------------------- the report for data.json
def _pct(c: float) -> float:
    """Log half-width -> approximate % move (upper side), rounded for display."""
    return round((math.exp(c) - 1) * 100, 2)


def _read(table: dict) -> str:
    """One plain-English sentence about the 5-day, 90% net."""
    rows = table.get((5, 0.9)) or table.get((HORIZONS[1], LEVELS[-1]))
    if not rows:
        return ""
    by = {r["m"]: r for r in rows}
    meth = [r for r in rows if r["m"] in METHODS]
    best = min(meth, key=lambda r: r["loss"])
    nrm = by.get("normal")
    parts = [f"For a 5-day, 90% net, the best single method was \"{LABELS[best['m']]}\" "
             f"(held {best['cov']:.0%} of the time)."]
    if nrm and best["m"] != "normal":
        parts.append(f"The plain bell curve held {nrm['cov']:.0%}.")
    if "perf" in by:
        parts.append(f"The weighted blend held {by['perf']['cov']:.0%} and the equal average {by['equal']['cov']:.0%}.")
    return " ".join(parts)


def build(px: pd.DataFrame, close_last: pd.Series | None, tickers, prev: dict | None = None,
          fast: bool = False, hs=HORIZONS, levels=LEVELS, methods=METHODS, step: int = 10) -> dict:
    """The 'bands' block for data['research']. `prev` is the last run's block; on --fast runs its
    comparison table and weights are reused and only today's nets are recomputed."""
    if px is None or px.empty or len(px) < MIN_HISTORY + 60:
        return {"available": False, "reason": f"needs about {MIN_HISTORY + 60} days of prices"}
    asof = px.index[-1].strftime("%Y-%m-%d")
    reuse = bool(fast and prev and prev.get("available") and prev.get("table") and prev.get("weights"))
    if reuse:                                   # --fast: keep last full run's comparison, refresh only today's nets
        table_out, weights_out = prev["table"], prev["weights"]
        mood = str(market_mood(px).iloc[-1])
        study_asof, n_dates, read = prev.get("study_asof"), prev.get("n_dates"), prev.get("read", "")
    else:
        ev = evaluate(px, hs, levels, methods, step=step)
        mood = ev["mood"]
        study_asof, n_dates = asof, ev["n_dates"]
        table_out = {f"{h}|{l}": [{**r, "cov": round(r["cov"], 4), "width": round(r["width"], 5),
                                     "loss": round(r["loss"], 6)} for r in rows]
                     for (h, l), rows in ev["table"].items()}
        weights_out = {f"{h}|{l}": {k: ({m: round(w, 4) for m, w in v.items()} if isinstance(v, dict) else v)
                                    for k, v in w.items()} for (h, l), w in ev["weights"].items()}
        read = _read(ev["table"])
    # both paths use the weights exactly as stored (rounded), so a --fast run reproduces a full run
    weights = {(int(k.split("|")[0]), float(k.split("|")[1])): v for k, v in weights_out.items()}
    cur = current_nets(px, tickers, weights, hs, levels, methods, mood)
    tracked = track(px, cur, (prev or {}).get("track") if prev and prev.get("available") else None, hs, levels)
    current = {}
    for t, d in cur.items():
        last = float(close_last[t]) if close_last is not None and t in close_last.index and np.isfinite(close_last[t]) else None
        current[t] = {f"{h}|{l}": {"pct": _pct(v["blend"]), "lo_pct": _pct(v["lo"]), "hi_pct": _pct(v["hi"]),
                                   "c": {m: round(x, 5) for m, x in v["c"].items()},
                                   "low": round(last * math.exp(-v["blend"]), 2) if last else None,
                                   "high": round(last * math.exp(v["blend"]), 2) if last else None}
                      for (h, l), v in d.items()}
    return {"available": True, "asof": asof, "study_asof": study_asof, "n_dates": n_dates,
            "horizons": list(hs), "levels": list(levels), "methods": list(methods), "labels": LABELS,
            "mood": mood, "table": table_out, "weights": weights_out, "current": current, "track": tracked,
            "read": read}
