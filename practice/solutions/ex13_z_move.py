"""Solution: ex13_z_move"""
def z_move(prices, n=1):
    import numpy as np
    p = prices.dropna()
    r = p.pct_change()
    sigma = r.iloc[-253:-1].std()
    ret = p.iloc[-1] / p.iloc[-1 - n] - 1
    return float(ret / (sigma * np.sqrt(n)))
