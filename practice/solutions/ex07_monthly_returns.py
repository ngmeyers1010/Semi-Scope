"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def monthly_returns(px, ticker):
    s = px[ticker].dropna()
    return s.groupby(s.index.to_period('M')).last().pct_change().dropna()
