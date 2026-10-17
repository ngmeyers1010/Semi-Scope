"""
Exercise 05: annual vol

Run `python practice/check.py 5` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def annual_vol(px, ticker, days=126):
    """Annualized volatility of `ticker` over the last `days` daily returns:
        standard deviation of daily returns x sqrt(252)
    (252 = trading days in a year).
    """
    # HINT: Daily returns: px[ticker].pct_change(). Keep the last `days` with .tail(days). .std() then multiply by 252 ** 0.5.
    # YOUR CODE HERE
    raise NotImplementedError
