"""Solution: ex27_catch_a_bad_number"""
import math
import statistics


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def flag_jumps(values, jump: float = 8.0, lookback: int = 4) -> list:
    values = list(values)
    dropped = []
    for i, x in enumerate(values):
        if not _ok(x) or x <= 0:
            continue
        before = [values[j] for j in range(max(0, i - lookback), i)
                  if j not in dropped and _ok(values[j]) and values[j] > 0]
        if len(before) < 2:
            continue
        r = x / statistics.median(before)
        if r >= jump or r <= 1 / jump:
            dropped.append(i)
    return dropped


def nonpositive(values) -> list:
    return [i for i, x in enumerate(values) if _ok(x) and x <= 0]
