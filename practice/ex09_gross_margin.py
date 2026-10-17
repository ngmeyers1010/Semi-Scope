"""
Exercise 09: gross margin

Run `python practice/check.py 9` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def gross_margin(revenue, cogs):
    """revenue and cogs are DataFrames with columns 'end' (quarter-end date) and 'val'.
    Return a DataFrame with columns ['end', 'gross_margin'] where gross_margin = 1 - cogs/revenue,
    only for quarters present in BOTH tables, sorted by 'end'.
    """
    # HINT: revenue.merge(cogs, on='end', suffixes=('_rev', '_cogs')) lines up matching quarters, like a VLOOKUP.
    # YOUR CODE HERE
    raise NotImplementedError
