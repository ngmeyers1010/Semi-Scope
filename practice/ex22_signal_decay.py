"""
Exercise 22: signal decay by hand (mirrors decay.py)

The dashboard's "How long does a pick's edge last?" card asks: N months after a rebalance,
how far ahead of the average stock are the picks? Write two functions.

1) excess_at(px, date, picks, universe, months) -> float or None

   * start = `date` (a trading day in px.index)
   * end   = the FIRST trading day ON OR AFTER date + `months` calendar months.
             date + months can land on a weekend or holiday, so don't look it up directly:
             target = pd.Timestamp(date) + pd.DateOffset(months=months)
             i = px.index.searchsorted(target)      # position of the first day >= target
   * if the data doesn't reach that far yet (i == len(px.index)), return None
   * picks return    = AVERAGE of (price at end / price at start - 1) over `picks`
   * universe return = AVERAGE of the same over `universe`, skipping stocks with a missing
                       (NaN) price at start or end
   * return picks return - universe return

2) overlap_t(values, months) -> float

   values = excess returns at one horizon, one per rebalance (every 3 months).
   t = mean / (sample std / sqrt(n)), then divide by sqrt(months / 3) when months > 3,
   because 6-month windows that start every 3 months overlap and aren't independent.
   Use the sample std (ddof=1, pandas' default).

Run `python practice/check.py 22` to check your answer.
"""
import pandas as pd


def excess_at(px: pd.DataFrame, date, picks: list, universe: list, months: int):
    # HINT: rets = px.loc[end, names] / px.loc[start, names] - 1, then .dropna().mean()
    # YOUR CODE HERE
    raise NotImplementedError


def overlap_t(values: list, months: int) -> float:
    # HINT: s = pd.Series(values); s.mean(), s.std(), len(s)
    # YOUR CODE HERE
    raise NotImplementedError
