"""
Risk panel: how bumpy is the portfolio, and how much do the picks move together?

Five chip stocks are NOT five independent bets. When memory prices crash, MU,
WDC and the equipment makers often fall together. This module measures that.

All functions are pure: prices in, numbers out.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
STRESS_WINDOWS = {   # name -> (start, end); hypothetical: TODAY's picks held through PAST windows
    "2018 Q4 selloff": ("2018-10-01", "2018-12-24"),
    "2020 COVID crash": ("2020-02-19", "2020-03-23"),
    "2022 chip bear market": ("2022-01-03", "2022-10-14"),
}


def _returns(px: pd.DataFrame, tickers: list[str], days: int | None) -> pd.DataFrame:
    r = px[[t for t in tickers if t in px]].pct_change().iloc[1:]
    return r.tail(days) if days else r


def corr_matrix(px: pd.DataFrame, tickers: list[str], days: int = 126) -> pd.DataFrame:
    """Pairwise correlation of daily returns over the last `days` trading days."""
    return _returns(px, tickers, days).corr()


def _port(r: pd.DataFrame, w: pd.Series) -> pd.Series:
    """Daily portfolio return with fixed weights (missing returns count as 0)."""
    w = w.reindex(r.columns).fillna(0)
    return (r.fillna(0) * w).sum(axis=1) / w.sum()


def effective_bets(r: pd.DataFrame, w: pd.Series) -> float:
    """Diversification ratio squared: (Σ wᵢσᵢ / σ_portfolio)².
    N identical stocks → 1 bet. N unrelated stocks with equal risk → N bets."""
    w = w.reindex(r.columns).fillna(0) / w.sum()
    cov = r.cov().values
    sig = np.sqrt(np.diag(cov))
    port = float(np.sqrt(w.values @ cov @ w.values))
    return float((w.values @ sig / port) ** 2) if port > 0 else float("nan")


def beta(port_r: pd.Series, bench_r: pd.Series) -> float:
    """How much the portfolio moves per 1% move in the benchmark."""
    j = pd.concat([port_r, bench_r], axis=1, sort=True).dropna()
    v = j.iloc[:, 1].var()
    return float(j.iloc[:, 0].cov(j.iloc[:, 1]) / v) if v > 0 else float("nan")


def var_95(port_r: pd.Series) -> float:
    """95% one-day historical VaR as a positive loss fraction: on 1 day in 20,
    expect to lose at least this much."""
    return float(-np.percentile(port_r.dropna(), 5))


def portfolio_risk(px: pd.DataFrame, weights: dict, bench: pd.DataFrame, amount: float = 1000.0) -> dict:
    """Risk numbers for a set of holdings held at `weights` (any scale)."""
    w = pd.Series(weights, dtype=float)
    w = w[w > 0]
    tick = [t for t in w.index if t in px]
    if not tick:
        return {}
    r1 = _returns(px, tick, TRADING_DAYS)
    r2 = _returns(px, tick, 2 * TRADING_DAYS)
    r5 = _returns(px, tick, 5 * TRADING_DAYS)
    p1, p2, p5 = _port(r1, w), _port(r2, w), _port(r5, w)
    month = (1 + p5).rolling(21).apply(np.prod, raw=True) - 1
    out = {
        "tickers": tick,
        "weights": {t: float(w[t] / w[tick].sum()) for t in tick},
        "volatility": float(p1.std() * np.sqrt(TRADING_DAYS)),
        "var95": var_95(p2),
        "var95_dollars": var_95(p2) * amount, "amount": amount,
        "worst_month": float(month.min()) if month.notna().any() else None,
        "worst_month_end": month.idxmin().strftime("%Y-%m-%d") if month.notna().any() else None,
        "effective_bets": effective_bets(r1, w),
        "n": len(tick),
    }
    for b in ("SPY", "SOXX"):
        if b in bench:
            out[f"beta_{b.lower()}"] = beta(p1, bench[b].pct_change().reindex(p1.index))
    c = corr_matrix(px, tick)
    out["corr"] = {"tickers": tick, "matrix": [[float(c.loc[a, b]) for b in tick] for a in tick]}
    off = c.values[~np.eye(len(tick), dtype=bool)]
    out["avg_corr"] = float(off.mean()) if off.size else None
    return out


def stress_tests(px: pd.DataFrame, tickers: list[str], bench: pd.DataFrame,
                 windows: dict = STRESS_WINDOWS) -> list[dict]:
    """Equal-weight return of `tickers` through each past window (hypothetical).
    Windows outside the price history, or with no picks trading, are skipped."""
    out = []
    for name, (a, b) in windows.items():
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        if px.empty or a < px.index[0] or b > px.index[-1]:
            continue
        s, e = px.loc[:a].iloc[-1], px.loc[:b].iloc[-1]
        have = [t for t in tickers if t in px and pd.notna(s.get(t)) and pd.notna(e.get(t)) and s[t] > 0]
        if not have:
            continue
        row = {"name": name, "start": a.strftime("%Y-%m-%d"), "end": b.strftime("%Y-%m-%d"),
               "picks": float(np.mean([e[t] / s[t] - 1 for t in have])), "n": len(have), "of": len(tickers)}
        for k in ("SPY", "SOXX"):
            if k in bench:
                bs, be = bench[k].loc[:a].dropna(), bench[k].loc[:b].dropna()
                row[k.lower()] = float(be.iloc[-1] / bs.iloc[-1] - 1) if len(bs) and len(be) else None
        out.append(row)
    return out


def build(px: pd.DataFrame, bench: pd.DataFrame, picks: list[str], real_positions: list[dict] | None,
          amount: float = 1000.0) -> dict:
    """data['risk']: model picks (equal weight) and, if logged, your real holdings (by value)."""
    out = {"model": portfolio_risk(px, {t: 1.0 for t in picks}, bench, amount),
           "stress": stress_tests(px, picks, bench), "picks": picks}
    held = {p["ticker"]: p["value"] for p in (real_positions or []) if p.get("value")}
    if held:
        out["mine"] = portfolio_risk(px, held, bench, amount)
        out["mine_stress"] = stress_tests(px, list(held), bench)
    return out
