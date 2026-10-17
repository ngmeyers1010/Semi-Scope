"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def group_median(table):
    return table.groupby('group')['rev_growth'].median().sort_values(ascending=False)
