"""
Exercise 24: up/down capture (mirrors capture.py) — boolean masks

How much of the benchmark's good months and bad months does a strategy catch?
Write up_down_capture(strat, bench) -> (up, down), where both inputs are DAILY price Series.

  1. monthly returns: s.resample("ME").last().pct_change().dropna()   (for both series)
  2. line them up: pd.concat([s_m.rename("s"), b_m.rename("b")], axis=1, sort=True).dropna()
  3. up months   = rows where b > 0      (a boolean mask: df[df["b"] > 0])
     down months = rows where b < 0      (flat months, b == 0, are in NEITHER)
  4. up   = (average strategy return in up months)   / (average benchmark return in up months)
     down = (average strategy return in down months) / (average benchmark return in down months)
  5. return (up, down) as floats

Up 1.2 and down 0.8 means: 120% of the gains, only 80% of the losses.

Run `python practice/check.py 24` to check your answer.
"""
import pandas as pd


def up_down_capture(strat: pd.Series, bench: pd.Series) -> tuple:
    # HINT: up = both[both["b"] > 0]; then up["s"].mean() / up["b"].mean()
    # YOUR CODE HERE
    raise NotImplementedError
