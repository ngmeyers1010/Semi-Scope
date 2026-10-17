"""Solution: ex31_beta_and_a_bad_day"""
import numpy as np
import pandas as pd


def beta(stock_returns, market_returns) -> float:
    j = pd.concat([stock_returns, market_returns], axis=1, sort=True).dropna()
    v = j.iloc[:, 1].var()
    return float(j.iloc[:, 0].cov(j.iloc[:, 1]) / v) if v > 0 else float("nan")


def var95(returns, amount: float) -> float:
    r = pd.Series(returns, dtype=float).dropna()
    return float(-np.percentile(r, 5) * amount)
