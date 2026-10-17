"""Out-of-sample split + walk-forward weights: no overlap, no look-ahead."""
import pytest
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demo_data  # noqa: E402
import robustness  # noqa: E402
from factors import score  # noqa: E402
from research import oos_verdict, split_quarters  # noqa: E402

TICKERS = [f"T{i}" for i in range(12)]


def test_split_periods_do_not_overlap():
    dates = [d.strftime("%Y-%m-%d") for d in pd.date_range("2018-03-01", "2021-12-01", freq="3MS")]
    ins, oos = split_quarters(dates, "2020-01-01")
    assert not set(ins) & set(oos)
    assert "2019-12-01" not in ins + oos                       # straddles the split: dropped
    nxt = {d: dates[i + 1] for i, d in enumerate(dates[:-1])}
    assert all(pd.Timestamp(nxt[d]) <= pd.Timestamp("2020-01-01") for d in ins)  # ends before split
    assert all(pd.Timestamp(d) >= pd.Timestamp("2020-01-01") for d in oos)


def test_oos_verdicts():
    assert oos_verdict(0.06, 0.05) == "held up"
    assert oos_verdict(0.06, 0.01) == "weakened"
    assert oos_verdict(0.06, -0.04) == "flipped"
    assert oos_verdict(0.005, 0.08) == "no in-sample edge"
    assert oos_verdict(-0.29, -0.28) == "backwards in both"     # consistently wrong is NOT "held up"
    assert oos_verdict(-0.04, 0.035) == "turned positive"


@pytest.mark.slow
def test_walk_forward_weights_have_no_lookahead():
    all_series, px, _ = demo_data.generate(TICKERS, ["SPY", "SOXX"], "2013-03-01", seed=5)
    base = {"rev_growth": 1.0, "momentum": 1.0, "gm_change": 1.0, "low_vol": 0.5}
    dates = [d for d in robustness.month_starts(px.index, "2014-03-01") if d.month in (3, 6, 9, 12)]
    d = dates[16]                                              # 4 years in

    def weights_at(px_used, series_used):
        zs = [(t, score(series_used, px_used, t, TICKERS)[1]) for t in dates if t <= px_used.index[-1]]
        hist = robustness.ic_history(zs, px_used, list(base))
        return robustness.walk_forward_weights(hist, d, base)

    full = weights_at(px, all_series)
    cut_series = {t: {k: v[v["filed"] < d] for k, v in s.items()} for t, s in all_series.items()}
    cut = weights_at(px.loc[:d], cut_series)
    assert full.keys() == cut.keys()
    assert np.allclose([full[k] for k in sorted(full)], [cut[k] for k in sorted(cut)])
    assert all(v >= 0 for v in full.values())                  # never short a factor
    assert full != base                                        # really learned, not the fallback


def test_walk_forward_falls_back_without_history():
    base = {"a": 1.0, "b": 0.5}
    assert robustness.walk_forward_weights([], pd.Timestamp("2015-01-01"), base) == base
