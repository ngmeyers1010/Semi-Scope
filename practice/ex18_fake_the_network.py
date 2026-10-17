"""
Exercise 18: test code that downloads, without the internet (mirrors tests/fixtures/live_sim.py)

Write latest_close(ticker, download):
  * `download` is a FUNCTION you are given. Call it as download([ticker]). It returns a
    pandas DataFrame of closing prices: one column per ticker, one row per day.
  * Return the most recent price that isn't NaN, as a float.
  * Return None if the ticker's column is missing, or if it is entirely NaN. (Yahoo returns
    an all-NaN column for a ticker it doesn't know, e.g. a typo like "NVDAA".)

Run `python practice/check.py 18` to check your answer, and `python practice/ex18_fake_the_network.py`
to run the small test at the bottom of this file.

Why pass `download` in as an argument? ("dependency injection")
  The real one would be yfinance.download, which needs the internet, is slow, and returns
  different numbers every day. A test can pass a FAKE function that returns a small,
  hand-made table instead, so it runs offline, instantly, and gives the same answer every time.

Why does live_sim.py fake the OUTERMOST layer (the download itself) and nothing deeper?
  Every line of code between the download and the dashboard still runs for real: the retry
  loop, dropping empty columns, the SEC parsers, scoring, writing data.json. If we faked
  something deeper (say, handed run.py a finished price table), all the code we skipped would
  go untested, and launch-day bugs hide exactly there. Fake as little as possible, as far
  out as possible.
"""
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def latest_close(ticker: str, download):
    # HINT: px = download([ticker])
    # HINT: if ticker not in px: return None
    # HINT: s = px[ticker].dropna(); if s.empty: return None; return float(s.iloc[-1])
    # YOUR CODE HERE
    raise NotImplementedError


# ---- a test with a fake download (read it, then run this file) ----
def fake_download(tickers):
    """Pretends to be Yahoo: 3 days of prices. MU's last day is missing; NVDAA is a typo."""
    idx = pd.to_datetime(["2026-10-09", "2026-10-12", "2026-10-13"])
    table = {"MU": [100.0, 102.0, np.nan], "NVDA": [180.0, 182.5, 181.0], "NVDAA": [np.nan] * 3}
    return pd.DataFrame({t: table[t] for t in tickers if t in table}, index=idx)


def test_latest_close():
    assert latest_close("NVDA", fake_download) == 181.0
    assert latest_close("MU", fake_download) == 102.0      # skips the missing last day
    assert latest_close("NVDAA", fake_download) is None    # all NaN: probably a typo
    assert latest_close("ZZZZ", fake_download) is None     # not in the table at all


if __name__ == "__main__":
    test_latest_close()
    print("test_latest_close passed")
