"""
Your stock list, as a plain CSV you can edit on GitHub (no Python needed).

state/my_stocks.csv:
    ticker,kind,note
    NVDA,holding,bought 2024
    AVGO,watch,

kind = holding (you own it, shown in "My stocks") or watch (scored on the same
yardstick but never picked). Blank kind means holding. Tickers that aren't in the
semis universe are scored as "Watchlist" stocks. Bad lines are reported, never fatal.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

PATH = Path(__file__).parent / "state" / "my_stocks.csv"
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
KINDS = {"holding", "watch"}


def parse(path: Path = PATH) -> dict | None:
    """{'holdings': [...], 'watch': [...], 'notes': {t: note}, 'problems': [str]}
    or None if the file doesn't exist (then config.py uses its built-in lists)."""
    path = Path(path)
    if not path.exists():
        return None
    holdings, watch, notes, problems = [], [], {}, []
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    rows = csv.reader(lines)
    header = next(rows, None)
    if not header or header[0].strip().lower() != "ticker":
        problems.append("First line should be: ticker,kind,note")
        rows = csv.reader(lines)             # treat every line as data
    for n, row in enumerate(rows, start=2 if header and header[0].strip().lower() == "ticker" else 1):
        if not row or not any(c.strip() for c in row) or row[0].strip().startswith("#"):
            continue
        t = row[0].strip().upper().lstrip("$")
        kind = (row[1].strip().lower() if len(row) > 1 else "") or "holding"
        note = ",".join(row[2:]).strip() if len(row) > 2 else ""
        if not TICKER_RE.match(t):
            problems.append(f"Line {n}: '{row[0].strip()}' doesn't look like a ticker — skipped")
            continue
        if kind not in KINDS:
            problems.append(f"Line {n}: kind '{kind}' for {t} should be 'holding' or 'watch' — treated as holding")
            kind = "holding"
        if t in holdings or t in watch:
            if kind == "holding" and t in watch:          # holding wins over watch
                watch.remove(t)
                holdings.append(t)
            problems.append(f"Line {n}: {t} is listed twice — merged")
        elif kind == "holding":
            holdings.append(t)
        else:
            watch.append(t)
        if note:
            notes[t] = note
    return {"holdings": holdings, "watch": watch, "notes": notes, "problems": problems}


def resolve(parsed: dict | None, universe: dict, default_holdings: list[str], default_watch: dict,
            known: dict | None = None) -> tuple[list[str], dict]:
    """(MY_HOLDINGS, WATCHLIST) from the parsed CSV, or the defaults if there's no file.
    Every ticker outside the universe gets a Watchlist entry so it can be scored."""
    if parsed is None:
        return list(default_holdings), dict(default_watch)
    known = {**(known or {}), **default_watch}
    watchlist = {}
    for t in parsed["holdings"] + parsed["watch"]:
        if t in universe or t in watchlist:
            continue
        watchlist[t] = dict(known.get(t) or {"name": t, "group": "Watchlist", "sec": True})
    return list(parsed["holdings"]), watchlist


def unknown(tickers: list[str], failures: dict) -> list[str]:
    """Your tickers whose prices couldn't be downloaded: most likely a typo."""
    return [t for t in tickers if "price" in (failures.get(t) or "")]


def stale(tickers: list[str], px, failures: dict) -> dict[str, int]:
    """Your tickers that HAVE price history but no recent price: {ticker: trading days since last price}.
    Usually a temporary data hiccup, a trading halt, or a delisting (not a typo)."""
    out = {}
    for t in tickers:
        if t in failures or px is None or t not in px:
            continue
        v = px[t].notna().to_numpy()
        if v.any():
            n = int(len(v) - 1 - v.nonzero()[0][-1])
            if n > 0:
                out[t] = n
    return out
