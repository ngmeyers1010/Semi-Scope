"""
What could $1,000 become? A range of outcomes from the backtest's own past.

A single backtest is ONE path through history. To see the range, this module replays that
history in a different order many times (a "block bootstrap"):

  * take the backtest's quarterly returns (strategy and SPY, same quarters)
  * build a path by stitching together random BLOCKS of 4 consecutive quarters, so good and
    bad stretches stay together the way they really happened (markets have streaks)
  * repeat 5,000 times with a fixed seed, so the numbers are the same on every run
  * SPY is replayed with the SAME sampled quarters, so "beat SPY" is a fair, paired comparison

This is not a forecast. It assumes the future looks like a reshuffled past, and with demo
data the past itself is made up.
"""
from __future__ import annotations

import math

import numpy as np

N_PATHS = 5000
BLOCK = 4                    # quarters per block (1 year)
HORIZONS = (1, 3, 5)         # years
SEED = 42
MIN_QUARTERS = 8
START = 1000.0


def _clean(qs: list[dict]) -> tuple[np.ndarray, np.ndarray | None]:
    rows = [(q.get("return"), q.get("spy")) for q in qs or []]
    rows = [(r, s) for r, s in rows if isinstance(r, (int, float)) and math.isfinite(r)]
    strat = np.array([r for r, _ in rows], dtype=float)
    spy = [s for _, s in rows]
    ok = all(isinstance(s, (int, float)) and math.isfinite(s) for s in spy)
    return strat, (np.array(spy, dtype=float) if ok and spy else None)


def sample_index(n: int, quarters: int, n_paths: int = N_PATHS, block: int = BLOCK, seed: int = SEED) -> np.ndarray:
    """(n_paths, quarters) array of row numbers: random blocks of `block` consecutive quarters."""
    rng = np.random.default_rng(seed)
    b = min(block, n)
    n_blocks = -(-quarters // b)                                   # ceil
    starts = rng.integers(0, n - b + 1, size=(n_paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(n_paths, -1)
    return idx[:, :quarters]


def _max_dd(paths: np.ndarray) -> np.ndarray:
    """Per path max drawdown on quarterly values (start = START included)."""
    full = np.concatenate([np.full((paths.shape[0], 1), START), paths], axis=1)
    return (full / np.maximum.accumulate(full, axis=1) - 1).min(axis=1)


def simulate(strat: np.ndarray, spy: np.ndarray | None, years: int = max(HORIZONS),
             n_paths: int = N_PATHS, seed: int = SEED) -> dict:
    q = 4 * years
    idx = sample_index(len(strat), q, n_paths, BLOCK, seed)
    s_paths = START * np.cumprod(1 + strat[idx], axis=1)
    b_paths = START * np.cumprod(1 + spy[idx], axis=1) if spy is not None else None
    return {"strategy": s_paths, "spy": b_paths}


def build(quarters: list[dict], n_paths: int = N_PATHS, seed: int = SEED) -> dict | None:
    strat, spy = _clean(quarters)
    if len(strat) < MIN_QUARTERS:
        return None
    sim = simulate(strat, spy, max(HORIZONS), n_paths, seed)
    S, B = sim["strategy"], sim["spy"]
    pct = lambda a, p: float(np.percentile(a, p))
    out = {"n_quarters": int(len(strat)), "n_paths": n_paths, "block": BLOCK, "start": START, "horizons": []}
    for y in HORIZONS:
        end = S[:, 4 * y - 1]
        h = {"years": y, "p10": pct(end, 10), "p50": pct(end, 50), "p90": pct(end, 90),
             "loss": float((end < START).mean())}
        if B is not None:
            h["beat_spy"] = float((end > B[:, 4 * y - 1]).mean())
            h["spy_p50"] = pct(B[:, 4 * y - 1], 50)
        out["horizons"].append(h)
    out["worst_dd_5pct"] = pct(_max_dd(S), 5)
    # fan chart: value at every quarter 0..20 for the 10th/50th/90th percentile (+ SPY median)
    full = np.concatenate([np.full((S.shape[0], 1), START), S], axis=1)
    out["fan"] = {"q": list(range(full.shape[1])),
                  "p10": [round(float(v)) for v in np.percentile(full, 10, axis=0)],
                  "p50": [round(float(v)) for v in np.percentile(full, 50, axis=0)],
                  "p90": [round(float(v)) for v in np.percentile(full, 90, axis=0)]}
    if B is not None:
        fb = np.concatenate([np.full((B.shape[0], 1), START), B], axis=1)
        out["fan"]["spy_p50"] = [round(float(v)) for v in np.percentile(fb, 50, axis=0)]
    out["read"] = read(out)
    return out


def _money(x: float) -> str:
    return f"${x:,.0f}"


def read(o: dict) -> str:
    h5 = next(h for h in o["horizons"] if h["years"] == max(HORIZONS))
    h1 = next(h for h in o["horizons"] if h["years"] == min(HORIZONS))
    text = (f"Replaying the backtest's {o['n_quarters']} quarters in random 1-year blocks, $1,000 became "
            f"{_money(h5['p10'])} to {_money(h5['p90'])} after 5 years in 8 of 10 replays (middle: {_money(h5['p50'])}). "
            f"After 1 year it was below $1,000 in {h1['loss']:.0%} of replays")
    if h5.get("beat_spy") is not None:
        text += f", and it beat SPY over 5 years in {h5['beat_spy']:.0%}"
    text += (f". The worst 1 in 20 replays fell {-o['worst_dd_5pct']:.0%} or more at some point. "
             "This replays the past; it is not a forecast.")
    return text
