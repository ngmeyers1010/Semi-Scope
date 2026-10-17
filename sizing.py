"""
Position sizing: how much of the money goes into each pick.

"Equal" puts the same dollars in every pick. "Inverse-volatility" (a.k.a. calmer-
weighted) puts MORE money into calmer stocks and LESS into jumpy ones, so each pick
contributes a similar amount of day-to-day swing. Weight_i = (1/vol_i) / sum(1/vol).

No look-ahead: volatility is measured from the LOOKBACK trading days up to and
including the rebalance date, never after it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LOOKBACK = 63   # ~3 months of trading days


def trailing_vol(px: pd.DataFrame, tickers: list[str], d, lookback: int = LOOKBACK) -> pd.Series:
    """Annualized volatility of each ticker over the `lookback` days ending at `d`."""
    hist = px.loc[:pd.Timestamp(d), [t for t in tickers if t in px]].tail(lookback + 1)
    return hist.pct_change().std() * np.sqrt(252)


def inverse_vol_from(vols: dict | pd.Series) -> pd.Series:
    """Weights from volatilities. Missing or zero vols get the average weight."""
    v = pd.Series(vols, dtype=float)
    inv = 1 / v.where(v > 0)
    if inv.notna().sum() == 0:
        return pd.Series(1 / len(v), index=v.index)
    inv = inv.fillna(inv.mean())
    return inv / inv.sum()


def weights(px: pd.DataFrame, picks: list[str], d, method: str = "equal",
            lookback: int = LOOKBACK) -> pd.Series:
    """Portfolio weights for `picks` on date `d` (they sum to 1)."""
    if not picks:
        return pd.Series(dtype=float)
    if method == "equal":
        return pd.Series(1 / len(picks), index=picks)
    if method == "inverse_vol":
        vol = trailing_vol(px, picks, d, lookback).reindex(picks)
        return inverse_vol_from(vol)
    raise ValueError(f"unknown weighting {method!r}")
