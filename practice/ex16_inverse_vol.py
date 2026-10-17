"""
Exercise 16: calmer stocks get more money (mirrors sizing.py)

Run `python practice/check.py 16` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def inverse_vol_weights(px: pd.DataFrame, tickers: list, lookback: int = 63) -> pd.Series:
    """Weights for `tickers` (they must add up to 1) that are proportional to 1 / volatility,
    where volatility = std of daily returns over the last `lookback` returns, times sqrt(252).
    Use the last lookback+1 rows of prices (lookback returns). Index the result by `tickers`
    in the order given.
    """
    # HINT: hist = px[tickers].tail(lookback + 1); vol = hist.pct_change().std() * np.sqrt(252)
    # HINT: inv = 1 / vol; return inv / inv.sum()
    # YOUR CODE HERE
    raise NotImplementedError
