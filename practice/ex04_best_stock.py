"""
Exercise 04: best stock

Run `python practice/check.py 4` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def best_stock(px, days=252):
    """Which ticker had the highest return over the last `days` trading days?
    Return its name as a string. Ignore tickers with missing data at either end.
    """
    # HINT: px.iloc[-1] / px.iloc[-days] - 1 gives one return per ticker. .dropna() then .idxmax() returns the label of the biggest.
    # YOUR CODE HERE
    raise NotImplementedError
