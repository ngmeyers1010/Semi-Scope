"""
Exercise 19: did the strategy beat SPY over every 1-year stretch? (mirrors steady.py)

Write two functions:

1. rolling_excess(strat, spy) -> pandas Series
   `strat` and `spy` are daily price Series with the same dates. For every day that has a
   full year (252 trading days) behind it, return:
       strategy's 1-year return  -  SPY's 1-year return
   where a 1-year return is  p / p.shift(252) - 1. Drop the first 252 days (they're NaN).

2. worst_window(excess) -> (end_date, value)
   The day where `excess` is lowest, and the value on that day.

Run `python practice/check.py 19` to check your answer.

TRAP: returns COMPOUND, they don't add up. Two days of +50% then -50%:
    added:      0.50 + (-0.50) = 0           ("flat")
    compounded: 1.50 * 0.50 - 1 = -0.25       (you lost a quarter)
So `daily_returns.rolling(252).sum()` is NOT a 1-year return. `p / p.shift(252) - 1`
(or `p.pct_change(252)`) is.
"""
import pandas as pd  # noqa: F401


def rolling_excess(strat: pd.Series, spy: pd.Series) -> pd.Series:
    # HINT: one_year = lambda p: p / p.shift(252) - 1
    # HINT: subtract SPY's from the strategy's, then .dropna()
    # YOUR CODE HERE
    raise NotImplementedError


def worst_window(excess: pd.Series):
    # HINT: excess.idxmin() gives the date of the smallest value; excess[that date] the value
    # YOUR CODE HERE
    raise NotImplementedError
