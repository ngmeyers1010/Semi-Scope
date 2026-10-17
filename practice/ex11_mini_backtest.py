"""
Exercise 11: mini backtest

Run `python practice/check.py 11` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def mini_backtest(px, start, end, k=3):
    """A tiny backtest. On date `start`, pick the k tickers with the best 6-1 month momentum
    using ONLY prices up to `start` (no peeking!). Put equal money in each and hold until `end`.
    Return the portfolio's total return (e.g. 0.12 for +12%).
    """
    # HINT: past = px.loc[:start] cuts off the future. Momentum from past.iloc[-21] / past.iloc[-126] - 1, take .nlargest(k).index.
    #       Then each pick's return start->end with px.loc[start:end], and average them.
    # YOUR CODE HERE
    raise NotImplementedError
