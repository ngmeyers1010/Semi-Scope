"""
Exercise 13: how unusual was that move? (mirrors moves.py)

Run `python practice/check.py 13` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def z_move(prices: pd.Series, n: int = 1) -> float:
    """Return the "z-move" of the last n-day move in `prices`:

        ret   = last price / price n days earlier - 1
        sigma = standard deviation of the daily returns over the past year (the 252 daily
                returns BEFORE the last one, so today's move doesn't inflate its own yardstick)
        z     = ret / (sigma * sqrt(n))

    Drop missing prices first. Example: a 6% day on a stock whose normal day is 2% -> z = 3.
    """
    # HINT: p = prices.dropna(); r = p.pct_change()
    # HINT: the year before today is r.iloc[-253:-1]  (252 values, today excluded)
    # HINT: np.sqrt(n). For n=5 compare p.iloc[-1] with p.iloc[-6].
    # YOUR CODE HERE
    raise NotImplementedError
