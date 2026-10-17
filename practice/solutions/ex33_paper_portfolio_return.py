"""Solution: ex33_paper_portfolio_return"""
import numpy as np  # noqa: F401
import pandas as pd


def paper_return(entries: list, px: pd.DataFrame, cost_bps: float = 10) -> float:
    daily = px.pct_change()
    value, prev_w = 1.0, pd.Series(dtype=float)
    for i, e in enumerate(entries):
        d = pd.Timestamp(e["date"])
        end = pd.Timestamp(entries[i + 1]["date"]) if i + 1 < len(entries) else px.index[-1]
        w = pd.Series(1 / len(e["picks"]), index=e["picks"])
        value *= 1 - w.subtract(prev_w, fill_value=0).abs().sum() * cost_bps / 1e4
        period = daily.loc[(daily.index > d) & (daily.index <= end)].reindex(columns=e["picks"]).fillna(0)
        if len(period):
            growth = (1 + period).cumprod()
            drifted = growth.iloc[-1] * w
            value = value * drifted.sum()
            prev_w = drifted / drifted.sum()
        else:
            prev_w = w
    return float(value - 1)
