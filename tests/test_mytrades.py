"""'My real trades' tracker: cost basis, bad input, missing prices, deposit timing."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mytrades  # noqa: E402

HEADER = "date,ticker,action,shares,price,note\n"


def write(tmp_path, body):
    p = tmp_path / "t.csv"
    p.write_text("# comment line\n" + HEADER + body)
    return p


def test_average_cost_with_partial_sells(tmp_path):
    t, err = mytrades.load(write(tmp_path, "2024-01-02,MU,buy,10,100,\n2024-02-01,MU,buy,10,200,\n"
                                           "2024-03-01,MU,sell,5,300,\n"))
    rows, tot, perr = mytrades.positions(t, {"MU": 250.0})
    mu = rows[0]
    assert not err and not perr
    assert mu["shares"] == 15 and mu["avg_cost"] == pytest.approx(150)      # avg cost unchanged by a sell
    assert mu["realized"] == pytest.approx(5 * (300 - 150))                  # 750
    assert mu["unrealized"] == pytest.approx(15 * (250 - 150))               # 1500
    assert tot["pnl"] == pytest.approx(2250)


def test_oversell_is_a_clear_error(tmp_path):
    t, _ = mytrades.load(write(tmp_path, "2024-01-02,AMD,buy,2,100,\n2024-01-05,AMD,sell,5,110,\n"))
    rows, _, perr = mytrades.positions(t, {"AMD": 120.0})
    assert rows[0]["shares"] == 2                                           # bad sell ignored
    assert "more than the 2 held" in perr[0]


def test_bad_lines_are_reported_not_fatal(tmp_path):
    t, err = mytrades.load(write(tmp_path, "2024-13-45,MU,buy,1,100,\n2024-01-02,MU,hold,1,100,\n"
                                           "2024-01-02,MU,buy,abc,100,\n2024-01-03,MU,buy,1,$1,000.50,\n"))
    assert len(err) == 4 and any("Line 3" in e for e in err) and len(t) == 0
    assert "too many commas" in err[3]    # "$1,000.50" unquoted would silently become $1
    t2, err2 = mytrades.load(write(tmp_path, '2024-01-03,MU,buy,1,"$1,000.50",quoted ok\n'))
    assert not err2 and t2["price"].iloc[0] == 1000.50


def test_missing_price_is_flagged(tmp_path):
    t, _ = mytrades.load(write(tmp_path, "2024-01-02,NVDAA,buy,1,100,typo\n"))
    rows, tot, perr = mytrades.positions(t, {})
    assert rows[0]["value"] is None and "NVDAA" in perr[0]


def test_deposits_are_not_gains(tmp_path):
    """Flat price + a second deposit: value doubles, but time-weighted return is 0."""
    idx = pd.bdate_range("2024-01-01", periods=10)
    close = pd.DataFrame({"MU": 100.0}, index=idx)
    t, _ = mytrades.load(write(tmp_path, "2024-01-01,MU,buy,1,100,\n2024-01-08,MU,buy,1,100,\n"))
    eq = mytrades.equity_curve(t, close)
    assert eq["value"].iloc[-1] == 200 and eq["invested"].iloc[-1] == 200
    assert eq["twr"].iloc[-1] == pytest.approx(1.0)

    close2 = close.copy(); close2.loc[idx[5]:, "MU"] = 110.0                 # +10% before the 2nd buy
    t2, _ = mytrades.load(write(tmp_path, "2024-01-01,MU,buy,1,100,\n2024-01-10,MU,buy,1,110,\n"))
    eq2 = mytrades.equity_curve(t2, close2)
    assert eq2["twr"].iloc[-1] == pytest.approx(1.10)                       # only the real +10%


def test_same_dollars_into_spy():
    idx = pd.bdate_range("2024-01-01", periods=4)
    spy = pd.Series([100, 110, 121, 121.0], index=idx)
    flows = pd.Series([100, 0, 121, 0.0], index=idx)
    v = mytrades.same_dollars_into(spy, flows)
    assert v.iloc[-1] == pytest.approx(1.21 * 100 + 121)


def test_empty_file_is_fine(tmp_path):
    p = tmp_path / "t.csv"; p.write_text(HEADER)
    out = mytrades.build(p, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None)
    assert out["n_trades"] == 0 and out["errors"] == []


# ---- dividends & fees (round 28) ----
def _div_market():
    """Price flat at 100; a $2 dividend on day 5 (price drops to 98, total return flat)."""
    idx = pd.bdate_range("2024-01-01", periods=10)
    close = pd.DataFrame({"TXN": [100.0] * 5 + [98.0] * 5}, index=idx)
    px = pd.DataFrame({"TXN": [100.0] * 10}, index=idx)          # total-return series doesn't drop
    return idx, close, px


def test_dividend_estimated_from_prices():
    idx, close, px = _div_market()
    dps = mytrades.dividends_per_share(close, px)
    assert dps["TXN"].iloc[5] == pytest.approx(2.0) and dps["TXN"].drop(idx[5]).sum() == 0


def test_dividend_credited_to_shares_held(tmp_path):
    idx, close, px = _div_market()
    t, _ = mytrades.load(write(tmp_path, "2024-01-01,TXN,buy,10,100,\n"))
    eq = mytrades.equity_curve(t, close, px)
    assert eq["dividends"].iloc[-1] == pytest.approx(20.0)         # $2 x 10 shares
    assert eq["value"].iloc[-1] == pytest.approx(980 + 20)         # price drop offset by cash
    assert eq["twr"].iloc[-1] == pytest.approx(1.0)                # total return flat, like px


def test_dividend_before_buy_not_credited(tmp_path):
    idx, close, px = _div_market()
    t, _ = mytrades.load(write(tmp_path, f"{idx[6].date()},TXN,buy,10,98,\n"))
    assert mytrades.equity_curve(t, close, px)["dividends"].iloc[-1] == 0
    # bought ON the ex-date: not held at the prior close -> no dividend
    t2, _ = mytrades.load(write(tmp_path, f"{idx[5].date()},TXN,buy,10,98,\n"))
    assert mytrades.equity_curve(t2, close, px)["dividends"].iloc[-1] == 0


def test_manual_dividend_overrides_estimate(tmp_path):
    idx, close, px = _div_market()
    t, _ = mytrades.load(write(tmp_path, f"2024-01-01,TXN,buy,10,100,\n{idx[5].date()},TXN,dividend,1,17.50,broker statement\n"))
    assert mytrades.equity_curve(t, close, px)["dividends"].iloc[-1] == pytest.approx(17.50)


def test_fee_reduces_pnl(tmp_path):
    idx, close, px = _div_market()
    p = write(tmp_path, "2024-01-01,TXN,buy,10,100,\n2024-01-03,,fee,1,4.95,commission\n")
    out = mytrades.build(p, close, px, pd.DataFrame(index=idx), None)
    T = out["totals"]
    assert T["fees"] == pytest.approx(4.95)
    assert T["pnl"] == pytest.approx(-20 + 20 - 4.95)              # price -20, dividend +20, fee
    assert out["positions"][0]["dividends"] == pytest.approx(20.0)
