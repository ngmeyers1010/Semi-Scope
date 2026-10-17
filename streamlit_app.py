"""
SemiScope, the Streamlit version: your own app to learn on.

Run it:   pip install -r requirements-app.txt
          streamlit run streamlit_app.py
Then open the link it prints (usually http://localhost:8501).

Streamlit re-runs this whole file top to bottom every time you click something.
So think of it as a script that draws the page, not a program that waits.
The data-shaping functions at the top don't use Streamlit at all, which means
the tests can check them without a browser.
"""
import json
from pathlib import Path

import pandas as pd

import orders                                                # the same "Invest $X" math the dashboard uses
import explain                                               # "why does A rank above B?"
import valuation                                             # "cheap vs its own history" labels

import os
# the file run.py writes (set SEMISCOPE_DATA=path/to/other.json to try a different one)
DATA = Path(os.environ.get("SEMISCOPE_DATA") or Path(__file__).parent / "docs" / "data.json")


# ---------- 1. Pure helpers: plain Python + pandas, no Streamlit ----------
def load_data(path: Path = DATA) -> dict:
    """Read data.json into a Python dict. The file is stored compactly (see slim.py), so
    unpack the time series and merge back the per-stock details from detail.json."""
    import slim
    data = slim.unpack(json.loads(path.read_text()))
    detail = path.parent / "detail.json"
    return slim.merge(data, json.loads(detail.read_text())) if detail.exists() else data


def rank_label(rec: dict, in_universe: bool = True) -> str:
    """'#3' for a ranked stock. '≈#7' when it only "would" rank: a watchlist stock, or a
    foreign filer (ASML, TSM) with too few stats to be ranked, which is never picked."""
    if rec.get("rank") is not None:
        return f"#{int(rec['rank'])}"
    if rec.get("would_rank") is not None:
        return f"≈#{int(rec['would_rank'])}" + (" (price only)" if in_universe else "")
    return "—"


def rankings_table(data: dict) -> pd.DataFrame:
    """One row per stock, best score first. Unscored stocks (no score) go last."""
    df = pd.DataFrame(data["rankings"])                     # list of dicts -> table
    df["shown_rank"] = [rank_label(r) for r in data["rankings"]]
    # P/S percentile vs the stock's own 5 years (0 = cheapest it's been). Missing -> None.
    df["ps_pct"] = [(r.get("valuation") or {}).get("pct") for r in data["rankings"]]
    df = df[["shown_rank", "ticker", "name", "group", "score", "ret_3m", "gross_margin", "ps_pct"]]
    df = df.rename(columns={"shown_rank": "rank"})
    return df.sort_values("score", ascending=False, na_position="last").reset_index(drop=True)


def groups_table(data: dict) -> pd.DataFrame:
    """Industry groups, leader first: return vs SOXX over 1/3/6 months, breadth, and how many
    of the model's top picks are in each group. Empty table if data.json has no groups."""
    rows = (data.get("groups") or {}).get("groups") or []
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    cols = {"group": "Group", "rel_1m": "1m vs SOXX", "rel_3m": "3m vs SOXX", "rel_6m": "6m vs SOXX",
            "breadth": "Breadth", "in_top": "In top 10"}
    return df[[c for c in cols if c in df]].rename(columns=cols)


def diverging_color(v) -> str:
    """CSS background for one cell: blue when ahead of SOXX, red when behind, stronger = bigger.
    Written by hand (no matplotlib) so you can see how a heat map works."""
    if v is None or pd.isna(v):
        return ""
    strength = min(abs(v) / 0.15, 1.0)                       # 15 points ahead/behind = full color
    rgb = "42,120,214" if v > 0 else "227,73,72"
    return f"background-color: rgba({rgb},{0.15 + 0.45 * strength:.2f})"


def valuation_view(rec: dict) -> dict | None:
    """{'pct', 'text', 'frac'} for the "cheap vs its own history" gauge, or None.
    Reuses valuation.label/ordinal so the words match the website exactly."""
    v = rec.get("valuation")
    if not v:
        return None
    if v.get("pct") is None:
        return {"pct": None, "frac": None,
                "text": f"P/S {v['ps']:.2f}×: {valuation.label(None)} (needs 2 years) to call it cheap or pricey."}
    return {"pct": v["pct"], "frac": min(max(v["pct"] / 100, 0.0), 1.0),
            "text": f"P/S {v['ps']:.2f}×, {valuation.ordinal(v['pct'])} percentile of its own 5-year range: "
                    f"{valuation.label(v['pct'])}."}


