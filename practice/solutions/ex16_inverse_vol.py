"""Solution: ex16_inverse_vol"""
def inverse_vol_weights(px, tickers, lookback=63):
    import numpy as np
    hist = px[tickers].tail(lookback + 1)
    vol = hist.pct_change().std() * np.sqrt(252)
    inv = 1 / vol
    return inv / inv.sum()
