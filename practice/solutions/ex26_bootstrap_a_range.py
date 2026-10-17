"""Solution: ex26_bootstrap_a_range"""
import numpy as np


def block_paths(returns, years: int, n_paths: int, block: int = 4, seed: int = 42):
    r = np.asarray(returns, dtype=float)
    n, q = len(r), 4 * years
    n_blocks = -(-q // block)                                   # ceil(q / block)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block + 1, size=(n_paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_paths, -1)[:, :q]
    return 1000 * np.cumprod(1 + r[idx], axis=1)


def summary(paths) -> dict:
    end = np.asarray(paths)[:, -1]
    return {"p10": float(np.percentile(end, 10)), "p50": float(np.percentile(end, 50)),
            "p90": float(np.percentile(end, 90)), "loss": float((end < 1000).mean())}
