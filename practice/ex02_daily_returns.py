"""
Exercise 02: daily returns

Run `python practice/check.py 2` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def daily_returns(px):
    """Return a DataFrame of daily returns for every ticker:
        return today = price today / price yesterday - 1
    Drop the very first row (it has no 'yesterday').
    """
    # HINT: pandas has a one-word method for this: .pct_change(). Then drop row 0 with .iloc[1:].
    # YOUR CODE HERE
    raise NotImplementedError
