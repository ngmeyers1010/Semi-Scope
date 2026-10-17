"""
Synthetic data in the exact SEC XBRL format, for testing without internet.
NOT real market data — the dashboard shows a DEMO banner when this is used.
"""
import numpy as np
import pandas as pd

from fundamentals import build_series


def _fact(start, end, val, filed, form):
    f = {"end": end.strftime("%Y-%m-%d"), "val": float(val),
         "filed": filed.strftime("%Y-%m-%d"), "form": form}
    if start is not None:
        f["start"] = start.strftime("%Y-%m-%d")
    return f


def _company(rng, fy_end_month, first_year, last_date):
    base = rng.uniform(1e9, 2e10)
    phase = rng.uniform(0, 2 * np.pi)
    trend = rng.uniform(0.005, 0.04)
    rev_old, rev_new, cogs, inv = [], [], [], []
    opinc, rd, cfo, capex = [], [], [], []
    xq = {}  # quarter end -> (op income, R&D, operating cash flow, capex)
    cycle_by_q = {}
    for fy in range(first_year, last_date.year + 2):
        fy_end = pd.Timestamp(year=fy, month=fy_end_month, day=1) + pd.offsets.MonthEnd(0)
        fy_start = fy_end - pd.DateOffset(years=1) + pd.Timedelta(days=1)
        q_vals = []
        for qi in range(4):
            qs = fy_start + pd.DateOffset(months=3 * qi)
            qe = (qs + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
            t = (qe.year - 2010) * 4 + qe.month / 3
            cyc = np.sin(t / 3.0 + phase)
            cycle_by_q[qe] = cyc
            r = base * np.exp(trend * t + 0.18 * cyc + rng.normal(0, 0.03))
            gm = 0.45 + 0.08 * cyc + rng.normal(0, 0.01)
            c = r * (1 - gm)
            dio = 100 - 25 * cyc + rng.normal(0, 4)
            q_vals.append((qs, qe, r, c, c / 91 * dio))
            # deterministic extras (no rng draws, so other demo numbers stay stable)
            xq[qe] = (r * (0.15 + 0.10 * cyc), r * 0.15,
                      r * (0.22 + 0.08 * cyc), r * (0.08 + 0.03 * cyc))
        for qi, (qs, qe, r, c, iv) in enumerate(q_vals):
            if qi < 3:
                filed = qe + pd.Timedelta(days=35)
                if filed > last_date:
                    continue
                tags = rev_old if qe.year < 2018 else rev_new
                tags.append(_fact(qs, qe, r, filed, "10-Q"))
                # restated comparative one year later (should be ignored)
                tags.append(_fact(qs, qe, r * 1.03, filed + pd.DateOffset(years=1), "10-Q"))
                cogs.append(_fact(qs, qe, c, filed, "10-Q"))
                op, rdv, _, _ = xq[qe]
                opinc.append(_fact(qs, qe, op, filed, "10-Q"))
                rd.append(_fact(qs, qe, rdv, filed, "10-Q"))
                # cash flow is reported YEAR-TO-DATE in 10-Qs
                ytd_cfo = sum(xq[v[1]][2] for v in q_vals[:qi + 1])
                ytd_cap = sum(xq[v[1]][3] for v in q_vals[:qi + 1])
                cfo.append(_fact(fy_start, qe, ytd_cfo, filed, "10-Q"))
                capex.append(_fact(fy_start, qe, ytd_cap, filed, "10-Q"))
            else:
                filed = qe + pd.Timedelta(days=55)
                if filed > last_date:
                    continue
            inv.append(_fact(None, qe, iv, filed, "10-Q" if qi < 3 else "10-K"))
        filed_k = fy_end + pd.Timedelta(days=55)
        if filed_k <= last_date:
            tags = rev_old if fy_end.year < 2018 else rev_new
            tags.append(_fact(fy_start, fy_end, sum(v[2] for v in q_vals), filed_k, "10-K"))
            cogs.append(_fact(fy_start, fy_end, sum(v[3] for v in q_vals), filed_k, "10-K"))
            for lst, j in ((opinc, 0), (rd, 1), (cfo, 2), (capex, 3)):
                lst.append(_fact(fy_start, fy_end, sum(xq[v[1]][j] for v in q_vals), filed_k, "10-K"))
    facts = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": rev_old}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": rev_new}},
        "CostOfRevenue": {"units": {"USD": cogs}},
        "InventoryNet": {"units": {"USD": inv}},
        "OperatingIncomeLoss": {"units": {"USD": opinc}},
        "ResearchAndDevelopmentExpense": {"units": {"USD": rd}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": cfo}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": capex}},
    }}}
    return facts, cycle_by_q, phase


