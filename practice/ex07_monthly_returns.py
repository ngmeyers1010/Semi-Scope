"""
Exercise 07: monthly returns

Run `python practice/check.py 7` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def monthly_returns(px, ticker):
    """Monthly returns of `ticker`: last price of each month vs the last price of the previous month.
    Return a Series (one value per month, first month dropped since it has no previous month).
    """
    # HINT: Group by month: s.groupby(s.index.to_period('M')).last() gives month-end prices. Then .pct_change().dropna().
    # YOUR CODE HERE
    raise NotImplementedError
