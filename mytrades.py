"""
My real trades: track YOUR actual money, not just the model's paper portfolio.

You keep a simple CSV (state/my_trades.csv) and edit it on GitHub's website
whenever you buy or sell:

    date,ticker,action,shares,price,note
    2026-10-16,MU,buy,3,112.40,first buy

Every daily run turns that into positions, profit/loss, a value curve, and the
same dollars put into SPY or into the model's picks on the same days.

Two kinds of return (both shown):
- Money-weighted ("what did I make?"): value now minus all the money you put in.
- Time-weighted ("how good were the picks?"): removes the effect of WHEN you
  added money, so depositing $500 never counts as a 'gain'. Quarterly returns
  use this one, so they're comparable with SPY.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from mystocks import TICKER_RE

from fundamentals import split_factor_after

COLUMNS = ["date", "ticker", "action", "shares", "price", "note"]
ACTIONS = ("buy", "sell", "dividend", "fee")   # dividend/fee: total cash = shares x price (use shares=1)
EPS = 1e-9


def load(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Read the trades CSV. Bad lines are skipped and explained, never fatal."""
    rows, errors = [], []
    if not Path(path).exists():
        return pd.DataFrame(columns=COLUMNS), []
    with open(path, newline="") as fh:
        lines = [(i, l) for i, l in enumerate(fh, 1) if l.strip() and not l.lstrip().startswith("#")]
    reader = csv.reader([l for _, l in lines])
    header = None
    for (lineno, _), rec in zip(lines, reader):
        rec = [c.strip() for c in rec]
        if header is None:
            header = [c.lower() for c in rec]
            missing = [c for c in COLUMNS[:5] if c not in header]
            if missing:
                return pd.DataFrame(columns=COLUMNS), [f"Header is missing column(s): {', '.join(missing)}. "
                                                       f"First line must be: {','.join(COLUMNS)}"]
            continue
        if len(rec) > len(header):
            errors.append(f"Line {lineno}: too many commas. Write 1000.50, not 1,000.50 "
                          f"(or put quotes around it)."); continue
        r = dict(zip(header, rec + [""] * (len(header) - len(rec))))
        try:
            d = pd.Timestamp(r["date"])
        except (ValueError, TypeError):
            errors.append(f"Line {lineno}: date '{r['date']}' isn't a date (use YYYY-MM-DD)."); continue
        action = r["action"].lower()
        if action not in ACTIONS:
            errors.append(f"Line {lineno}: action must be buy, sell, dividend or fee, got '{r['action']}'."); continue
        try:
            shares, price = float(r["shares"]), float(r["price"].replace("$", "").replace(",", ""))
        except ValueError:
            errors.append(f"Line {lineno}: shares and price must be numbers."); continue
        if shares <= 0 or price <= 0:
            errors.append(f"Line {lineno}: shares and price must be more than 0."); continue
        if not r["ticker"]:
            if action != "fee":
                errors.append(f"Line {lineno}: ticker is empty."); continue
            r["ticker"] = "FEE"
        tick = r["ticker"].strip().upper().lstrip("$")
        if not TICKER_RE.match(tick):
            errors.append(f"Line {lineno}: '{r['ticker'][:20]}' doesn't look like a ticker (letters, digits, '.' or '-')."); continue
        rows.append({"date": d, "ticker": tick, "action": action, "shares": shares,
                     "price": price, "note": r.get("note", "")})
    df = pd.DataFrame(rows, columns=COLUMNS)
    if len(df):
        df = df.sort_values("date", kind="stable").reset_index(drop=True)
    return df, errors


def _adjust_for_splits(trades: pd.DataFrame, splits: pd.DataFrame | None) -> pd.DataFrame:
    """Convert shares/price to today's split units (a 10:1 split later turns
    1 share @ $1000 into 10 shares @ $100). Same money, comparable with prices."""
    t = trades.copy()
    if splits is None or t.empty:
        return t
    for i, r in t.iterrows():
        f = split_factor_after(splits[r["ticker"]], r["date"]) if r["ticker"] in splits else 1.0
        t.at[i, "shares"], t.at[i, "price"] = r["shares"] * f, r["price"] / f
    return t


