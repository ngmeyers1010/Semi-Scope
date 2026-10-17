"""FIFO tax lots, short/long-term boundary, wash-sale flags, preview."""
import pandas as pd
import pytest

import mytrades as mt


def T(*rows):
    return pd.DataFrame([{"date": pd.Timestamp(d), "ticker": t, "action": a, "shares": float(n),
                          "price": float(p), "note": ""} for d, t, a, n, p in rows], columns=mt.COLUMNS)


def test_fifo_order_across_partial_sells():
    tr = T(("2024-01-02", "MU", "buy", 10, 50), ("2024-03-01", "MU", "buy", 10, 80),
           ("2024-06-03", "MU", "sell", 6, 100), ("2024-07-01", "MU", "sell", 8, 100))
    r = mt.tax_lots(tr, {"MU": 100}, "2024-08-01")
    # first sell: 6 from lot 1 (gain 6*50); second: 4 from lot 1 + 4 from lot 2
    assert r["sales"][0]["gain"] == pytest.approx(300)
    assert r["sales"][1]["gain"] == pytest.approx(4 * 50 + 4 * 20)
    assert [(l["date"], l["shares"]) for l in r["open"]] == [("2024-03-01", 6.0)]


def test_long_term_boundary():
    assert mt.long_term_date("2023-03-15") == pd.Timestamp("2024-03-16")
    assert not mt.is_long_term("2023-03-15", "2024-03-15")          # exactly one year: still short-term
    assert mt.is_long_term("2023-03-15", "2024-03-16")              # more than one year
    assert mt.long_term_date("2024-02-29") == pd.Timestamp("2025-03-01")   # leap day
    assert not mt.is_long_term("2024-02-29", "2025-02-28")
    tr = T(("2023-03-15", "NVDA", "buy", 1, 100), ("2023-03-15", "NVDA", "buy", 1, 100),
           ("2024-03-15", "NVDA", "sell", 1, 150), ("2024-03-16", "NVDA", "sell", 1, 150))
    r = mt.tax_lots(tr, {"NVDA": 150}, "2024-04-01")
    assert r["by_year"]["2024"] == {"st": pytest.approx(50), "lt": pytest.approx(50)}


def test_wash_sale_window():
    base = [("2024-05-01", "AMD", "buy", 10, 100), ("2024-06-01", "AMD", "sell", 10, 80)]
    after = mt.tax_lots(T(*base, ("2024-07-01", "AMD", "buy", 5, 85)), {"AMD": 90}, "2024-08-01")
    assert len(after["wash"]) == 1 and after["wash"][0]["buys"] == ["2024-07-01"]        # 30 days after
    before = mt.tax_lots(T(("2024-04-01", "AMD", "buy", 10, 100), ("2024-05-02", "AMD", "buy", 5, 95),
                           ("2024-06-01", "AMD", "sell", 10, 80)), {"AMD": 90}, "2024-08-01")
    assert len(before["wash"]) == 1 and before["wash"][0]["buys"] == ["2024-05-02"]       # 30 days before
    late = mt.tax_lots(T(*base, ("2024-07-02", "AMD", "buy", 5, 85)), {"AMD": 90}, "2024-08-01")
    assert late["wash"] == []                                                            # 31 days: fine
    gain = mt.tax_lots(T(("2024-05-01", "AMD", "buy", 10, 100), ("2024-06-01", "AMD", "sell", 10, 120),
                         ("2024-06-05", "AMD", "buy", 5, 110)), {"AMD": 90}, "2024-08-01")
    assert gain["wash"] == []                                                            # gains never wash


def test_fifo_total_matches_average_cost():
    tr = T(("2023-01-03", "MU", "buy", 10, 50), ("2023-06-01", "MU", "buy", 5, 70),
           ("2024-02-01", "MU", "sell", 12, 90), ("2024-05-01", "MU", "buy", 4, 60),
           ("2025-01-02", "MU", "sell", 7, 75), ("2024-01-02", "AMD", "buy", 3, 140),
           ("2024-09-03", "AMD", "sell", 3, 120))
    tr = tr.sort_values("date", kind="stable").reset_index(drop=True)
    last = {"MU": 100.0, "AMD": 150.0}
    lots = mt.tax_lots(tr, last, "2025-06-01")
    rows, totals, _ = mt.positions(tr, last)
    # realized + unrealized is the same money either way; fully closed AMD matches exactly
    assert lots["realized"] + lots["unrealized"] == pytest.approx(totals["realized"] + totals["unrealized"])
    amd = next(r for r in rows if r["ticker"] == "AMD")
    assert sum(s["gain"] for s in lots["sales"] if s["ticker"] == "AMD") == pytest.approx(amd["realized"])
    assert sum(y["st"] + y["lt"] for y in lots["by_year"].values()) == pytest.approx(lots["realized"])


def test_preview_and_lt_soon():
    tr = T(("2024-01-02", "MU", "buy", 10, 50), ("2025-05-01", "MU", "buy", 10, 80))
    r = mt.tax_lots(tr, {"MU": 100}, "2025-01-01")
    assert r["open"][0]["lt_soon"] and r["open"][0]["term"] == "ST"
    p = mt.preview_sell(r["open"], "MU", 12, 100, "2025-06-01")
    assert p["lt"] == pytest.approx(10 * 50) and p["st"] == pytest.approx(2 * 20)
    assert mt.preview_sell(r["open"], "MU", 99, 100, "2025-06-01")["capped"]
