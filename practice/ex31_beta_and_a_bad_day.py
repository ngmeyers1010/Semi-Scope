"""
Exercise 31: beta and a bad day (mirrors beta() and var_95() in risk.py, the Risk card)

1) beta(stock_returns, market_returns) -> float

   How much the stock tends to move when the market moves 1%:
       beta = covariance(stock, market) / variance(market)
   * the two Series are daily returns with DATES as the index. They may not cover the same
     days, and either can have missing values (NaN). Line them up by date first and keep only
     days where both have a number: pd.concat([s, m], axis=1).dropna()
   * use pandas' .cov() and .var(): both are SAMPLE statistics (divide by n - 1)
   * if the market's variance is 0, return float("nan")

2) var95(returns, amount) -> float, a POSITIVE dollar amount

   "On a bad day (1 in 20), how much could I lose?" Historical 95% value at risk:
   * drop missing values
   * the 5th percentile of the daily returns: np.percentile(r, 5) (a negative number, like -0.031)
   * flip the sign and multiply by `amount`: a 3.1% loss on $1,000 is 31.0

Run `python practice/check.py 31` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def beta(stock_returns, market_returns) -> float:
    # HINT: j = pd.concat([stock_returns, market_returns], axis=1).dropna()
    # YOUR CODE HERE
    raise NotImplementedError


def var95(returns, amount: float) -> float:
    # YOUR CODE HERE
    raise NotImplementedError
