"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def momentum_z(px):
    m = (px.iloc[-21] / px.iloc[-126] - 1).dropna()
    return ((m - m.mean()) / m.std()).sort_values(ascending=False)
