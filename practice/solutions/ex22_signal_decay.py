"""Solution: ex22_signal_decay"""
import math

import pandas as pd


def excess_at(px: pd.DataFrame, date, picks: list, universe: list, months: int):
    start = pd.Timestamp(date)
    i = px.index.searchsorted(start + pd.DateOffset(months=months))   # first day >= target
    if i >= len(px.index):
        return None                                                    # hasn't happened yet
    end = px.index[i]

    def avg(names):
        return (px.loc[end, names] / px.loc[start, names] - 1).dropna().mean()

    return float(avg(list(picks)) - avg(list(universe)))


def overlap_t(values: list, months: int) -> float:
    s = pd.Series(values, dtype=float)
    t = s.mean() / (s.std() / math.sqrt(len(s)))
    return float(t / math.sqrt(max(1.0, months / 3)))
