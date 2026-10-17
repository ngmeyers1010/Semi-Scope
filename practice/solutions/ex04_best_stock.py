"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def best_stock(px, days=252):
    r = (px.iloc[-1] / px.iloc[-days] - 1).dropna()
    return str(r.idxmax())
