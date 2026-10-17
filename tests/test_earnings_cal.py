"""Earnings calendar: dates, week buckets, expected-move bands, digest lines."""
import pandas as pd
import pytest

import earnings_cal as ec

ASOF = "2026-10-13"          # a Tuesday


def rec(t, nxt="2026-10-20", days=7, price=100.0, avg=0.05, events=None):
    ev = events if events is not None else [{"day": f"2025-0{i}-01", "ret": r}
                                             for i, r in enumerate([0.04, -0.06, 0.02, 0.08], 1)]
    return {"ticker": t, "last_price": price,
            "filing": None if nxt is None else {"next_filing": nxt, "days_until": days},
            "earnings": None if avg is None else {"avg_abs": avg, "events": ev}}


def test_bucket_boundaries():
    assert ec.bucket(ASOF, "2026-10-13") == "This week"           # today
    assert ec.bucket(ASOF, "2026-10-18") == "This week"           # Sunday closes the week
    assert ec.bucket(ASOF, "2026-10-19") == "Next week"           # Monday starts the next
    assert ec.bucket(ASOF, "2026-10-25") == "Next week"
    assert ec.bucket(ASOF, "2026-10-26") == "Later"
    assert ec.bucket("2026-10-18", "2026-10-19") == "Next week"   # as-of on a Sunday


def test_band_math():
    assert ec.band(100.0, 0.05) == [95.0, 105.0]
    assert ec.band(None, 0.05) is None and ec.band(100, None) is None and ec.band(100, 0) is None
    assert ec.band(100, float("nan")) is None


def test_build_rows_and_text():
    cal = ec.build([rec("MU"), rec("ZZ"), rec("NVDA", nxt="2026-11-04", days=22, price=180.0, avg=0.061)],
                   ASOF, owned={"MU", "NVDA"}, picks={"AMAT"})
    assert [r["ticker"] for r in cal["rows"]] == ["MU", "NVDA"]           # ZZ: not owned, not a pick
    mu = cal["rows"][0]
    assert mu["week"] == "Next week" and mu["band"] == [95.0, 105.0]
    assert mu["n"] == 4 and mu["ups"] == 3 and mu["biggest"]["ret"] == 0.08
    nv = cal["rows"][1]["text"]
    assert nv == "NVDA ≈Nov 4 (in 22 days): usually moves ±6.1% the next day (≈$169–$191); up 3 of last 4."


def test_no_history_still_listed_and_no_date_omitted():
    cal = ec.build([rec("NEW", avg=None, events=[]), rec("NODATE", nxt=None)], ASOF, {"NEW", "NODATE"}, set())
    assert [r["ticker"] for r in cal["rows"]] == ["NEW"]
    r = cal["rows"][0]
    assert r["band"] is None and r["move"] is None and r["n"] is None
    assert r["text"].endswith("no earnings-day history yet.")


def test_digest_items_window_and_empty_section():
    cal = ec.build([rec("MU", days=7), rec("NVDA", nxt="2026-11-04", days=22)], ASOF, {"MU", "NVDA"}, set())
    assert [t.split()[0] for t in ec.digest_items(cal)] == ["MU"]
    assert ec.digest_items(None) == [] and ec.digest_items({"rows": []}) == []
    import digest
    base = {"prices_asof": ASOF, "top_n": 5, "rankings": [], "holdings": []}
    titles = [s["title"] for s in digest.build({**base, "earnings_cal": cal}, write=False)["sections"]]
    assert any(t.startswith("Earnings coming up") for t in titles)
    titles = [s["title"] for s in digest.build({**base, "earnings_cal": {"rows": []}}, write=False)["sections"]]
    assert not any(t.startswith("Earnings coming up") for t in titles)


def test_small_price_band_keeps_cents_on_both_ends():
    r = ec.build([rec("CHEAP", price=12.9, avg=0.03)], ASOF, {"CHEAP"}, set())["rows"][0]
    assert "(≈$12.51–$13.29)" in r["text"]
