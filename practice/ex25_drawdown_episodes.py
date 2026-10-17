"""
Exercise 25: drawdown episodes (mirrors drawdowns.py)

"Max drawdown −49%" says how deep. This exercise finds every drop and how long it lasted.
Write two functions.

1) underwater(curve) -> Series
   How far below its previous high the curve is each day: curve / curve.cummax() - 1
   (0 on a day that's a new high, negative otherwise)

2) episodes(curve, min_depth=0.02) -> list of dicts, oldest first:
     {"peak": Timestamp, "trough": Timestamp, "recovery": Timestamp or None, "depth": float}

   Walk the underwater series day by day:
   * an episode STARTS when the value goes below 0. Its peak is the DAY BEFORE (the last high)
   * it ENDS on the first day back at 0 (that day is the recovery)
   * if the data ends while still below 0, the episode is still open: recovery = None
   * trough = the day with the lowest underwater value between peak and recovery
     (window.idxmin()); depth = that lowest value (negative, e.g. -0.23)
   * keep only episodes at least min_depth deep (-depth >= min_depth): ignore small wiggles

   Tip: enumerate(uw.items()) gives you (i, (date, value)); remember the START POSITION i,
   then slice uw.iloc[start:end] for the window.

Run `python practice/check.py 25` to check your answer.
"""
import pandas as pd


def underwater(curve: pd.Series) -> pd.Series:
    # YOUR CODE HERE
    raise NotImplementedError


def episodes(curve: pd.Series, min_depth: float = 0.02) -> list:
    # HINT: uw = underwater(curve.dropna()); start = None
    # HINT: for i, (d, v) in enumerate(uw.items()): ...
    # YOUR CODE HERE
    raise NotImplementedError
