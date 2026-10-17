"""
Semis/hardware factor model, computed strictly as of a given date.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import FACTORS, MIN_FACTORS

STALE_DAYS = 200  # ignore fundamentals if the latest quarter is older than this

# Split-adjusted (NOT dividend-adjusted) closes used for market cap. run.py sets
# this; if left None we fall back to the total-return prices passed to score().
MARKET = {"close": None}


def _known(series: pd.DataFrame | None, asof) -> pd.DataFrame | None:
    """Rows of a point-in-time series that had been filed by `asof`."""
    if series is None or series.empty:
        return series
    return series[series["filed"] < asof].sort_values("end")


# ---------------------------------------------------------------------------
# Fast path. score() runs ~240 times per pipeline run x 30 companies, so the
# pandas filtering above was the #1 cost. _arrays() converts each series to
# plain numpy arrays ONCE (sorted by quarter end); _Known is the same
# "filed before asof" view as _known(), just much cheaper. Results are
# identical (tests/test_speed.py checks this against the slow version).
# ---------------------------------------------------------------------------
_ARR: dict[int, tuple] = {}
DAY = np.int64(86_400_000_000_000)


def _arrays(df: pd.DataFrame | None):
    if df is None or df.empty:
        return None
    hit = _ARR.get(id(df))
    if hit is not None and hit[0] is df:
        return hit[1]
    d = df.sort_values("end")
    arr = (d["end"].values.astype("datetime64[ns]").astype(np.int64),
           d["val"].to_numpy(dtype=float),
           d["filed"].values.astype("datetime64[ns]").astype(np.int64))
    _ARR[id(df)] = (df, arr)
    return arr


class _Known:
    """Quarters filed before `asof`: .end (int64 ns) and .val, sorted by end."""
    __slots__ = ("end", "val")

    def __init__(self, df, asof_ns):
        a = _arrays(df)
        if a is None:
            self.end = self.val = np.empty(0)
            return
        m = a[2] < asof_ns
        self.end, self.val = a[0][m], a[1][m]

    def __len__(self):
        return len(self.end)

    def at(self, end_ns, tol: int = 20) -> float:
        """Like _val(): value for the quarter ending within tol days of end_ns."""
        if not len(self.end):
            return np.nan
        d = np.abs(self.end - end_ns) // DAY
        i = int(np.argmin(d))
        return float(self.val[i]) if d[i] <= tol else np.nan

    def ttm(self, rev_end_ns=None) -> float:
        if len(self.end) < 4:
            return np.nan
        e = self.end[-4:]
        if rev_end_ns is not None and abs(int(e[-1] - rev_end_ns)) // DAY > 20:
            return np.nan
        span = int(e[-1] - e[0]) // DAY
        return float(self.val[-4:].sum()) if 250 <= span <= 300 else np.nan


def _val(s: pd.DataFrame | None, end: pd.Timestamp, tol: int = 20) -> float:
    """Value for the quarter ending near `end` (±tol days), or NaN."""
    if s is None or s.empty:
        return np.nan
    d = (s["end"] - end).abs().dt.days
    i = d.idxmin()
    return s.loc[i, "val"] if d.loc[i] <= tol else np.nan


def ttm(series: dict, asof, key: str, rev_end: pd.Timestamp | None = None) -> float:
    """Trailing-12-month sum of a quarterly series known at `asof` (NaN if gaps).
    If rev_end is given, the 4 quarters must end at that same quarter."""
    return _Known(series.get(key), pd.Timestamp(asof).value).ttm(
        None if rev_end is None else pd.Timestamp(rev_end).value)


def sales_yield(series: dict, asof, price: float | None) -> float:
    """TTM revenue / market cap (higher = cheaper). Uses only filed data."""
    a = pd.Timestamp(asof).value
    rev, sh = _Known(series.get("revenue"), a), _Known(series.get("shares"), a)
    if len(rev) < 4 or not len(sh) or not price or np.isnan(price):
        return np.nan
    e = rev.end[-4:]
    span = int(e[-1] - e[0]) // DAY
    if not 250 <= span <= 300 or (a - int(e[-1])) // DAY > STALE_DAYS:
        return np.nan
    if (a - int(sh.end[-1])) // DAY > 400 or sh.val[-1] <= 0:
        return np.nan
    return float(rev.val[-4:].sum()) / (float(sh.val[-1]) * price)


def fundamental_factors(series: dict, asof, price: float | None = None) -> dict:
    """All fundamental factors for ONE company, using only data filed before `asof`."""
    asof = pd.Timestamp(asof)
    a = asof.value
    rev = _Known(series.get("revenue"), a)
    cogs = _Known(series.get("cogs"), a)
    inv = _Known(series.get("inventory"), a)
    out = {k: np.nan for k in ("rev_growth", "rev_accel", "gm_change", "inv_days_change",
                                "op_margin_change", "rd_intensity", "fcf_margin", "capex_intensity")}
    out["latest_quarter"] = None
    out["sales_yield"] = sales_yield(series, asof, price)
    if len(rev) < 6:
        return out
    L, prev = int(rev.end[-1]), int(rev.end[-2])
    if (a - L) // DAY > STALE_DAYS:
        return out
    yr = 364 * int(DAY)
    out["latest_quarter"] = pd.Timestamp(L).strftime("%Y-%m-%d")

    r0, r1 = rev.at(L), rev.at(L - yr)
    p0, p1 = rev.at(prev), rev.at(prev - yr)
    g_now = r0 / r1 - 1 if r1 and r1 > 0 else np.nan
    g_prev = p0 / p1 - 1 if p1 and p1 > 0 else np.nan
    out["rev_growth"] = g_now
    out["rev_accel"] = g_now - g_prev

    c0, c1 = cogs.at(L), cogs.at(L - yr)
    if r0 and r1 and r0 > 0 and r1 > 0:
        out["gm_change"] = (1 - c0 / r0) - (1 - c1 / r1)
        out["gross_margin"] = 1 - c0 / r0

    i0, i1 = inv.at(L, tol=10), inv.at(L - yr, tol=10)
    if c0 and c1 and c0 > 0 and c1 > 0:
        dio0, dio1 = i0 / c0 * 91, i1 / c1 * 91
        out["inv_days_change"] = dio0 - dio1
        out["inv_days"] = dio0

    # operating margin change YoY
    opi = _Known(series.get("opinc"), a)
    o0, o1 = opi.at(L), opi.at(L - yr)
    if r0 and r1 and r0 > 0 and r1 > 0 and pd.notna(o0) and pd.notna(o1):
        out["op_margin_change"] = o0 / r0 - o1 / r1
        out["op_margin"] = o0 / r0

    # TTM ratios: R&D intensity, FCF margin, capex intensity
    rev_ttm = rev.ttm()
    if rev_ttm and rev_ttm > 0:
        rd = _Known(series.get("rd"), a).ttm(L)
        cfo, capex = _Known(series.get("cfo"), a).ttm(L), _Known(series.get("capex"), a).ttm(L)
        out["rd_intensity"] = rd / rev_ttm
        out["fcf_margin"] = (cfo - capex) / rev_ttm
        out["capex_intensity"] = capex / rev_ttm
    return out


def price_factors(px: pd.DataFrame, asof) -> pd.DataFrame:
    """Momentum (6-1 month) and 6-month volatility from prices known at `asof`."""
    hist = px[px.index <= pd.Timestamp(asof)]
    if len(hist) < 130:
        return pd.DataFrame(index=px.columns, columns=["momentum", "low_vol"], dtype=float)
    p_now_skip = hist.iloc[-21]   # ~1 month ago
    p_6m = hist.iloc[-126]        # ~6 months ago
    mom = p_now_skip / p_6m - 1
    vol = hist.iloc[-126:].pct_change().std() * np.sqrt(252)
    return pd.DataFrame({"momentum": mom, "low_vol": vol})


def z_stats(col: pd.Series) -> dict:
    """The numbers _z() uses: winsor bounds (5th/95th percentile) and the clipped mean / std.
    Exposed so the dashboard can show the arithmetic behind a z-score (walkthrough.py)."""
    s = col.astype(float)
    lo, hi = s.quantile(0.05), s.quantile(0.95)
    c = s.clip(lo, hi)
    return {"lo": lo, "hi": hi, "mean": c.mean(), "sd": c.std()}


def _z(col: pd.Series) -> pd.Series:
    """Cross-sectional z-score after trimming the top/bottom 5% (winsorizing)."""
    st = z_stats(col)
    s = col.astype(float).clip(st["lo"], st["hi"])  # winsorize so one crazy number can't dominate
    sd = st["sd"]
    return (s - st["mean"]) / sd if sd and sd > 0 else s * 0


STALE_MAX_DAYS = 3   # trading days a price may be missing before the stock drops out


def stale_days(s: pd.Series) -> int:
    """How many trading days at the end of `s` have no price (0 = fresh)."""
    v = s.notna().to_numpy()
    if not v.any():
        return len(v)
    return int(len(v) - 1 - np.flatnonzero(v)[-1])


def _prices_at(px: pd.DataFrame, asof, tickers: list[str]) -> dict[str, float]:
    """Last known (split-adjusted) close for each ticker on or before `asof`."""
    close = MARKET["close"] if MARKET["close"] is not None else px
    hist = close[close.index <= pd.Timestamp(asof)]
    return {t: (hist[t].dropna().iloc[-1] if t in hist and hist[t].notna().any() else np.nan)
            for t in tickers}


# Optional memo shared by backtest, robustness, walk-forward and explain within ONE
# pipeline run (run.py turns it on). Off by default so tests never share results.
MEMO: dict | None = None


def score(all_series: dict, px: pd.DataFrame, asof, tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Raw factors, z-scores, and composite score for each ticker as of `asof`."""
    if MEMO is not None:
        key = (id(all_series), id(px), id(MARKET["close"]), pd.Timestamp(asof), tuple(tickers))
        if key not in MEMO:
            MEMO[key] = _score(all_series, px, asof, tickers)
        ranked, z = MEMO[key]
        return ranked.copy(), z.copy()
    return _score(all_series, px, asof, tickers)


