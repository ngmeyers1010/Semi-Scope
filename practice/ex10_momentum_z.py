"""
Exercise 10: momentum z

Run `python practice/check.py 10` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def momentum_z(px):
    """Your first factor! For every ticker compute 6-1 month momentum:
        price 21 trading days ago / price 126 trading days ago - 1
    (skipping the latest month avoids short-term reversals). Then z-score it:
        z = (x - mean) / standard deviation
    Return the z-scores as a Series sorted highest first. Drop tickers with missing data.
    """
    # HINT: m = px.iloc[-21] / px.iloc[-126] - 1, .dropna(), then (m - m.mean()) / m.std(), then .sort_values(ascending=False).
    # YOUR CODE HERE
    raise NotImplementedError
