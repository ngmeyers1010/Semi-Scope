"""
Exercise 14: first in, first out (mirrors mytrades.fifo_sell)

Run `python practice/check.py 14` to check your answer.
"""
import pandas as pd  # noqa: F401


def fifo_gains(lots: list, shares: float, price: float, sell_date: str) -> pd.Series:
    """`lots` is a list of (buy_date, shares, buy_price), oldest first, e.g.
        [("2024-01-02", 10, 50.0), ("2025-03-01", 5, 80.0)]
    You sell `shares` at `price` on `sell_date`. Take shares from the OLDEST lot first.
    A piece is long-term if it was held MORE than 365 days ((sell - buy).days > 365).

    Return pd.Series({"short": short-term gain, "long": long-term gain}) in dollars.
    (Simplified: the real code in mytrades.py also handles leap years exactly.)
    """
    # HINT: loop over lots; take = min(lot_shares, shares_left); gain = take * (price - buy_price)
    # HINT: pd.Timestamp(sell_date) - pd.Timestamp(buy_date) gives a Timedelta with .days
    # HINT: stop when nothing is left to sell.
    # YOUR CODE HERE
    raise NotImplementedError
