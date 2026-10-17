"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def annual_vol(px, ticker, days=126):
    r = px[ticker].pct_change().dropna().tail(days)
    return float(r.std() * 252 ** 0.5)
