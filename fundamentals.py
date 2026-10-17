"""
Turn raw SEC XBRL "company facts" into clean, point-in-time quarterly series.

Key ideas
- Every value carries the date it was FILED with the SEC. When we score a stock
  as of some date, we only use values filed on or before that date. This is what
  prevents look-ahead bias in the backtest.
- We keep the ORIGINALLY reported value for each quarter (later restatements
  would not have been known at the time).
- Companies only report Q1-Q3 as 3-month numbers; Q4 is derived as
  (full fiscal year) - (Q1 + Q2 + Q3), stamped with the 10-K filing date.
"""
from __future__ import annotations

import pandas as pd

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueGoodsNet",
]
COGS_TAGS = [
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "CostOfGoodsSold",
    "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
]
GROSS_PROFIT_TAGS = ["GrossProfit"]
INVENTORY_TAGS = ["InventoryNet"]
OPINC_TAGS = ["OperatingIncomeLoss"]
RD_TAGS = ["ResearchAndDevelopmentExpense",
           "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"]
CFO_TAGS = ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"]


def _facts_for(facts: dict, tag: str) -> list[dict]:
    """The USD fact list for one us-gaap tag (empty if the company never used it)."""
    try:
        units = facts["facts"]["us-gaap"][tag]["units"]
    except KeyError:
        return []
    return units.get("USD", [])


def _duration_quarters(facts: dict, tags: list[str]) -> pd.DataFrame:
    """Quarterly (3-month) values for a flow item, merged across tag names."""
    rows = []
    for priority, tag in enumerate(tags):
        for f in _facts_for(facts, tag):
            if "start" not in f or f.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                continue
            rows.append({"start": f["start"], "end": f["end"], "val": f["val"],
                         "filed": f["filed"], "prio": priority})
    if not rows:
        return pd.DataFrame(columns=["end", "val", "filed"])
    df = pd.DataFrame(rows)
    for c in ("start", "end", "filed"):
        df[c] = pd.to_datetime(df[c])
    df["days"] = (df["end"] - df["start"]).dt.days
    # earliest filing wins (original report); tag priority breaks ties
    df = df.sort_values(["filed", "prio"]).drop_duplicates(["start", "end"], keep="first")

    q = df[df["days"].between(80, 100)][["start", "end", "val", "filed"]].copy()
    annual = df[df["days"].between(350, 380)]

    derived = []
    for _, a in annual.iterrows():
        inside = q[(q["start"] >= a["start"] - pd.Timedelta(days=7)) & (q["end"] <= a["end"])]
        has_q4 = (abs(inside["end"] - a["end"]).dt.days <= 7).any()
        if has_q4:
            continue
        first3 = inside.sort_values("end").drop_duplicates("end").tail(3)
        if len(first3) == 3:
            derived.append({"start": first3["end"].max() + pd.Timedelta(days=1),
                            "end": a["end"], "val": a["val"] - first3["val"].sum(),
                            "filed": max(a["filed"], first3["filed"].max())})
    if derived:
        q = pd.concat([q, pd.DataFrame(derived)], ignore_index=True)
    q = q.sort_values(["end", "filed"]).drop_duplicates("end", keep="first")
    return q[["end", "val", "filed"]].reset_index(drop=True)


