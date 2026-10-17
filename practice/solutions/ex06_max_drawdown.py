"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def max_drawdown(prices):
    return float((prices / prices.cummax() - 1).min())
