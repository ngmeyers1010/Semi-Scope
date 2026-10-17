"""Solution: ex25_drawdown_episodes"""
import pandas as pd


def underwater(curve: pd.Series) -> pd.Series:
    return curve / curve.cummax() - 1


def episodes(curve: pd.Series, min_depth: float = 0.02) -> list:
    uw = underwater(curve.dropna())
    out, start = [], None

    def close(i_peak, i_end):
        window = uw.iloc[i_peak:i_end]
        out.append({"peak": uw.index[i_peak], "trough": window.idxmin(),
                    "recovery": uw.index[i_end] if i_end < len(uw) else None,
                    "depth": float(window.min())})

    for i, (d, v) in enumerate(uw.items()):
        if v < 0 and start is None:
            start = i - 1                      # the peak is the day before it went under
        elif v >= 0 and start is not None:
            close(start, i)
            start = None
    if start is not None:                      # still underwater when the data ends
        close(start, len(uw))
    return [e for e in out if -e["depth"] >= min_depth]