def steady_view(data: dict) -> dict | None:
    """The "Is the edge steady?" numbers: rolling 1-year excess vs SPY (as a % series),
    plus 4 headline numbers and the plain-English read. None if not available yet."""
    st_ = data.get("steady") or {}
    s = st_.get("paper") if (st_.get("paper") or {}).get("available") else st_.get("backtest")
    if not s or not s.get("available") or not s.get("rolling"):
        return None
    series = pd.Series({pd.Timestamp(d): v * 100 for d, v in s["rolling"]}, name="1-yr return minus SPY (%)")
    ir = s.get("info_ratio")
    return {
        "series": series, "read": s.get("read", ""), "label": s.get("label", "backtest"),
        "metrics": [("Beat SPY", f"{s['pct_windows_beat']:.0%}", "of 1-year windows"),
                    ("Information ratio", "—" if ir is None else f"{ir:.2f}", "0.5+ is good"),
                    ("Tracking error", f"{s['tracking_error']:.1%}", "typical yearly gap vs SPY"),
                    ("Worst year", f"{s['worst']['excess']:+.0%}", f"{s['worst']['start'][:7]} → {s['worst']['end'][:7]}")],
    }


def earnings_table(data: dict) -> pd.DataFrame:
    """Upcoming earnings for your stocks and the picks: date, typical next-day move, price band.
    Empty table if data.json has no calendar (older file) or no dates are known yet."""
    rows = (data.get("earnings_cal") or {}).get("rows") or []
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["typical move"] = df["move"].map(lambda m: None if m is None or pd.isna(m) else f"±{m:.1%}")
    df["band"] = df["band"].map(lambda b: f"${b[0]:,.2f}–${b[1]:,.2f}" if isinstance(b, list) else "")
    df["up / last"] = [f"{u} of {n}" if n else "—" for u, n in zip(df["ups"], df["n"])]
    return df[["week", "date", "ticker", "days", "typical move", "band", "up / last"]]


def launch_text(path: Path = Path(__file__).parent / "docs" / "LAUNCH.md") -> str:
    """The first-real-run checklist, or '' if the file is missing."""
    return path.read_text() if path.exists() else ""


def stock(data: dict, ticker: str) -> dict:
    """The full record for one ticker (rankings or watchlist)."""
    return next(r for r in data["rankings"] + data["watchlist"] if r["ticker"] == ticker)


def history_table(rec: dict) -> pd.DataFrame:
    """Quarterly revenue ($bn) and gross margin (%) indexed by quarter-end date."""
    h = pd.DataFrame(rec.get("history") or [])          # missing if detail.json is absent
    if h.empty:
        return h
    h["q"] = pd.to_datetime(h["q"])
    return pd.DataFrame({"Revenue ($bn)": h["rev"] / 1e9,
                         "Gross margin (%)": h["gm"] * 100}).set_index(h["q"])


def factor_z(rec: dict, factors: dict | None = None) -> pd.Series:
    """z-scores of the factors that COUNT (weight > 0). factors.py already
    flips "lower is better" stats, so positive always means "helps the score"."""
    z = pd.Series(rec["z"], dtype=float).dropna()
    if factors:
        z = z[[f for f in z.index if factors[f]["weight"] > 0]]
    return z.sort_values()


def performance_curves(data: dict) -> tuple[pd.DataFrame, str]:
    """Paper portfolio vs SPY if tracking has started, else the backtest."""
    paper = data.get("paper") or {}
    curves, label = paper.get("curves") or {}, "Paper portfolio (live)"
    if len(curves.get("paper", [])) < 2:
        curves, label = data["backtest"]["curves"], "Backtest (paper tracking hasn't started yet)"
    out = {}
    for name, pts in curves.items():
        if name in ("strategy", "paper", "SPY"):            # keep it simple: us vs the market
            s = pd.Series({pd.Timestamp(d): v for d, v in pts})
            out["Top-5 strategy" if name != "SPY" else "S&P 500 (SPY)"] = s / s.iloc[0]  # start both at 1.0
    return pd.DataFrame(out), label


def order_table(data: dict, amount: float, fractional: bool, calmer: bool = False) -> pd.DataFrame:
    """Shares to buy of each top pick for `amount` dollars (see orders.py)."""
    picks = data["order_plan_inputs"]["picks"]
    weights = orders.calmer_weights(picks) if calmer else None   # more money in calmer stocks
    plan = orders.plan(picks, amount, fractional, weights)
    df = pd.DataFrame(plan["rows"])[["ticker", "price", "shares", "cost", "note"]]
    # heads-up for picks that report earnings within a week
    df["heads_up"] = [orders.earnings_note(p.get("days_to_filing"), p.get("earn_move")) for p in picks]
    return df.round({"price": 2, "shares": 4, "cost": 2})


