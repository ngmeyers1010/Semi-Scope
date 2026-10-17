"""
Exercise 03: total return

Run `python practice/check.py 3` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def total_return(px, ticker, start, end):
    """Total return of `ticker` from the first trading day ON OR AFTER `start`
    to the last trading day ON OR BEFORE `end`, e.g. 0.25 for +25%.
    start/end are strings like '2020-01-01'.
    """
    # HINT: px.loc[start:end, ticker] slices by date (both ends included). Then last / first - 1.
    # YOUR CODE HERE
    raise NotImplementedError
