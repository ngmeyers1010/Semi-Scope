"""Solution: ex32_sharpe_and_effective_bets"""
import numpy as np
import pandas as pd


def sharpe(curve) -> float:
    r = curve.pct_change().dropna()
    vol = r.std() * np.sqrt(252)
    return float((r.mean() * 252) / vol) if vol else float("nan")


def effective_bets(r, w: dict) -> float:
    wv = pd.Series(w, dtype=float).reindex(r.columns).fillna(0)
    wv = wv / wv.sum()
    cov = r.cov().values
    sigma = np.sqrt(np.diag(cov))
    port = float(np.sqrt(wv.values @ cov @ wv.values))
    return float((wv.values @ sigma / port) ** 2) if port > 0 else float("nan")
