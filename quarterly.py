"""
Quarterly report cards: one Markdown file per calendar quarter, written once
when the quarter ends and never rewritten (append-only, like the paper log).

    reports/2026Q4.md

build_report() is a pure function of the dashboard data, so it's easy to test.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def quarter_of(d) -> str:
    """'2026Q1' for any date in Jan-Mar 2026 (2026-03-31 included)."""
    return str(pd.Timestamp(d).to_period("Q"))


def bounds(q: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """First and last calendar day of a quarter like '2026Q1'."""
    p = pd.Period(q, freq="Q")
    return p.start_time.normalize(), p.end_time.normalize()


def completed_quarters(first, asof) -> list[str]:
    """Quarters that have fully ended by `asof`, from the one containing `first`."""
    last_done = pd.Timestamp(asof).to_period("Q") - 1
    start = pd.Timestamp(first).to_period("Q")
    return [str(p) for p in pd.period_range(start, last_done, freq="Q")] if start <= last_done else []


def quarter_returns(series: pd.Series) -> dict[str, float]:
    """Calendar-quarter returns from a daily value curve: last value in the
    quarter / last value before it - 1 (first quarter starts at the first value)."""
    s = series.dropna()
    out, prev = {}, None
    for q, g in s.groupby(s.index.to_period("Q")):
        base = prev if prev is not None else g.iloc[0]
        out[str(q)] = float(g.iloc[-1] / base - 1)
        prev = g.iloc[-1]
    return out


def _pct(v) -> str:
    return "—" if v is None else f"{v:+.1%}"


def build_report(data: dict, q: str) -> str:
    """Markdown report card for quarter `q` (e.g. '2026Q1')."""
    lo, hi = bounds(q)
    in_q = lambda d: lo <= pd.Timestamp(d) <= hi
    qr = data.get("quarter_returns", {})
    get = lambda k: qr.get(k, {}).get(q)
    live = get("paper") is not None
    model, spy, soxx = (get("paper") if live else get("strategy")), get("SPY"), get("SOXX")
    L = [f"# SemiScope report card: {q}", "",
         f"{lo.date()} to {hi.date()} · generated {pd.Timestamp.now('UTC'):%Y-%m-%d}", ""]

    # verdict
    mine = next((r for r in (data.get("my_trades") or {}).get("quarters", []) if r["quarter"] == q), None)
    v = []
    if model is not None and spy is not None:
        v.append(f"{'Model' if live else 'Model (backtest, not live)'} "
                 f"{'beat' if model > spy else 'trailed'} SPY by {abs(model - spy):.1%}")
    if mine and model is not None:
        v.append(f"you {'beat' if mine['me'] > model else 'trailed'} the model by {abs(mine['me'] - model):.1%}")
    L += [f"**Verdict:** {'; '.join(v)}." if v else "**Verdict:** not enough data for this quarter.", ""]

    # performance table
    L += ["## Returns this quarter", "", "| | Return | vs SPY |", "|---|---:|---:|"]
    rows = [("Model paper portfolio" if live else "Model (backtest; paper not started)", model),
            ("S&P 500 (SPY)", spy), ("Semis ETF (SOXX)", soxx)]
    if mine:
        rows.insert(1, ("**You (real trades, time-weighted)**", mine["me"]))
    for name, r in rows:
        L.append(f"| {name} | {_pct(r)} | {'—' if r is None or spy is None or name.startswith('S&P') else _pct(r - spy)} |")
    L.append("")

    # picks held during the quarter
    L += ["## Picks held", ""]
    entries = [e for e in ((data.get("paper") or {}).get("entries") or []) if pd.Timestamp(e["date"]) <= hi]
    if entries:
        active = [e for e in entries if in_q(e["date"])] or entries[-1:]
        for e in active:
            L.append(f"- **Paper picks from {e['date']}** ({e['reason']}): {', '.join(e['picks'])}")
    else:
        bt = [b for b in data.get("backtest", {}).get("quarters", []) if pd.Timestamp(b["date"]) <= hi
              and pd.Timestamp(b["end"]) >= lo]
        if bt:
            L.append("_No live paper picks yet. Backtest picks shown instead (not proof):_")
            L.append("")
            for b in bt:
                rets = ", ".join(f"{t} {_pct(b['pick_returns'].get(t))}" for t in b["picks"])
                L.append(f"- {b['date']} → {b['end']}: {rets} · portfolio {_pct(b['return'])}")
        else:
            L.append("- No picks recorded for this quarter.")
    L.append("")

    # your trades
    L += ["## Your real trades", ""]
    if mine:
        L.append(f"- Time-weighted return {_pct(mine['me'])} vs SPY {_pct(mine.get('spy'))} "
                 f"({_pct(mine.get('vs_spy'))}).")
    else:
        L.append("- No real trades logged for this quarter (add them in `state/my_trades.csv`).")
    L.append("")

    # significance
    conf = data.get("confidence") or {}
    cb = conf.get("paper") or conf.get("backtest")
    if cb and cb.get("t") is not None:
        src = "Paper portfolio" if conf.get("paper") else "Backtest (in-sample)"
        L += ["## Is the edge real?", "",
              f"- {src}: **{cb['verdict']}**. {cb.get('explain', '')}", ""]

    # factors
    L += ["## Which stats worked", ""]
    ic = (data.get("research") or {}).get("ic", {})
    labels = {f: c["label"] for f, c in (data.get("factors") or {}).items()}
    got = []
    for f, pts in ic.items():
        vals = [v for d, v in pts if in_q(d) and v is not None]
        if vals:
            got.append((f, sum(vals) / len(vals)))
    if got:
        got.sort(key=lambda x: -x[1])
        L += ["Rank correlation between each stat and the next quarter's returns, for rebalances in this quarter "
              "(above 0 = it pointed the right way).", "", "| Stat | IC |", "|---|---:|"]
        L += [f"| {'**Composite score**' if f == 'score' else labels.get(f, f)} | {v:+.3f} |" for f, v in got]
    else:
        L.append("- No completed rebalance in this quarter yet (IC needs the following quarter's returns).")
    L.append("")

    # cycle
    gh = dict((data.get("cycle") or {}).get("growth_history", []))
    prev_q = str(pd.Period(q, freq="Q") - 1)
    if q in gh or prev_q in gh:
        L += ["## Chip cycle", "",
              f"- Median revenue growth (YoY) of the universe: {_pct(gh.get(prev_q))} last quarter → {_pct(gh.get(q))} this quarter.",
              "  (Companies report 1–2 months after quarter end, so the latest figure can lag.)", ""]

    # alerts
    al = [a for a in data.get("alert_log", []) if in_q(a["date"])]
    L += ["## Alerts this quarter", ""]
    L += [f"- {a['date']}: {a['text']}" for a in al] or ["- None."]
    L += ["", "_Research tool, not financial advice._", ""]
    return "\n".join(L)


def write_new(data: dict, out_dir: Path, quarters: list[str]) -> list[str]:
    """Write reports for quarters that don't have one yet. Never overwrites."""
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for q in quarters:
        p = out_dir / f"{q}.md"
        if not p.exists():
            p.write_text(build_report(data, q))
            made.append(q)
    return made


def load_all(out_dir: Path) -> list[dict]:
    """All saved reports, newest first, for the dashboard."""
    if not out_dir.exists():
        return []
    return [{"quarter": p.stem, "markdown": p.read_text()} for p in sorted(out_dir.glob("[0-9][0-9][0-9][0-9]Q[1-4].md"), reverse=True)]