def _ytd_quarters(facts: dict, tags: list[str]) -> pd.DataFrame:
    """Quarterly values for items reported YEAR-TO-DATE (cash-flow statement).

    10-Qs report cash flow as 3-, 6-, 9-month YTD totals and the 10-K as the full
    year, all sharing the fiscal-year start date. Within each start date we
    de-cumulate: Q2 = 6mo - 3mo, Q3 = 9mo - 6mo, Q4 = 12mo - 9mo. Each derived
    quarter is stamped with the filing date of the later YTD report.
    """
    rows = []
    for priority, tag in enumerate(tags):
        for f in _facts_for(facts, tag):
            if "start" not in f or f.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                continue
            rows.append({"start": f["start"], "end": f["end"], "val": f["val"],
                         "filed": f["filed"], "prio": priority})
    if not rows:
        return pd.DataFrame(columns=["end", "val", "filed"])
    df = pd.DataFrame(rows)
    for c in ("start", "end", "filed"):
        df[c] = pd.to_datetime(df[c])
    df = df.sort_values(["filed", "prio"]).drop_duplicates(["start", "end"], keep="first")
    out = []
    for start, g in df.groupby("start"):
        prev_val, prev_end = 0.0, start - pd.Timedelta(days=1)
        for _, r in g.sort_values("end").iterrows():
            span = (r["end"] - prev_end).days
            if 80 <= span <= 100:
                out.append({"end": r["end"], "val": r["val"] - prev_val, "filed": r["filed"]})
            elif span > 100:
                break  # gap in the YTD chain; can't de-cumulate safely
            prev_val, prev_end = r["val"], r["end"]
    if not out:
        return pd.DataFrame(columns=["end", "val", "filed"])
    q = pd.DataFrame(out).sort_values(["end", "filed"]).drop_duplicates("end", keep="first")
    return q.reset_index(drop=True)


def _instant(facts: dict, tags: list[str]) -> pd.DataFrame:
    """Point-in-time balance-sheet values (e.g., inventory)."""
    rows = []
    for priority, tag in enumerate(tags):
        for f in _facts_for(facts, tag):
            if f.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                continue
            rows.append({"end": f["end"], "val": f["val"], "filed": f["filed"], "prio": priority})
    if not rows:
        return pd.DataFrame(columns=["end", "val", "filed"])
    df = pd.DataFrame(rows)
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    df = df.sort_values(["filed", "prio"]).drop_duplicates("end", keep="first")
    return df[["end", "val", "filed"]].sort_values("end").reset_index(drop=True)


def split_factor_after(splits: pd.Series | None, date: pd.Timestamp) -> float:
    """Product of split ratios strictly after `date` (1.0 if none)."""
    if splits is None or len(splits) == 0:
        return 1.0
    s = splits[(splits.index > date) & (splits > 0)]
    return float(s.prod()) if len(s) else 1.0


def shares_series(facts: dict, splits: pd.Series | None = None) -> pd.DataFrame:
    """Cover-page shares outstanding (dei), summed across share classes, in
    TODAY'S split units so they line up with split-adjusted prices.

    Multiplying by future split ratios is only a unit conversion: it gives the
    exact historical market cap when paired with split-adjusted prices, so it
    leaks no future information."""
    try:
        rows = facts["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
    except KeyError:
        return pd.DataFrame(columns=["end", "val", "filed"])
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["end", "val", "filed"])
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    key = "accn" if "accn" in df else "filed"
    g = df.groupby([key, "end"], as_index=False).agg(val=("val", "sum"), filed=("filed", "min"))
    g = g.sort_values("filed").drop_duplicates("end", keep="first")
    g["val"] = [v * split_factor_after(splits, e) for v, e in zip(g["val"], g["end"])]
    return g[["end", "val", "filed"]].sort_values("end").reset_index(drop=True)


def build_series(facts: dict, splits: pd.Series | None = None) -> dict[str, pd.DataFrame]:
    """Dict of point-in-time series: revenue, cogs, inventory, shares."""
    rev = _duration_quarters(facts, REVENUE_TAGS)
    cogs = _duration_quarters(facts, COGS_TAGS)
    if cogs.empty:
        gp = _duration_quarters(facts, GROSS_PROFIT_TAGS)
        if not gp.empty and not rev.empty:
            m = rev.merge(gp, on="end", suffixes=("_r", "_g"))
            cogs = pd.DataFrame({"end": m["end"], "val": m["val_r"] - m["val_g"],
                                 "filed": m[["filed_r", "filed_g"]].max(axis=1)})
    return {"revenue": rev, "cogs": cogs, "inventory": _instant(facts, INVENTORY_TAGS),
            "opinc": _duration_quarters(facts, OPINC_TAGS),
            "rd": _duration_quarters(facts, RD_TAGS),
            "cfo": _ytd_quarters(facts, CFO_TAGS),
            "capex": _ytd_quarters(facts, CAPEX_TAGS),
            "shares": shares_series(facts, splits)}
