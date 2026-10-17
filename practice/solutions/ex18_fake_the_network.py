"""Solution: ex18_fake_the_network"""

import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401


def latest_close(ticker: str, download):
    px = download([ticker])
    if ticker not in px:
        return None
    s = px[ticker].dropna()
    if s.empty:
        return None
    return float(s.iloc[-1])


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
