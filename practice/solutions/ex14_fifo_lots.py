"""Solution: ex14_fifo_lots"""
def fifo_gains(lots, shares, price, sell_date):
    import pandas as pd
    left, short, long_ = shares, 0.0, 0.0
    for buy_date, n, buy_price in lots:
        if left <= 0:
            break
        take = min(n, left)
        gain = take * (price - buy_price)
        if (pd.Timestamp(sell_date) - pd.Timestamp(buy_date)).days > 365:
            long_ += gain
        else:
            short += gain
        left -= take
    return pd.Series({"short": short, "long": long_})
