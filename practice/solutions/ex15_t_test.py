"""Solution: ex15_t_test"""
def edge_stats(excess):
    import math
    import pandas as pd
    s = pd.Series(excess, dtype=float)
    mean, sd, n = s.mean(), s.std(), len(s)
    t = mean / (sd / math.sqrt(n))
    need = math.ceil((2 * sd / mean) ** 2) if mean > 0 else float("nan")
    return pd.Series({"mean": mean, "sd": sd, "t": t, "quarters_needed": need})
