"""
Data access: SEC EDGAR (fundamentals) and Yahoo Finance via yfinance (prices).
Raw downloads are cached in cache/ so reruns are fast and polite to the SEC.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import SEC_USER_AGENT_DEFAULT

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)
UA = os.environ.get("SEC_USER_AGENT") or SEC_USER_AGENT_DEFAULT
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}

# One shared connection that retries temporary failures (rate limits, server
# hiccups) 3 times, waiting 1s, 2s, 4s in between. Free data sources blip.
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"])))


def _get_json(url: str, cache_file: str, max_age_hours: float = 20) -> dict:
    """GET a JSON URL, reusing a cached copy if it is fresh enough."""
    path = CACHE / cache_file
    if path.exists() and (time.time() - path.stat().st_mtime) < max_age_hours * 3600:
        return json.loads(path.read_text())
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    path.write_text(r.text)
    time.sleep(0.15)  # SEC asks for <10 requests/second
    return r.json()


def ticker_to_cik() -> dict[str, int]:
    """Map ticker -> SEC CIK number (the SEC's company ID)."""
    data = _get_json("https://www.sec.gov/files/company_tickers.json",
                     "company_tickers.json", max_age_hours=24 * 7)
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def company_facts(cik: int) -> dict:
    """All XBRL facts a company has ever filed (the raw material for fundamentals)."""
    return _get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
                     f"facts_{cik}.json")


def prices(tickers: list[str], start: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    """Returns (px, close, splits):
    px     - split + dividend adjusted closes (for returns)
    close  - split-adjusted closes WITHOUT dividend adjustment (for market cap)
    splits - stock split ratios by date (0 = no split), one column per ticker
    """
    import yfinance as yf

    def download(ts):
        return yf.download(list(ts), start=start, auto_adjust=False, actions=True,
                           progress=False, threads=True)

    def col(raw, name, ts):
        if raw is None or raw.empty or name not in raw.columns.get_level_values(0):
            return pd.DataFrame()
        df = raw[name]
        if isinstance(df, pd.Series):
            df = df.to_frame(ts[0])
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df.sort_index().dropna(axis=1, how="all")

    out = {"Adj Close": [], "Close": [], "Stock Splits": []}
    todo = list(tickers)
    for attempt in range(3):          # retry only the tickers that came back empty
        if not todo:
            break
        if attempt:
            time.sleep(5 * attempt)
            print(f"  retrying {len(todo)} tickers: {todo}")
        try:
            raw = download(todo)
        except Exception as e:  # network error: try again
            print(f"  price download error: {e}")
            continue
        got = col(raw, "Adj Close", todo)
        for k in out:
            df = col(raw, k, todo)
            keep = [t for t in df.columns if t in got.columns]
            if keep:
                out[k].append(df[keep])
        todo = [t for t in todo if t not in got.columns]
    if todo:
        print(f"  ! no prices for: {todo}")

    def join(frames):
        return pd.concat(frames, axis=1, sort=True).sort_index() if frames else pd.DataFrame()

    splits = join(out["Stock Splits"])
    return join(out["Adj Close"]), join(out["Close"]), (splits if not splits.empty else None)
