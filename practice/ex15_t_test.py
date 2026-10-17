"""
Exercise 15: is the edge real? (mirrors confidence.py)

Run `python practice/check.py 15` to check your answer.
"""
import math  # noqa: F401

import pandas as pd  # noqa: F401


def edge_stats(excess: list) -> pd.Series:
    """`excess` = quarterly returns of a strategy MINUS the S&P 500's, e.g. [0.02, -0.01, 0.03].
    Return pd.Series({"mean": ..., "sd": ..., "t": ..., "quarters_needed": ...}) where
        sd               = sample standard deviation (divide by n-1)
        t                = mean / (sd / sqrt(n))
        quarters_needed  = smallest whole n with t >= 2 at this mean and sd:  ceil((2*sd/mean)**2)
                           (NaN if the mean is not positive: more data won't help)
    """
    # HINT: pd.Series(excess).std() already divides by n-1.
    # HINT: math.ceil, math.sqrt, float("nan")
    # YOUR CODE HERE
    raise NotImplementedError
