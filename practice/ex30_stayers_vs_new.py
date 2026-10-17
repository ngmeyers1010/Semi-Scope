"""
Exercise 30: stayers vs new picks (mirrors streak_edge.py, the Research tab's
"Does a top-5 streak mean anything?" card)

`quarters` is the backtest's list of rebalances, oldest first. Each one looks like
    {"date": "2012-06-01", "end": "2012-09-04", "picks": ["AVGO", "MU", ...],
     "pick_returns": {"AVGO": 0.065, "MU": -0.06, ...}, "universe": 0.05}
"universe" is the average stock's return that quarter. A pick's EXCESS = its return - universe.

1) classify(quarters) -> list of {"date": ..., "stay": [excess, ...], "new": [excess, ...]}

   * skip the FIRST quarter: there's no quarter before it, so you can't tell stayers from new
   * for each later quarter q (with the one before it, prev):
       a pick is a STAYER if it is in prev["picks"] AND prev["end"] == q["date"]
       (the previous holding period ran right up to this rebalance, no gap); otherwise NEW
   * skip a pick whose return is None; keep the picks' order within each list
   * skip a quarter with no picks or with universe None

2) gap_t(rows) -> t-stat (float) or None

   * for each row with at least one stayer AND one new pick:
         gap = mean(stay) - mean(new)
   * t = mean(gaps) / (sd(gaps) / sqrt(number of gaps)), with the SAMPLE sd (divide by n - 1)
   * None if fewer than 2 gaps, or if every gap is the same (sd is 0)

   One gap per quarter, not one t-test on all picks: five picks from the same quarter ride
   the same market, so they aren't five independent tries.

Run `python practice/check.py 30` to check your answer.
"""
import math


def classify(quarters) -> list:
    # HINT: for prev, q in zip(quarters, quarters[1:]):
    # YOUR CODE HERE
    raise NotImplementedError


def gap_t(rows):
    # HINT: statistics.stdev(xs) is the sample sd (n - 1)
    # YOUR CODE HERE
    raise NotImplementedError
