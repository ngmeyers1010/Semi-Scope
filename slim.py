"""
Make data.json small enough to load fast on a phone.

Two tricks, both undone by the dashboard right after it loads (unpackPairs / detail.json):

1. split():  per-stock heavy fields (1-year prices, quarterly history, earnings events)
   move to docs/detail.json, which the dashboard only downloads when you open a stock's
   details or the Compare card.
2. pack():   a dict of time series like {"strategy": [[date, v], ...], "SPY": [[date, v], ...]}
   repeats every date once per series. Packed, the dates are stored once:
   {"_d": [dates...], "strategy": [v...], "SPY": [v...]}  (null where a series has no value).
"""
from __future__ import annotations

HEAVY = ("px_1y", "history", "earnings")


def split(data: dict) -> tuple[dict, dict]:
    """(slim data, detail) — detail = {ticker: {px_1y, history, earnings}}."""
    detail: dict[str, dict] = {}

    def strip(row: dict | None) -> None:
        if not isinstance(row, dict) or "ticker" not in row:
            return
        d = detail.setdefault(row["ticker"], {})
        for k in HEAVY:
            if k in row:
                d.setdefault(k, row.pop(k))      # first copy wins (holdings repeat ranking rows)
        # keep a tiny summary so lists/tables don't need the detail file
        e = d.get("earnings")
        if isinstance(e, dict):
            row["earn_avg_abs"] = e.get("avg_abs")

    for r in (data.get("rankings") or []) + (data.get("watchlist") or []):
        strip(r)
    for h in data.get("holdings") or []:
        strip(h.get("current"))
    return data, detail


def merge(data: dict, detail: dict) -> dict:
    """Put detail fields back on every stock row (used by Streamlit and tests)."""
    def put(row):
        if isinstance(row, dict) and row.get("ticker") in detail:
            for k, v in detail[row["ticker"]].items():
                row.setdefault(k, v)
    for r in (data.get("rankings") or []) + (data.get("watchlist") or []):
        put(r)
    for h in data.get("holdings") or []:
        put(h.get("current"))
    return data


def _is_series(v) -> bool:
    """A non-empty [[date, value], ...] list with no repeated dates (repeats can't be packed
    losslessly, so such a list is left as it is)."""
    return (isinstance(v, list) and len(v) > 0
            and all(isinstance(p, list) and len(p) == 2 and isinstance(p[0], str) for p in v)
            and len({p[0] for p in v}) == len(v))


def pack(x):
    """Recursively pack dicts whose values are ALL [[date, value], ...] series (2+ of them).
    Lossless: series with identical dates keep their nulls ("_same"); otherwise dates are
    merged and only series without nulls are packed."""
    if isinstance(x, list):
        return [pack(v) for v in x]
    if not isinstance(x, dict):
        return x
    if len(x) >= 2 and all(_is_series(v) for v in x.values()):
        cols = [[p[0] for p in v] for v in x.values()]
        if all(c == cols[0] for c in cols):
            return {"_d": cols[0], "_same": 1, **{k: [p[1] for p in v] for k, v in x.items()}}
        if all(p[1] is not None for v in x.values() for p in v):
            dates = sorted({d for c in cols for d in c})
            pos = {d: i for i, d in enumerate(dates)}
            out = {"_d": dates}
            for k, v in x.items():
                arr = [None] * len(dates)
                for d, val in v:
                    arr[pos[d]] = val
                out[k] = arr
            return out
    return {k: pack(v) for k, v in x.items()}


def unpack(x):
    """Inverse of pack()."""
    if isinstance(x, list):
        return [unpack(v) for v in x]
    if not isinstance(x, dict):
        return x
    if "_d" in x and isinstance(x["_d"], list):
        dates, same = x["_d"], bool(x.get("_same"))
        return {k: [[d, v] for d, v in zip(dates, arr) if same or v is not None]
                for k, arr in x.items() if k not in ("_d", "_same")}
    return {k: unpack(v) for k, v in x.items()}