# Fixed end date so the demo is identical on every day you run it (otherwise the
# random series get longer each day and every number shifts). Bump it occasionally.
DEMO_END = "2026-10-13"


def generate(tickers, benchmarks, backtest_start, seed=7, return_market=False, end=None, raw_facts=None):
    """raw_facts: optional dict that receives each ticker's raw SEC-format JSON (used by
    tests/fixtures/live_sim.py to fake the SEC download). Doesn't change any numbers."""
    rng = np.random.default_rng(seed)
    last = pd.Timestamp(end or DEMO_END)
    idx = pd.bdate_range(pd.Timestamp(backtest_start) - pd.DateOffset(years=1), last)
    mkt = rng.normal(0.0004, 0.011, len(idx))
    all_series, px, splits = {}, {}, {}
    for k, t in enumerate(tickers):
        fy_month = [12, 12, 1, 6, 9, 12][k % 6]
        facts, cyc, phase = _company(rng, fy_month, 2009, last)
        # price drift follows the cycle's slope with a lead, so the factors have
        # something to find
        tt = ((idx.year - 2010) * 4 + idx.month / 3 + 0.5).values
        slope = np.cos(tt / 3.0 + phase)
        r = 1.3 * mkt + 0.0009 * slope + rng.normal(0, 0.018, len(idx))
        start_i = 0 if k % 7 else rng.integers(200, 1500)  # some IPO later
        series = 50 * np.exp(np.cumsum(r))
        series[:start_i] = np.nan
        px[t] = series

        # cover-page share counts; every 4th stock does a 10:1 split in 2024
        sp = pd.Series(0.0, index=idx)
        split_date = None
        if k % 4 == 0:
            split_date = idx[idx >= pd.Timestamp("2024-06-10")][0]
            sp[split_date] = 10.0
        splits[t] = sp
        rev0 = facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["val"]
        n0 = rev0 * 4 * rng.uniform(2, 8) / 50   # shares so P/S starts ~2-8x
        filed = sorted({f["filed"] for tag in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax")
                        for f in facts["facts"]["us-gaap"][tag]["units"]["USD"]})
        dei = []
        for i, f in enumerate(filed):
            fd = pd.Timestamp(f)
            raw_n = n0 * (1 - 0.002 * i)                 # slow buyback
            if split_date is not None and fd >= split_date:
                raw_n *= 10                              # post-split raw count
            dei.append({"end": (fd - pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
                        "val": raw_n, "filed": f, "accn": f"acc-{t}-{i}"})
        facts["facts"]["dei"] = {"EntityCommonStockSharesOutstanding": {"units": {"shares": dei}}}
        if raw_facts is not None:
            raw_facts[t] = facts

        if k % 10 != 9:  # every 10th stock acts like a foreign filer (no SEC data)
            all_series[t] = build_series(facts, sp)
    prices = pd.DataFrame(px, index=idx)
    bench = pd.DataFrame({
        benchmarks[0]: 100 * np.exp(np.cumsum(mkt)),
        benchmarks[1]: 100 * np.exp(np.cumsum(1.3 * mkt + rng.normal(0, 0.004, len(idx)))),
    }, index=idx)
    if return_market:
        return all_series, prices, bench, prices.copy(), pd.DataFrame(splits)
    return all_series, prices, bench