def compare_table(data: dict, tickers: list[str]) -> pd.DataFrame:
    """Factor z-scores side by side (rows = factors that count, columns = tickers)."""
    recs = [stock(data, t) for t in tickers]
    rows = {c["label"].split(" (")[0]: [r["z"].get(f) for r in recs]
            for f, c in data["factors"].items() if c["weight"] > 0}
    return pd.DataFrame(rows, index=tickers).T


def compare_prices(data: dict, tickers: list[str]) -> pd.DataFrame:
    """1-year weekly prices, each starting at 100."""
    out = {}
    for t in tickers:
        p = pd.Series({pd.Timestamp(d): v for d, v in stock(data, t).get("px_1y") or []})
        if len(p):
            out[t] = p / p.iloc[0] * 100
    return pd.DataFrame(out)


def lots_table(data: dict) -> pd.DataFrame:
    """Your open tax lots (first in, first out), oldest first."""
    lots = ((data.get("my_trades") or {}).get("lots") or {}).get("open") or []
    if not lots:
        return pd.DataFrame()
    df = pd.DataFrame(lots)[["ticker", "date", "shares", "cost", "gain", "term", "lt_date"]]
    return df.rename(columns={"date": "bought", "lt_date": "long-term from"}).round(2)


# ---------- 2. The page: Streamlit draws everything below ----------
def main() -> None:
    import streamlit as st                                   # imported here so tests don't need it

    st.set_page_config(page_title="SemiScope", layout="wide")
    data = load_data()
    st.title("SemiScope")
    st.caption(f"Prices as of {data['prices_asof']} · mode: {data['mode']}")

    # Your list comes from state/my_stocks.csv; show any problems with it
    ms = data.get("my_stocks") or {}
    for t in ms.get("unknown", []):
        st.warning(f"{t} isn't a ticker we can find (no prices). Typo? Check state/my_stocks.csv.")
    for p in ms.get("problems", []):
        st.warning(p)
    with st.expander("My stock list"):
        st.write("Holdings: " + (", ".join(ms.get("holdings", [])) or "none"))
        for h in data.get("holdings") or []:                 # where each of your stocks ranks
            st.write(f"- {h['ticker']}: " + (rank_label(h["current"], h.get("in_universe", True))
                                              if h.get("current") else "no prices this run"))
        st.write("Watching: " + (", ".join(ms.get("watch", [])) or "none"))
        st.caption("Edit state/my_stocks.csv to change it (ticker,kind,note).")

    # A dropdown. Whatever you pick becomes `ticker`, and the page re-runs.
    tickers = [r["ticker"] for r in data["rankings"]] + [r["ticker"] for r in data["watchlist"]]
    ticker = st.selectbox("Pick a stock", tickers, index=0)
    rec = stock(data, ticker)

    # A row of 4 big numbers. st.columns splits the page into side-by-side boxes.
    c1, c2, c3, c4 = st.columns(4)
    in_universe = any(r["ticker"] == ticker for r in data["rankings"])
    c1.metric("Rank", rank_label(rec, in_universe))       # "≈#" = would rank, never picked
    c2.metric("Score", f"{rec['score']:+.2f}" if rec["score"] is not None else "—")
    c3.metric("3-month return", f"{rec['ret_3m']:.1%}" if rec["ret_3m"] is not None else "—")
    c4.metric("Gross margin", f"{rec['gross_margin']:.1%}" if rec["gross_margin"] else "—")

    left, right = st.columns(2)
    with left:                                               # everything indented goes in the left box
        st.subheader("Revenue & gross margin")
        h = history_table(rec)
        if h.empty:
            st.info("No SEC quarterly data for this stock (foreign filer).")
        else:
            st.caption("Quarterly revenue, $ billions")
            st.bar_chart(h["Revenue ($bn)"])
            st.caption("Gross margin, % of revenue")
            st.line_chart(h["Gross margin (%)"])
    with right:
        st.subheader("Why it ranks where it does")
        st.caption("Factor z-scores: bars right of 0 help the score, left of 0 hurt it.")
        st.bar_chart(factor_z(rec, data["factors"]), horizontal=True)

    # Cheap vs its own history: a progress bar works as a simple 0-100 gauge
    vv = valuation_view(rec)
    if vv:
        st.subheader("Cheap vs its own history")
        if vv["frac"] is not None:
            st.progress(vv["frac"])                          # left = cheapest it's been, right = priciest
        st.write(vv["text"])
        st.caption("Context only, not part of the score. Cheap can stay cheap in a downturn.")

    st.subheader(f"Top {data['top_n']} right now")
    st.dataframe(rankings_table(data).head(data["top_n"]), hide_index=True,
                 column_config={"ret_3m": st.column_config.NumberColumn("3-mo return", format="percent"),
                                "gross_margin": st.column_config.NumberColumn("Gross margin", format="percent"),
                                "score": st.column_config.NumberColumn(format="%.2f"),
                                "ps_pct": st.column_config.NumberColumn("P/S pct (own 5y)", format="%.0f")})

    # Group leadership: which industry groups are beating the semis ETF?
    groups = groups_table(data)
    if not groups.empty:
        st.subheader("Group leadership")
        st.caption((data.get("groups") or {}).get("read", ""))
        rel = [c for c in groups.columns if c.endswith("vs SOXX")]
        styled = (groups.style.map(diverging_color, subset=rel)          # color = ahead/behind SOXX
                  .format({**{c: "{:+.1%}" for c in rel}, "Breadth": "{:.0%}"}, na_rep="—"))
        st.dataframe(styled, hide_index=True)

    # "Invest $X": number_input gives a number box; radio gives a two-way choice
    st.subheader("Invest $X")
    st.caption("What the model's rules would buy with this amount at the last close. Arithmetic, not advice.")
    amount = st.number_input("Amount ($)", min_value=0.0, value=1000.0, step=100.0)
    frac = st.radio("Shares", ["Fractional", "Whole shares"], horizontal=True) == "Fractional"
    calm = st.radio("Sizing", ["Equal", "Calmer-weighted"], horizontal=True) == "Calmer-weighted"
    st.dataframe(order_table(data, amount, frac, calm), hide_index=True)

    st.subheader("Compare")
    picks = st.multiselect("Pick 2–3 stocks", tickers, default=tickers[:2], max_selections=3)
    if len(picks) >= 2:
        st.write(explain.compare(stock(data, picks[0]), stock(data, picks[1]), data["factors"])["sentence"])
        st.dataframe(compare_table(data, picks).round(2))
        st.caption("Price over the last year, each starting at 100")
        st.line_chart(compare_prices(data, picks))

    lots = lots_table(data)
    if not lots.empty:
        st.subheader("My tax lots")
        st.caption("Held more than a year = long-term. Not tax advice.")
        st.dataframe(lots, hide_index=True)
        for w in data["my_trades"]["lots"].get("wash", []):
            st.warning(w["text"])

    curves, label = performance_curves(data)
    st.subheader("Does it work?")
    st.caption(label + " · both lines start at 1.0, so 2.0 means doubled")
    st.line_chart(curves)

    # Earnings coming up: when each of your stocks reports, and how much it usually moves
    cal = earnings_table(data)
    if not cal.empty:
        st.subheader("Earnings coming up")
        st.caption("Dates are estimates. The band shows how big a typical reaction is, not which way.")
        st.dataframe(cal, hide_index=True)

    # Is the edge steady? One number per 1-year window: strategy minus SPY
    sv = steady_view(data)
    st.subheader("Is the edge steady?")
    if sv is None:
        st.info("Needs more than a year of daily history.")
    else:
        for col, (name, value, note) in zip(st.columns(4), sv["metrics"]):
            col.metric(name, value, help=note)
        st.line_chart(sv["series"])                          # above 0 = beat SPY over that year
        st.write(sv["read"])

    # The launch checklist, folded away until you need it
    text = launch_text()
    if text:
        with st.expander("Launch day: your first real run (docs/LAUNCH.md)"):
            st.markdown(text)


if __name__ == "__main__":   # true under `streamlit run`, false when tests import this file
    main()

# ---------------------------------------------------------------------------
# TRY THIS (one per practice session, run `streamlit run streamlit_app.py` after each)
# 1. Add a 5th metric: "Factors scored" using rec["n_factors"]. (Hint: st.columns(5).)
# 2. Add st.slider("How many to show", 3, 15, 5) and use it instead of data["top_n"].
# 3. Add SOXX to performance_curves (look at the `if name in (...)` line).
# 4. Put a checkbox "Only my stocks" that filters the dropdown to rec["owned"] == True.
# 5. Add a 4th line to the history chart: inventory days (h["dio"] in history_table).
#    Then write a test for it in tests/test_streamlit_app.py.
# 6. In diverging_color, change 0.15 to 0.05. What happens to the Group leadership colors,
#    and why? (Hint: it's the size of gap that counts as "full color".)
# 7. Add a horizontal line at 0 to the "Is the edge steady?" chart. st.line_chart can't, so
#    try st.altair_chart: an Altair line plus alt.Chart(...).mark_rule(y=0).
# ---------------------------------------------------------------------------