def positions(trades: pd.DataFrame, last_price: dict) -> tuple[list[dict], dict, list[str]]:
    """Average-cost positions. Returns (rows, totals, errors)."""
    book: dict[str, dict] = {}
    errors = []
    for _, r in trades[trades["action"].isin(["buy", "sell"])].iterrows():
        b = book.setdefault(r["ticker"], {"shares": 0.0, "cost": 0.0, "realized": 0.0, "bought": 0.0})
        if r["action"] == "buy":
            b["shares"] += r["shares"]; b["cost"] += r["shares"] * r["price"]; b["bought"] += r["shares"] * r["price"]
        else:
            if r["shares"] > b["shares"] + EPS:
                errors.append(f"{r['date'].date()}: sell of {r['shares']:g} {r['ticker']} is more than the "
                              f"{b['shares']:g} held — that sell was ignored. Check for a typo or a missing buy.")
                continue
            avg = b["cost"] / b["shares"] if b["shares"] > EPS else 0.0
            b["realized"] += r["shares"] * (r["price"] - avg)
            b["cost"] -= r["shares"] * avg
            b["shares"] -= r["shares"]
            if b["shares"] < EPS:
                b["shares"], b["cost"] = 0.0, 0.0
    rows = []
    for t, b in book.items():
        p = last_price.get(t)
        if p is None and b["shares"] > EPS:
            errors.append(f"No price found for {t} — check the ticker spelling. Its value isn't counted.")
        mv = b["shares"] * p if p is not None else None
        rows.append({"ticker": t, "shares": b["shares"], "avg_cost": b["cost"] / b["shares"] if b["shares"] > EPS else None,
                     "cost_basis": b["cost"], "price": p, "value": mv,
                     "unrealized": (mv - b["cost"]) if mv is not None else None, "realized": b["realized"]})
    rows.sort(key=lambda r: -(r["value"] or 0))
    val = sum(r["value"] or 0 for r in rows)
    cost = sum(r["cost_basis"] for r in rows if r["value"] is not None)
    totals = {"value": val, "cost_basis": cost, "unrealized": val - cost,
              "realized": sum(r["realized"] for r in rows)}
    totals["pnl"] = totals["unrealized"] + totals["realized"]
    return rows, totals, errors


