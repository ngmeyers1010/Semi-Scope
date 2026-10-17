"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def check_max_drawdown(fn):
    import pandas as pd
    s = pd.Series([100, 150, 75, 120], dtype=float)
    assert abs(fn(s) - (-0.5)) < 1e-9, fn(s)
    flat = pd.Series([10, 11, 12], dtype=float)
    assert abs(fn(flat)) < 1e-9, fn(flat)
