"""
Exercise 33: the paper portfolio's return (mirrors paper.performance(), the "Paper return" tile)

`entries` is the paper log, oldest first. Each entry has {"date": "2026-10-13", "picks": ["MU", ...], ...}
(the real log also keeps entry_prices and scores; you won't need them).
`px` is a DataFrame of daily closing prices (dates as the index, one column per ticker).
Each entry says: "from the close on this date, hold these picks in equal weight until the next
entry" (the last entry is held until the last date in px).

paper_return(entries, px, cost_bps=10) -> total return as a fraction (0.031 = +3.1%)

   value = 1.0, previous weights = none
   for each entry (and the date of the next one, or px's last date):
     * target weights: 1 / len(picks) each
     * trading cost: value *= 1 - (sum of |target - previous| over all tickers) * cost_bps / 10000
       (the first entry buys everything: that sum is 1.0)
     * daily returns = px.pct_change(), for days AFTER the entry date up to and including the end.
       The picks were chosen with the entry day's close, so that day's own move doesn't count.
     * a pick with no price on a day (or missing from px entirely) counts as 0% that day
     * grow each pick: growth = (1 + returns).cumprod(); the portfolio is value * sum(growth * weight)
     * at the end of the period: value = that last number, and the previous weights are the
       DRIFTED ones: growth.iloc[-1] * weight, divided by their sum
   return value - 1

Run `python practice/check.py 33` to check your answer.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def paper_return(entries: list, px: pd.DataFrame, cost_bps: float = 10) -> float:
    # HINT: daily = px.pct_change(); prev_w = pd.Series(dtype=float)
    # HINT: period = daily.loc[(daily.index > d) & (daily.index <= end)].reindex(columns=picks).fillna(0)
    # YOUR CODE HERE
    raise NotImplementedError
