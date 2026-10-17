"""Solution: ex24_up_down_capture"""
import pandas as pd


def up_down_capture(strat: pd.Series, bench: pd.Series) -> tuple:
    def monthly(p):
        return p.resample("ME").last().pct_change().dropna()

    both = pd.concat([monthly(strat).rename("s"), monthly(bench).rename("b")], axis=1, sort=True).dropna()
    up, down = both[both["b"] > 0], both[both["b"] < 0]
    return float(up["s"].mean() / up["b"].mean()), float(down["s"].mean() / down["b"].mean())
