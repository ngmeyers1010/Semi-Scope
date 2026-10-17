"""
Exercise 12: check max drawdown

Run `python practice/check.py 12` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def check_max_drawdown(fn):
    """Now YOU write the test. `fn` is someone's max_drawdown function (like exercise 6).
    Use `assert` statements so that check_max_drawdown(fn) raises AssertionError if fn is wrong
    and does nothing if fn is right. The checker will hand you one correct and two BUGGY versions;
    your test must catch both bugs.
    Tip: make a tiny pd.Series where you know the answer by hand.
    """
    # HINT: Try a series like 100, 150, 75, 120: answer -0.5. A buggy version might measure from the FIRST price (-0.25)
    #       or return a positive number. Use abs(fn(s) - expected) < 1e-9 rather than == for floats.
    # YOUR CODE HERE
    raise NotImplementedError
