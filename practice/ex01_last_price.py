"""
Exercise 01: last price

Run `python practice/check.py 1` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def last_price(px, ticker):
    """Return the most recent price of `ticker` as a float.
    
    px is a DataFrame: one row per trading day (the index is dates), one column per ticker.
    Some early rows are NaN (the stock wasn't trading yet).
    """
    # HINT: px[ticker] gives one column (a Series). .dropna() removes missing values. .iloc[-1] is the last item.
    # YOUR CODE HERE
    raise NotImplementedError
