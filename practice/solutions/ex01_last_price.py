"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def last_price(px, ticker):
    return float(px[ticker].dropna().iloc[-1])
