"""
Exercise 06: max drawdown

Run `python practice/check.py 6` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def max_drawdown(prices):
    """Biggest peak-to-trough fall of a price Series, as a negative number.
    Example: 100 -> 150 -> 75 -> 120 has max drawdown -0.5 (150 down to 75).
    """
    # HINT: .cummax() gives the highest price so far at each point. prices / running_peak - 1 is the drawdown each day; take the .min().
    # YOUR CODE HERE
    raise NotImplementedError
