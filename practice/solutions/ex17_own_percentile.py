"""Solution: ex17_own_percentile"""
import pandas as pd


def own_percentile(history: pd.Series, today: float) -> float:
    h = history.dropna()
    below = (h < today).sum()
    equal = (h == today).sum()
    return float(100.0 * (below + 0.5 * equal) / len(h))


def valuation_label(pct) -> str:
    if pct is None:
        return "not enough history"
    if pct < 10:
        return "near its cheapest"
    if pct < 25:
        return "cheaper than usual"
    if pct <= 75:
        return "about usual"
    if pct <= 90:
        return "pricier than usual"
    return "near its priciest"
