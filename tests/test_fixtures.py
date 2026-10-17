"""Parser tests on hand-made SEC files that copy real EDGAR quirks
(see tests/fixtures/make_fixtures.py for what each file contains)."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fundamentals import build_series  # noqa: E402
from factors import fundamental_factors, _known  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / f"{name}.json").read_text())


def by_end(s):
    return {d.strftime("%Y-%m-%d"): (v, f.strftime("%Y-%m-%d"))
            for d, v, f in zip(s["end"], s["val"], s["filed"])}


def test_53_week_year_q4_derived_and_amendment_ignored():
    s = build_series(load("aapl_like"))
    rev = by_end(s["revenue"])
    # 4 quarters, the 14-week Q1 included, the 6-month YTD figure ignored
    assert list(rev) == ["2022-12-31", "2023-04-01", "2023-07-01", "2023-09-30"]
    # Q1 = ORIGINAL value (not the 2024 restated comparative)
    assert rev["2022-12-31"] == (117_000, "2023-02-03")
    # Q4 = 10-K annual (not the 10-K/A) minus Q1..Q3, known on the 10-K date
    assert rev["2023-09-30"] == (383_000 - 117_000 - 95_000 - 82_000, "2023-11-03")


def test_ytd_cash_flow_53_week():
    cfo = by_end(build_series(load("aapl_like"))["cfo"])
    assert [v for v, _ in cfo.values()] == [34_000, 28_000, 26_000, 22_000]


def test_revenue_tag_switch_and_late_january_year():
    s = build_series(load("nvda_like"))
    rev = s["revenue"]
    assert len(rev) == 8
    gaps = rev["end"].diff().dt.days.dropna()
    assert gaps.between(84, 98).all(), gaps.tolist()
    r = by_end(rev)
    assert r["2018-01-28"][0] == 9_714 - 1_937 - 2_230 - 2_636   # old tag, original value
    assert r["2019-01-27"][0] == 11_716 - 3_207 - 3_123 - 3_181  # new tag
    # COGS backed out of gross profit, Q4 included
    assert len(s["cogs"]) == 8


def test_share_classes_summed_and_split_adjusted():
    splits = pd.Series([20.0], index=pd.to_datetime(["2022-07-18"]))
    sh = build_series(load("googl_like"), splits)["shares"]
    assert len(sh) == 1 and sh["val"].iloc[0] == (300 + 45 + 320) * 20


def test_amendment_only_value_uses_amendment_date():
    rev = build_series(load("googl_like"))["revenue"]
    r = by_end(rev)
    assert r["2021-06-30"] == (62_000, "2021-09-15")
    # not known before the amendment was filed (no look-ahead)
    assert "2021-06-30" not in by_end(_known(rev, pd.Timestamp("2021-09-01")))


def test_missing_inventory_does_not_crash():
    s = build_series(load("googl_like"))
    assert s["inventory"].empty and s["cogs"].empty
    out = fundamental_factors(s, pd.Timestamp("2021-12-01"), price=None)
    assert isinstance(out, dict)
    assert pd.isna(out.get("inv_days_change", float("nan")))


def test_download_failures_flagged_in_health():
    import data_health
    s = build_series(load("aapl_like"))
    asof = pd.Timestamp("2023-12-01")
    nf = pd.DataFrame({"n_factors": [5]}, index=["AAPL"])
    h = data_health.build({"AAPL": s}, ["AAPL"], nf, asof, {},
                          failures={"AAPL": "SEC download failed (Timeout)", "SMCI": "price download failed"})
    rows = {r["ticker"]: r for r in h["rows"]}
    assert rows["SMCI"]["status"] == "warn" and "price download failed" in rows["SMCI"]["flags"][0]
    assert rows["AAPL"]["flags"][0].startswith("Download failed")
    assert h["summary"]["failed"] == 2


def test_price_retry_keeps_good_tickers(monkeypatch):
    """Tickers that come back empty are retried; good ones are kept."""
    import data_sources as ds
    import sys, types
    calls = []
    idx = pd.bdate_range("2024-01-01", periods=5)

    def fake_download(ts, **kw):
        calls.append(list(ts))
        ok = [t for t in ts if t != "BAD" and (t != "FLAKY" or len(calls) > 1)]
        cols = pd.MultiIndex.from_product([["Adj Close", "Close", "Stock Splits"], list(ts)])
        df = pd.DataFrame(float("nan"), index=idx, columns=cols)
        for t in ok:
            df[("Adj Close", t)] = df[("Close", t)] = 10.0
            df[("Stock Splits", t)] = 0.0
        return df

    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=fake_download))
    monkeypatch.setattr(ds.time, "sleep", lambda s: None)
    px, close, splits = ds.prices(["GOOD", "FLAKY", "BAD"], "2024-01-01")
    assert sorted(px.columns) == ["FLAKY", "GOOD"]
    assert calls[1] == ["FLAKY", "BAD"] and calls[2] == ["BAD"]
