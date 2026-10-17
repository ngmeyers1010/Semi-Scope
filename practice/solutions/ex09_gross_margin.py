"""SOLUTION. Try the exercise first! Peeking skips the part where you actually learn."""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def gross_margin(revenue, cogs):
    m = revenue.merge(cogs, on='end', suffixes=('_rev', '_cogs'))
    m['gross_margin'] = 1 - m['val_cogs'] / m['val_rev']
    return m[['end', 'gross_margin']].sort_values('end').reset_index(drop=True)
