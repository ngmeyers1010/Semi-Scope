"""
Hand-entered quarterly results for foreign filers (ASML, TSMC, ...).

The SEC feed only has 10-Q/10-K numbers. Foreign companies file a 20-F once a year,
so SemiScope scored them on price alone (2 factors, below MIN_FACTORS, never picked).
This reads state/foreign_fundamentals.csv instead (edit it on GitHub, no Python needed):

    ticker,quarter_end,reported,revenue,cost_of_sales,inventory,operating_income,rd,op_cash_flow,capex,units,source
    TSM,2026-09-30,2026-10-15,1494.24,501.86,427.75,876.45,88.98,919.77,443.21,TWD bn,3Q26 Management Report

Rules
- One row per quarter, 3-MONTH numbers (not year-to-date).
- reported = the day the results became public. It does the job of the SEC "filed" date:
  scoring as of day D only sees rows reported BEFORE D, so the backtest can't peek.
- Any currency or unit, as long as each company keeps the same one. The factors are growth
  rates and margins, so the currency cancels. units and source are notes for you.
- Leave a cell blank if the company doesn't report it. Lines starting with # are skipped.
- Numbers can be typed the way statements print them: "1,494.24" or "(413.3)".
  cost_of_sales, rd and capex are always stored as positive amounts;
  operating_income and op_cash_flow keep their sign (they can really be negative).
- No share counts, so the sales-yield factor stays blank for these stocks.
Bad lines are reported, never fatal (same idea as mystocks.py).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

PATH = Path(__file__).parent / "state" / "foreign_fundamentals.csv"

# CSV column -> series name used by fundamentals.build_series() and factors.py
SERIES = {"revenue": "revenue", "cost_of_sales": "cogs", "inventory": "inventory",
          "operating_income": "opinc", "rd": "rd", "op_cash_flow": "cfo", "capex": "capex"}
ALWAYS_POSITIVE = {"cost_of_sales", "rd", "capex"}
REQUIRED = ("ticker", "quarter_end", "reported", "revenue")
MAX_GAP_DAYS = 100     # quarter ends further apart than this: a quarter is probably missing


def number(text: str | None) -> float | None:
    """'1,494.24' -> 1494.24, '(251.9)' -> -251.9, '' -> None. Raises ValueError on junk."""
    s = (text or "").strip().replace(",", "").replace("\u2212", "-")
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    v = float(s.strip("()"))
    return -v if negative else v


def _date(text: str | None) -> pd.Timestamp | None:
    try:
        d = pd.Timestamp((text or "").strip())
    except (ValueError, TypeError):
        return None
    return None if pd.isna(d) else d.normalize()


def parse(path: Path = PATH) -> tuple[list[dict], list[str]]:
    """(rows, problems). A missing file gives ([], [])."""
    path = Path(path)
    if not path.exists():
        return [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = [(h or "").strip() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            return [], [f"Header is missing {', '.join(missing)}. The first line should start: "
                        f"{','.join(REQUIRED)},cost_of_sales,..."]
        reader.fieldnames = header
        rows, problems, seen = [], [], set()
        for raw in reader:
            r = {k: (v or "").strip() for k, v in raw.items() if isinstance(k, str) and isinstance(v, (str, type(None)))}
            t = r.get("ticker", "").upper().lstrip("$")
            if not t or t.startswith("#"):
                continue
            where = f"Line {reader.line_num} ({t})"
            end, rep = _date(r.get("quarter_end")), _date(r.get("reported"))
            if end is None or rep is None:
                problems.append(f"{where}: dates should look like 2026-09-30 — skipped")
                continue
            if rep <= end:
                problems.append(f"{where}: reported {rep.date()} is not after quarter_end {end.date()} — skipped")
                continue
            vals, unreadable = {}, []
            for col in SERIES:
                try:
                    v = number(r.get(col))
                except ValueError:
                    unreadable.append(col)
                    v = None
                if v is not None and col in ALWAYS_POSITIVE:
                    v = abs(v)
                vals[col] = v
            if unreadable:
                problems.append(f"{where}: couldn't read {', '.join(unreadable)} — left blank")
            if vals["revenue"] is None:
                problems.append(f"{where}: no revenue — skipped")
                continue
            if (t, end) in seen:
                problems.append(f"{where}: {t} {end.date()} is listed twice — kept the first one")
                continue
            seen.add((t, end))
            rows.append({"ticker": t, "end": end, "filed": rep, **vals})
    return rows, problems


def load(path: Path = PATH) -> tuple[dict[str, dict[str, pd.DataFrame]], list[str]]:
    """({ticker: {series: DataFrame(end, val, filed)}}, problems).

    Same shape as fundamentals.build_series(), so factors.py, sanity.py and the backtest
    treat these stocks exactly like SEC filers (minus share counts)."""
    rows, problems = parse(path)
    out: dict[str, dict[str, pd.DataFrame]] = {}
    if not rows:
        return out, problems
    df = pd.DataFrame(rows)
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    for t, g in df.groupby("ticker", sort=True):
        g = g.sort_values("end")
        ends = list(g["end"])
        for a, b in zip(ends, ends[1:]):
            if (b - a).days > MAX_GAP_DAYS:
                problems.append(f"{t}: {(b - a).days} days between {a.date()} and {b.date()} — a quarter may be missing")
        out[t] = {}
        for col, name in SERIES.items():
            s = pd.DataFrame({"end": g["end"], "val": pd.to_numeric(g[col], errors="coerce").astype(float),
                              "filed": g["filed"]})
            out[t][name] = s.dropna(subset=["val"]).reset_index(drop=True)
    return out, problems
