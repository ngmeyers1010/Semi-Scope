"""
Exercise 26: bootstrap a range (mirrors outcomes.py)

One backtest is one path through history. Replay the same quarters in a random order many
times to see a RANGE of outcomes. Write two functions.

1) block_paths(returns, years, n_paths, block=4, seed=42) -> numpy array, shape (n_paths, 4*years)

   returns: list of quarterly returns, e.g. [0.05, -0.02, ...] (n of them)
   Each row is one replay: the value of $1,000 after each quarter.

   * q = 4 * years quarters per path; n_blocks = ceil(q / block)   (use -(-q // block))
   * rng = np.random.default_rng(seed)
   * starts = rng.integers(0, n - block + 1, size=(n_paths, n_blocks))
       (integers' upper bound is EXCLUSIVE, so +1 lets the very last block be picked)
   * each start s means quarters s, s+1, ..., s+block-1 (consecutive: markets have streaks)
       idx = starts[:, :, None] + np.arange(block)      -> shape (n_paths, n_blocks, block)
       idx = idx.reshape(n_paths, -1)[:, :q]           -> stitch blocks, trim to q
   * r = np.array(returns)[idx]; values = 1000 * np.cumprod(1 + r, axis=1)

2) summary(paths) -> {"p10", "p50", "p90", "loss"} as floats
   * percentiles (np.percentile) of the LAST column only (where each replay ended)
   * loss = share of replays that ended below 1000

Run `python practice/check.py 26` to check your answer.
"""
import numpy as np


def block_paths(returns, years: int, n_paths: int, block: int = 4, seed: int = 42):
    # YOUR CODE HERE
    raise NotImplementedError


def summary(paths) -> dict:
    # HINT: end = paths[:, -1]
    # YOUR CODE HERE
    raise NotImplementedError
