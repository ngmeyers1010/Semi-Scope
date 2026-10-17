"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def total_return(px, ticker, start, end):
    s = px.loc[start:end, ticker].dropna()
    return float(s.iloc[-1] / s.iloc[0] - 1)
