"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def mini_backtest(px, start, end, k=3):
    past = px.loc[:start]
    mom = (past.iloc[-21] / past.iloc[-126] - 1).dropna()
    picks = mom.nlargest(k).index
    window = px.loc[start:end, picks]
    return float((window.iloc[-1] / window.iloc[0] - 1).mean())
