"""
Exercise 32: Sharpe and effective bets (mirrors backtest.stats() and risk.effective_bets())

1) sharpe(curve) -> float

   `curve` is a daily equity curve (a Series of values, dates as the index), like the Backtest
   tab's strategy line. SemiScope's Sharpe has no risk-free rate:
   * daily returns: curve.pct_change().dropna()
   * yearly return = average daily return * 252
   * yearly volatility = std of daily returns * sqrt(252)   (pandas .std(), the sample std)
   * Sharpe = yearly return / yearly volatility   (if the volatility is 0, return float("nan"))

2) effective_bets(r, w) -> float

   How many independent bets a portfolio acts like. `r` is a DataFrame of daily returns (one
   column per stock), `w` a dict of weights {ticker: weight} for those columns (any scale).
   * cov = r.cov()   (sample covariance matrix); sigma = each stock's std = sqrt of its diagonal
   * portfolio std = sqrt(w @ cov @ w) with the weights in the same column order (and normalized)
   * effective bets = (sum(w * sigma) / portfolio std) ** 2
   5 stocks that always move together -> about 1. 5 unrelated stocks with equal risk -> 5.

Run `python practice/check.py 32` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def sharpe(curve) -> float:
    # HINT: r = curve.pct_change().dropna()
    # YOUR CODE HERE
    raise NotImplementedError


def effective_bets(r, w: dict) -> float:
    # HINT: wv = pd.Series(w, dtype=float).reindex(r.columns).fillna(0); wv = wv / wv.sum()
    # YOUR CODE HERE
    raise NotImplementedError
