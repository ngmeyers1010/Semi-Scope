"""Warnings hygiene: deprecations from OUR code fail the build (pytest.ini filterwarnings).

pandas announces behaviour changes as warnings first (e.g. round 65: `concat` will stop sorting
date indexes). A warning that scrolls by today is a silently different number after an upgrade,
so a representative slice of the pipeline runs here with ALL deprecation warnings as errors.
"""
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def demo():
    import demo_data
    from config import BACKTEST_START
    tickers = ["MU", "AMD", "NVDA", "INTC", "AMAT", "LRCX", "TXN", "ADI", "KLAC", "ON"]
    all_series, px, bench = demo_data.generate(tickers, ["SPY", "SOXX"], "2014-03-01", seed=5)
    return tickers, all_series, px, bench, BACKTEST_START


def _strict():
    w = warnings.catch_warnings()
    w.__enter__()
    for cat in (DeprecationWarning, FutureWarning, PendingDeprecationWarning):
        warnings.simplefilter("error", cat)
    return w


def test_pipeline_slice_raises_no_deprecations(demo):
    import backtest
    import capture
    import decay
    import factors
    import risk
    import steady
    tickers, all_series, px, bench, start = demo
    w = _strict()
    try:
        ranked, z = factors.score(all_series, px, px.index[-1], tickers)
        assert len(ranked) and z.shape[0] == len(ranked)
        curves, quarters, panel = backtest.run_backtest(all_series, px, bench, tickers, "2016-03-01")
        assert quarters and capture.build(curves, bench) is not None
        assert decay.build(px, quarters, tickers) is not None
        assert steady.build(curves, bench)["backtest"]["available"]
        r = px[tickers].pct_change().dropna(how="all")
        risk.beta(r.mean(axis=1), bench["SPY"].pct_change())
    finally:
        w.__exit__(None, None, None)


def test_ini_turns_our_deprecations_into_errors():
    """The pytest.ini filter must catch a warning raised from a repo module (sanity check that the
    regex isn't silently matching nothing)."""
    with pytest.raises(FutureWarning):
        warnings.warn("pretend pandas changed a default", FutureWarning)


def test_mixed_datetime_concat_is_explicit():
    """The exact round-65 pattern, now written the explicit way everywhere."""
    import re
    bad = []
    for p in ROOT.glob("*.py"):
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if re.search(r"pd\.concat\(.*axis=1", line) and "sort=" not in line:
                bad.append(f"{p.name}:{i}")
    assert not bad, f"pd.concat(axis=1) without sort= (pandas will change the default): {bad}"
