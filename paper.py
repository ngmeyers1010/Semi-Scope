"""
Forward paper portfolio — the real test.

Picks are appended to state/paper_portfolio.json and never edited afterward.
Because the file lives in git, every quarter's picks are timestamped by a
commit made BEFORE the returns happened. That's your proof it isn't hindsight.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import rebalance_dates, stats
from config import COST_BPS, PAPER_START, TOP_N
from factors import score

STATE = Path(__file__).parent / "state" / "paper_portfolio.json"


def load() -> dict:
    """Read the paper-portfolio log (or start an empty one)."""
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"note": "Append-only log of live paper picks. Do not edit past entries.",
            "entries": []}


def save(state: dict) -> None:
    """Write the paper-portfolio log back to disk."""
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def _record(state: dict, all_series: dict, px: pd.DataFrame, d: pd.Timestamp,
            tickers: list[str], reason: str) -> None:
    """Score the universe as of `d` and append the top-N picks to the log."""
    ranked, _ = score(all_series, px, d, tickers)
    picks = ranked["score"].dropna().head(TOP_N).index.tolist()
    state["entries"].append({
        "date": d.strftime("%Y-%m-%d"),
        "reason": reason,
        "picks": picks,
        "entry_prices": {t: round(float(px.loc[d, t]), 4) for t in picks},
        "scores": {t: round(float(ranked.loc[t, "score"]), 3) for t in picks},
        "recorded_at": pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def update(all_series: dict, px: pd.DataFrame, tickers: list[str]) -> tuple[dict, list[pd.Timestamp]]:
    """Add any due entries. Returns (state, list_of_new_entry_dates)."""
    state = load()
    last_px_date = px.index[-1]
    new = []
    if not state["entries"]:
        if last_px_date >= pd.Timestamp(PAPER_START) - pd.Timedelta(days=7):
            _record(state, all_series, px, last_px_date, tickers, "inception")
            new.append(last_px_date)
    else:
        last = pd.Timestamp(state["entries"][-1]["date"])
        for d in rebalance_dates(px.index, last + pd.Timedelta(days=1)):
            # only record a rebalance within a few days of it happening, so the
            # log can never be back-filled with hindsight
            if (last_px_date - d).days <= 10:
                _record(state, all_series, px, d, tickers, "quarterly rebalance")
                new.append(d)
    if new:
        save(state)
    return state, new


def performance(state: dict, px: pd.DataFrame, bench_px: pd.DataFrame) -> dict | None:
    """Equity curve, stats and current holdings for the logged paper picks."""
    entries = state["entries"]
    if not entries:
        return None
    daily = px.pct_change()
    value, prev_w, curve = 1.0, pd.Series(dtype=float), []
    start = pd.Timestamp(entries[0]["date"])
    curve.append((start, 1.0))
    holdings = []
    for i, e in enumerate(entries):
        d = pd.Timestamp(e["date"])
        end = pd.Timestamp(entries[i + 1]["date"]) if i + 1 < len(entries) else px.index[-1]
        w = pd.Series(1 / len(e["picks"]), index=e["picks"])
        value *= 1 - w.subtract(prev_w, fill_value=0).abs().sum() * COST_BPS / 1e4
        # a pick whose prices failed to download today counts as flat (0%) rather than crashing the run
        period = daily.loc[(daily.index > d) & (daily.index <= end)].reindex(columns=e["picks"]).fillna(0)
        if len(period):
            growth = (1 + period).cumprod()
            path = value * (growth * w).sum(axis=1)
            curve += list(path.items())
            drifted = growth.iloc[-1] * w
            prev_w = drifted / drifted.sum()
            value = path.iloc[-1]
        else:
            prev_w = w
        if i == len(entries) - 1:
            for t in e["picks"]:
                cur = px[t].dropna() if t in px else pd.Series(dtype=float)
                if cur.empty:          # no prices this run (download failed or delisted)
                    holdings.append({"ticker": t, "entry": e["entry_prices"][t], "last": None, "return": None})
                    continue
                holdings.append({"ticker": t, "entry": e["entry_prices"][t],
                                 "last": round(float(cur.iloc[-1]), 2),
                                 "return": float(cur.iloc[-1] / e["entry_prices"][t] - 1)})
    eq = pd.Series(dict(curve)).sort_index()
    curves = {"paper": eq}
    for b in bench_px.columns:
        bp = bench_px[b].loc[start:].dropna()
        if len(bp):
            curves[b] = bp / bp.iloc[0]
    return {"curves": curves, "stats": {k: stats(v) for k, v in curves.items()},
            "holdings": holdings, "entries": entries}