def _score(all_series: dict, px: pd.DataFrame, asof, tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = _prices_at(px, asof, tickers)
    rows = {t: fundamental_factors(all_series.get(t, {}), asof, p[t]) for t in tickers}
    raw = pd.DataFrame(rows).T
    pf = price_factors(px[[t for t in tickers if t in px.columns]], asof)
    raw = raw.join(pf, how="left")

    # can't rank a stock that wasn't trading yet (or stopped trading). A missing last bar or two
    # (data hiccup, short halt) is tolerated: the stock stays ranked on its last price, flagged stale.
    hist = px[px.index <= pd.Timestamp(asof)]
    traded = [t for t in tickers if t in hist.columns and hist[t].notna().sum() >= 130
              and hist[t].iloc[-(STALE_MAX_DAYS + 1):].notna().any()]
    raw = raw.loc[raw.index.intersection(traded)]
    raw["stale_days"] = [stale_days(hist[t]) for t in raw.index]

    z = pd.DataFrame({f: _z(raw[f]) * FACTORS[f]["sign"] for f in FACTORS})
    names = [f for f, c in FACTORS.items() if c["weight"] > 0]  # informational = weight 0
    w = pd.Series({f: FACTORS[f]["weight"] for f in names})
    have = z[names].notna()
    composite = (z[names].fillna(0) * w).sum(axis=1) / (have * w).sum(axis=1)
    partial = composite.copy()
    composite[have.sum(axis=1) < MIN_FACTORS] = np.nan
    raw["n_factors"] = have.sum(axis=1)
    raw["score"] = composite
    raw["rank"] = raw["score"].rank(ascending=False, method="first")
    # too few factors to be ranked (e.g. a foreign filer with price data only): still show
    # roughly where it would land on what it has, like a watchlist stock. Never picked.
    thin = raw.index[composite.isna() & partial.notna() & (have.sum(axis=1) > 0)]
    if len(thin):
        uni = composite.dropna()
        raw["would_rank"] = np.nan
        raw.loc[thin, "would_rank"] = [int((uni > partial[t]).sum()) + 1 for t in thin]
        raw.loc[thin, "partial_score"] = partial[thin]
    return raw.sort_values("score", ascending=False), z


def score_outsiders(all_series: dict, px: pd.DataFrame, asof, ranked: pd.DataFrame,
                    extra: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score non-universe stocks (e.g. your watchlist) on the universe's yardstick.

    Each factor is z-scored with the UNIVERSE's mean/std (and winsor bounds), so a
    watchlist stock doesn't shift anyone else's score. `would_rank` = where it
    would slot into the semis ranking.
    """
    extra = [t for t in extra if t in px.columns]
    if not extra:
        return pd.DataFrame(), pd.DataFrame()
    p = _prices_at(px, asof, extra)
    rows = {t: fundamental_factors(all_series.get(t, {}), asof, p[t]) for t in extra}
    raw = pd.DataFrame(rows).T.join(price_factors(px[extra], asof), how="left")
    z = pd.DataFrame(index=raw.index)
    for f in FACTORS:
        u = ranked[f].astype(float)
        lo, hi = u.quantile(0.05), u.quantile(0.95)
        uc = u.clip(lo, hi)
        sd = uc.std()
        x = raw[f].astype(float).clip(lo, hi)
        z[f] = ((x - uc.mean()) / sd if sd and sd > 0 else x * 0) * FACTORS[f]["sign"]
    names = [f for f, c in FACTORS.items() if c["weight"] > 0]
    w = pd.Series({f: FACTORS[f]["weight"] for f in names})
    have = z[names].notna()
    raw["score"] = (z[names].fillna(0) * w).sum(axis=1) / (have * w).sum(axis=1)
    raw.loc[have.sum(axis=1) < MIN_FACTORS, "score"] = np.nan
    raw["n_factors"] = have.sum(axis=1)
    uni = ranked["score"].dropna()
    raw["would_rank"] = [int((uni > v).sum()) + 1 if pd.notna(v) else np.nan for v in raw["score"]]
    return raw, z
