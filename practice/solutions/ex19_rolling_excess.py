"""Solution: ex19_rolling_excess"""
import pandas as pd


def rolling_excess(strat: pd.Series, spy: pd.Series) -> pd.Series:
    one_year = lambda p: p / p.shift(252) - 1
    return (one_year(strat) - one_year(spy)).dropna()


def worst_window(excess: pd.Series):
    d = excess.idxmin()
    return d, float(excess[d])
