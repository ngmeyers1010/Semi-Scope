"""
Exercise 17: is it cheap compared with ITSELF? (mirrors valuation.py)

Semis are cyclical, so "MU trades at 2x sales" means little on its own. Comparing it with
MU's own history means more: "2x is cheaper than 90% of the last 5 years".

Write two functions:

1. own_percentile(history, today) -> float between 0 and 100
   `history` is a pandas Series of past weekly price-to-sales values. It may contain NaN
   (weeks with no data): ignore those. Return the share of history BELOW today, times 100,
   where weeks EQUAL to today count half.
       history [2, 3, 3, 3, 5], today 3  ->  (1 below + 0.5 * 3 equal) / 5 * 100 = 50.0

2. valuation_label(pct) -> str, using exactly these rules (None means "not enough history"):
       pct < 10          "near its cheapest"
       10 <= pct < 25    "cheaper than usual"
       25 <= pct <= 75   "about usual"
       75 <  pct <= 90   "pricier than usual"
       pct > 90          "near its priciest"

Run `python practice/check.py 17` to check your answer.

TRAP worth knowing: Python's round(12.5) is 12 ("banker's rounding": halves go to the even
number), but JavaScript's Math.round(12.5) is 13. SemiScope shows the same number in Python
and on the website, so valuation.ordinal() uses floor(x + 0.5) instead of round().
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def own_percentile(history: pd.Series, today: float) -> float:
    # HINT: h = history.dropna()
    # HINT: (h < today) is a True/False Series; .sum() counts the Trues
    # HINT: why ties count half: if every week equals today, "below" is 0% and "below or
    #       equal" is 100%. Neither is fair; half-way (50) says "right in the middle".
    # YOUR CODE HERE
    raise NotImplementedError


def valuation_label(pct) -> str:
    # HINT: check None first, then go from low to high with if / elif.
    # HINT: watch the edges: 25 and 75 are "about usual", 90 is "pricier than usual".
    # YOUR CODE HERE
    raise NotImplementedError
