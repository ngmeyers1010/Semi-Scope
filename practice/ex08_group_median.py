"""
Exercise 08: group median

Run `python practice/check.py 8` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def group_median(table):
    """`table` has columns 'ticker', 'group' (e.g. 'Memory/Storage') and 'rev_growth'.
    Return a Series: the median rev_growth of each group, sorted from highest to lowest.
    This is exactly what cycle.py does to gauge the chip cycle.
    """
    # HINT: table.groupby('group')['rev_growth'].median() then .sort_values(ascending=False).
    # YOUR CODE HERE
    raise NotImplementedError
