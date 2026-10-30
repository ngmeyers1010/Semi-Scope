"""
My research: PACS Group (NYSE: PACS), written by me.

Run from the semiscope folder:   python my_research/pacs_stats.py

Fill in each TODO. Stuck? Look the command up in the "Python Command Dictionary" doc:
each TODO says which section to check.
"""
import numpy as np
import pandas as pd
import yfinance as yf

TICKER = "PACS"
COMPARE = "SPY"      # the S&P 500 fund, so I can see if PACS beat the market

# 1. Download ~2 years of daily prices for PACS and SPY (done for you).
px = yf.download([TICKER, COMPARE], period="2y", auto_adjust=True, progress=False)["Close"]
print(px.tail())     # look at the data before doing maths on it

s = px[TICKER].dropna()

# 2. Latest price.            Dictionary: "pandas: picking data" (iloc)
last = None  # TODO

# 3. Total return over the whole period.    Dictionary: "How the commands chain together"
total = None  # TODO  (end / start - 1)

# 4. Daily returns.           Dictionary: "pandas: cleaning and maths" (pct_change)
r = None  # TODO

# 5. Annual volatility.       Dictionary: "numpy" (np.sqrt)
vol = None  # TODO

# 6. Max drawdown (worst fall from a high, a negative number).   Dictionary: cummax
dd = None  # TODO

# 7. Bonus: did PACS beat SPY? Compute SPY's total return the same way.
spy_total = None  # TODO

print(f"{TICKER} last price  {last}")
print(f"{TICKER} total return {total}")
print(f"{TICKER} volatility   {vol}")
print(f"{TICKER} max drawdown {dd}")
print(f"{COMPARE} total return {spy_total}")
# When it works: change the prints to percentages with f"{total:.1%}"