def _flows(trades: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Net money in (+buys, -sells) per trading day; weekend trades move to the next trading day."""
    cf = pd.Series(0.0, index=index)
    for _, r in trades.iterrows():
        pos = index.searchsorted(r["date"])
        if pos < len(index):
            cf.iloc[pos] += (1 if r["action"] == "buy" else -1) * r["shares"] * r["price"]
    return cf


def dividends_per_share(close: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    """Cash dividend per share (in today's split units) paid each day, recovered
    from the gap between the total-return price (px, Adj Close) and the plain
    price (close): dividend = close_yesterday x (total return - price return).
    If a stock pays $1 on a $100 stock, its price drops ~$1 but total return doesn't."""
    cols = [c for c in close.columns if c in px.columns]
    c, a = close[cols], px[cols]
    d = c.shift(1) * (a.pct_change() - c.pct_change())
    d = d.where(d > c.shift(1) * 1e-5, 0.0)          # ignore rounding noise and negatives
    return d.fillna(0.0)


def dividend_cash(trades: pd.DataFrame, close: pd.DataFrame, px: pd.DataFrame | None,
                  held: pd.DataFrame) -> pd.DataFrame:
    """Dividend cash received per day per ticker = shares held at YESTERDAY's
    close x dividend per share. Manual 'dividend' rows replace the estimate for
    that ticker on that day."""
    cash = pd.DataFrame(0.0, index=held.index, columns=held.columns)
    if px is not None:
        dps = dividends_per_share(close, px).reindex(index=held.index, columns=held.columns).fillna(0.0)
        cash = held.shift(1).fillna(0.0) * dps
    for _, r in trades[trades["action"] == "dividend"].iterrows():
        pos = held.index.searchsorted(r["date"])
        if pos < len(held.index):
            if r["ticker"] not in cash:
                cash[r["ticker"]] = 0.0
            cash.iloc[pos, cash.columns.get_loc(r["ticker"])] = r["shares"] * r["price"]
    return cash


def equity_curve(trades: pd.DataFrame, close: pd.DataFrame, px: pd.DataFrame | None = None) -> pd.DataFrame:
    """Daily: value of holdings, dividend cash, fees, money put in, and a time-weighted index.
    Dividends are kept as cash (not reinvested); fees reduce value."""
    if trades.empty:
        return pd.DataFrame()
    other = trades[~trades["action"].isin(["buy", "sell"])]
    trades = trades[trades["action"].isin(["buy", "sell"])]
    if trades.empty:
        return pd.DataFrame()
    first = close.index.searchsorted(trades["date"].min())
    if first >= len(close.index):        # every trade is newer than the latest price we have
        return pd.DataFrame()
    idx = close.index[first:]
    held = pd.DataFrame(0.0, index=idx, columns=sorted(set(trades["ticker"]) & set(close.columns)))
    for _, r in trades.iterrows():
        if r["ticker"] in held:
            pos = idx.searchsorted(r["date"])
            held.iloc[pos:, held.columns.get_loc(r["ticker"])] += r["shares"] * (1 if r["action"] == "buy" else -1)
    held = held.clip(lower=0)
    holdings = (held * close.loc[idx, held.columns].ffill()).sum(axis=1)
    divs = dividend_cash(other, close, px, held).sum(axis=1).cumsum()
    fees = pd.Series(0.0, index=idx)
    for _, r in other[other["action"] == "fee"].iterrows():
        pos = idx.searchsorted(r["date"])
        if pos < len(idx):
            fees.iloc[pos] += r["shares"] * r["price"]
    fees = fees.cumsum()
    value = holdings + divs - fees
    cf = _flows(trades[trades["ticker"].isin(held.columns)], idx)
    # time-weighted: today's return = (value today - money added today) / value yesterday
    prev = value.shift(1)
    r = ((value - cf) / prev - 1).where(prev > EPS, 0.0).fillna(0.0)
    return pd.DataFrame({"value": value, "holdings": holdings, "dividends": divs, "fees": fees,
                         "invested": cf.cumsum(), "flow": cf, "twr": (1 + r).cumprod()})


def same_dollars_into(index_px: pd.Series, flows: pd.Series) -> pd.Series:
    """Value if the same money went into `index_px` on the same days."""
    p = index_px.reindex(flows.index).ffill()
    units = (flows / p).fillna(0).cumsum()
    return units * p


def quarterly(twr: pd.Series, spy: pd.Series | None) -> list[dict]:
    """Time-weighted return per calendar quarter, with SPY over the same days."""
    out = []
    for q, g in twr.groupby(twr.index.to_period("Q")):
        start = twr[twr.index < g.index[0]]
        base = start.iloc[-1] if len(start) else 1.0
        row = {"quarter": str(q), "me": float(g.iloc[-1] / base - 1)}
        if spy is not None:
            s = spy.reindex(twr.index).ffill()
            sb = s[s.index < g.index[0]]
            sbase = sb.iloc[-1] if len(sb) else s.loc[g.index[0]]
            row["spy"] = float(s.loc[g.index[-1]] / sbase - 1)
            row["vs_spy"] = row["me"] - row["spy"]
        out.append(row)
    return out


def build(path: Path, close: pd.DataFrame, px: pd.DataFrame, bench: pd.DataFrame,
          model_curve: pd.Series | None, splits: pd.DataFrame | None = None, demo: bool = False) -> dict:
    """Everything the dashboard needs for the 'My real money' card."""
    trades, errors = load(path)
    out = {"n_trades": int(len(trades)), "errors": errors, "demo": demo, "file": str(Path(path).name)}
    if trades.empty:
        return out
    trades = _adjust_for_splits(trades, splits)
    last = {t: float(close[t].dropna().iloc[-1]) for t in set(trades["ticker"]) if t in close and close[t].notna().any()}
    rows, totals, perr = positions(trades, last)
    out["errors"] += perr
    late = trades[trades["date"] > close.index[-1]]
    if len(late):
        out["errors"].append(f"{len(late)} trade(s) dated after the latest price ({close.index[-1].date()}) — "
                             "they'll be counted once that day's prices are in.")
    eq = equity_curve(trades, close, px)
    if eq.empty:
        return out
    # dividends per ticker (for the positions table) and fees
    bs = trades[trades["action"].isin(["buy", "sell"])]
    idx = eq.index
    held = pd.DataFrame(0.0, index=idx, columns=sorted(set(bs["ticker"]) & set(close.columns)))
    for _, r in bs.iterrows():
        if r["ticker"] in held:
            held.iloc[idx.searchsorted(r["date"]):, held.columns.get_loc(r["ticker"])] += \
                r["shares"] * (1 if r["action"] == "buy" else -1)
    div_by = dividend_cash(trades, close, px, held.clip(lower=0)).sum()
    for row in rows:
        row["dividends"] = float(div_by.get(row["ticker"], 0.0))
    totals["dividends"] = float(eq["dividends"].iloc[-1])
    totals["fees"] = float(eq["fees"].iloc[-1])
    totals["pnl"] = totals["unrealized"] + totals["realized"] + totals["dividends"] - totals["fees"]
    totals["value"] = float(eq["value"].iloc[-1])
    totals["dividends_manual"] = bool((trades["action"] == "dividend").any())
    curves = {"me": eq["value"], "invested": eq["invested"]}
    if totals["dividends"] > 0:
        curves["divs"] = eq["dividends"]
    spy = bench["SPY"] if "SPY" in bench else None
    if spy is not None:
        curves["spy"] = same_dollars_into(spy, eq["flow"])
        totals["spy_pnl"] = float(curves["spy"].iloc[-1] - eq["invested"].iloc[-1])
    if model_curve is not None and len(model_curve):
        curves["model"] = same_dollars_into(model_curve, eq["flow"])
        totals["model_pnl"] = float(curves["model"].iloc[-1] - eq["invested"].iloc[-1])
    totals["invested"] = float(eq["invested"].iloc[-1])
    totals["twr"] = float(eq["twr"].iloc[-1] - 1)
    out["lots"] = tax_lots(trades, last, close.index[-1])
    out.update({"positions": rows, "totals": totals, "quarters": quarterly(eq["twr"], spy),
                "curves": {k: [[d.strftime("%Y-%m-%d"), round(float(v), 2)] for d, v in s.resample("W-FRI").last().dropna().items()]
                           for k, s in curves.items()},
                "first_trade": trades["date"].min().strftime("%Y-%m-%d")})
    return out


def write_demo(path: Path, close: pd.DataFrame) -> None:
    """A few FAKE trades so the card has something to show in --demo mode."""
    idx = close.index
    picks = [("MU", 300, 5), ("NVDA", 250, 4), ("AMD", 200, 6), ("MU", 120, -3), ("AAPL", 90, 2)]
    lines = ["# DEMO trades — fake, generated by run.py --demo. Your real file is state/my_trades.csv.",
             ",".join(COLUMNS)]
    for t, days_ago, n in picks:
        if t not in close:
            continue
        d = idx[-days_ago]
        lines.append(f"{d.date()},{t},{'buy' if n > 0 else 'sell'},{abs(n)},{close[t].loc[d]:.2f},demo")
    if "AAPL" in close and "NVDA" in close:   # manual dividend + fee rows, to show the format
        lines.append(f"{idx[-30].date()},AAPL,dividend,1,0.52,demo: 2 shares x $0.26")
        lines.append(f"{idx[-200].date()},NVDA,dividend,1,0.04,demo: 4 shares x $0.01")
        lines.append(f"{idx[-250].date()},,fee,1,1.00,demo: transfer fee")
    Path(path).write_text("\n".join(lines) + "\n")


# ---------- Tax lots (FIFO), holding periods and wash-sale flags ----------
# NOT tax advice. US-style rules, simplified: FIFO lot matching (most brokers'
# default), "long-term" = held MORE than one year, wash sales flagged only.

def long_term_date(bought) -> pd.Timestamp:
    """First day a lot bought on `bought` counts as long-term (held more than a year):
    the day after the same calendar date next year. 2024-02-29 -> 2025-03-01."""
    return (pd.Timestamp(bought) + pd.DateOffset(years=1)).normalize() + pd.Timedelta(days=1)


def is_long_term(bought, sold) -> bool:
    return pd.Timestamp(sold).normalize() >= long_term_date(bought)


def fifo_sell(lots: list[dict], shares: float, price: float, date) -> tuple[list[dict], list[dict]]:
    """Take `shares` from the oldest lots first. Returns (pieces sold, remaining lots).
    Each piece: {buy_date, shares, cost, proceeds, gain, term, buy_id}. Doesn't mutate `lots`."""
    left, pieces, remaining = shares, [], []
    for lot in lots:
        if left <= EPS:
            remaining.append(dict(lot)); continue
        take = min(lot["shares"], left)
        cost = take * lot["price"]
        pieces.append({"buy_date": lot["date"], "shares": take, "cost": cost, "proceeds": take * price,
                       "gain": take * price - cost, "buy_id": lot["id"],
                       "term": "LT" if is_long_term(lot["date"], date) else "ST"})
        left -= take
        if lot["shares"] - take > EPS:
            remaining.append({**lot, "shares": lot["shares"] - take})
    return pieces, remaining


def tax_lots(trades: pd.DataFrame, last_price: dict, asof=None, soon_days: int = 60) -> dict:
    """Open lots, realized short/long-term gains by year, and wash-sale flags."""
    asof = pd.Timestamp(asof or pd.Timestamp.today()).normalize()
    bs = trades[trades["action"].isin(["buy", "sell"])].reset_index(drop=True)
    book: dict[str, list[dict]] = {}
    sales, wash = [], []
    for i, r in bs.iterrows():
        t, d = r["ticker"], pd.Timestamp(r["date"])
        if r["action"] == "buy":
            book.setdefault(t, []).append({"id": i, "date": d, "shares": r["shares"], "price": r["price"]})
            continue
        held = sum(l["shares"] for l in book.get(t, []))
        if r["shares"] > held + EPS:
            continue                                        # positions() already reports this
        pieces, book[t] = fifo_sell(book.get(t, []), r["shares"], r["price"], d)
        gain = sum(p["gain"] for p in pieces)
        sale = {"date": d.strftime("%Y-%m-%d"), "ticker": t, "shares": r["shares"], "price": r["price"],
                "gain": gain, "st": sum(p["gain"] for p in pieces if p["term"] == "ST"),
                "lt": sum(p["gain"] for p in pieces if p["term"] == "LT")}
        sales.append(sale)
        if gain < -EPS:                                     # a loss: any OTHER buy within 30 days either side?
            used = {p["buy_id"] for p in pieces}
            near = [b for j, b in bs.iterrows() if b["ticker"] == t and b["action"] == "buy" and j not in used
                    and abs((pd.Timestamp(b["date"]) - d).days) <= 30]
            if near:
                wash.append({"date": sale["date"], "ticker": t, "loss": gain,
                             "buys": [pd.Timestamp(b["date"]).strftime("%Y-%m-%d") for b in near],
                             "text": f"{t}: sold at a {money(gain)} loss on {sale['date']} and bought within 30 days "
                                     f"({', '.join(pd.Timestamp(b['date']).strftime('%Y-%m-%d') for b in near)}). "
                                     f"This may be a wash sale: the loss may not be deductible yet."})
    by_year: dict[str, dict] = {}
    for s in sales:
        y = by_year.setdefault(s["date"][:4], {"st": 0.0, "lt": 0.0})
        y["st"] += s["st"]; y["lt"] += s["lt"]
    open_lots = []
    for t, lots in book.items():
        p = last_price.get(t)
        for l in lots:
            if l["shares"] <= EPS:
                continue
            ltd = long_term_date(l["date"])
            days_to_lt = (ltd - asof).days
            open_lots.append({"ticker": t, "date": l["date"].strftime("%Y-%m-%d"), "shares": l["shares"],
                              "price": l["price"], "cost": l["shares"] * l["price"],
                              "value": l["shares"] * p if p is not None else None,
                              "gain": (l["shares"] * (p - l["price"])) if p is not None else None,
                              "days_held": int((asof - l["date"]).days),
                              "term": "LT" if asof >= ltd else "ST",
                              "lt_date": ltd.strftime("%Y-%m-%d"),
                              "lt_soon": 0 < days_to_lt <= soon_days})
    open_lots.sort(key=lambda l: (l["ticker"], l["date"]))
    return {"open": open_lots, "sales": sales, "by_year": dict(sorted(by_year.items())), "wash": wash,
            "realized": sum(s["gain"] for s in sales),
            "unrealized": sum(l["gain"] for l in open_lots if l["gain"] is not None)}


def preview_sell(open_lots: list[dict], ticker: str, shares: float, price: float, asof) -> dict:
    """What FIFO would sell if you sold `shares` of `ticker` at `price` on `asof`."""
    lots = [{"id": i, "date": pd.Timestamp(l["date"]), "shares": l["shares"], "price": l["price"]}
            for i, l in enumerate(open_lots) if l["ticker"] == ticker]
    have = sum(l["shares"] for l in lots)
    pieces, _ = fifo_sell(lots, min(shares, have), price, asof)
    return {"ticker": ticker, "shares": min(shares, have), "capped": shares > have + EPS,
            "st": sum(p["gain"] for p in pieces if p["term"] == "ST"),
            "lt": sum(p["gain"] for p in pieces if p["term"] == "LT"),
            "pieces": [{**p, "buy_date": p["buy_date"].strftime("%Y-%m-%d")} for p in pieces]}


def money(v: float) -> str:
    return ("-$" if v < 0 else "$") + f"{abs(v):,.2f}"
