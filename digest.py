"""
Weekly-style digest: the five things worth knowing, in plain English.

Written to state/digest.md every run (committed by the workflow, so you get a
dated history in git) and shown as the "This week" card on the dashboard.
"""
from __future__ import annotations

from pathlib import Path

import alerts as alerts_mod
import valuation
import earnings_cal

DIGEST_MD = Path(__file__).parent / "state" / "digest.md"


def _pct(x, d=1):
    return "n/a" if x is None else f"{x * 100:+.{d}f}%"


def sections(data: dict) -> list[dict]:
    """Structured digest: [{title, items: [str]}] built from a data.json dict."""
    out = []
    n, top_n = data.get("universe_size") or 0, data.get("top_n", 5)

    c = data.get("cycle") or {}
    if c:
        out.append({"title": f"Cycle: {c.get('phase', 'Unknown')}", "items": [
            c.get("phase_text", ""),
            f"Median sales growth {_pct(c.get('median_growth'))}; "
            f"{round((c.get('accel_share') or 0) * 100)}% of companies accelerating.",
        ]})

    ranks = [r for r in data.get("rankings") or [] if r.get("rank") is not None]
    top = sorted(ranks, key=lambda r: r["rank"])[:top_n]
    moves = [a["text"] for a in data.get("alerts") or [] if a["kind"] == "top"]
    out.append({"title": f"Top {top_n} right now", "items":
                [", ".join(f"{r['ticker']} ({r['score']:+.2f})" for r in top) or "No ranked stocks yet."]
                + (moves or ["No changes since the last update."])})

    sm = [m["text"] for m in data.get("score_moves") or [] if m.get("text")]
    if sm:
        since = (data.get("explain") or {}).get("run_date")
        out.append({"title": "Biggest score moves" + (f" since {since}" if since else ""), "items": sm +
                    ["Each number is that stat's share of the score change; the shares add up to the total."]})

    oc = data.get("outcomes") or {}
    if oc.get("read"):
        out.append({"title": "What could $1,000 become? (backtest replayed)", "items": [oc["read"]]})

    dd = data.get("drawdowns") or {}
    if dd.get("read"):
        out.append({"title": "Drawdowns (backtest)", "items": [dd["read"]]})

    cap = data.get("capture") or {}
    cs = cap.get("paper") or cap.get("backtest") or {}
    if cs.get("SOXX") or cs.get("SPY"):
        out.append({"title": "Up/down capture" + (" (paper portfolio)" if cap.get("paper") else " (backtest)"),
                    "items": [c["read"] for c in (cs.get("SOXX"), cs.get("SPY")) if c and c.get("read")]})

    qs = (data.get("weekly") or {}).get("questions") or []
    if qs:
        out.append({"title": "Questions for this week", "items": [q["q"] for q in qs] +
                    ["The whole week on one screen: weekly.html on your dashboard."]})

    rb = data.get("rebalance") or {}
    if rb.get("text"):
        out.append({"title": "Next rebalance", "items": [rb["text"]]})

    ec = earnings_cal.digest_items(data.get("earnings_cal"))
    if ec:
        out.append({"title": f"Earnings coming up (next {earnings_cal.DIGEST_DAYS} days)", "items": ec +
                    ["Dates are estimates from each company's filing rhythm. Past moves show size, not direction."]})

    gr = data.get("groups") or {}
    if gr.get("read"):
        out.append({"title": "Group leadership", "items": [gr["read"]]})

    hold_items = []
    for h in data.get("holdings") or []:
        cur = h.get("current") or {}
        sig, r = alerts_mod.holding_signal(h, n, top_n)
        where = f"#{int(r)}/{n}" if r is not None else "unranked"
        if r is not None and (not h.get("in_universe") or cur.get("rank") is None):
            where = "≈" + where
        if cur.get("rank") is None and r is not None and h.get("in_universe"):
            where += ", price data only"         # e.g. a foreign filer: too few factors to be picked
        hold_items.append(f"{h['ticker']}: {sig} ({where})")
    # valuation extremes vs each holding's own 5-year P/S range (context, not a signal)
    for h in data.get("holdings") or []:
        v = (h.get("current") or {}).get("valuation")
        if v and v.get("pct") is not None and not valuation.EXTREME_LO <= v["pct"] <= valuation.EXTREME_HI:
            hold_items.append(valuation.sentence(h["ticker"], v))
    if hold_items:
        out.append({"title": "Your stocks", "items": hold_items})

    p = data.get("paper") or {}
    st = p.get("stats") or {}
    if p.get("entries") and not (st.get("paper") or {}).get("total_return") and \
            (st.get("paper") or {}).get("total_return") != 0:
        e = p["entries"][-1]
        out.append({"title": "Paper portfolio (the real test)", "items": [
            f"Opened {p['entries'][0]['date']} with {', '.join(e['picks'])} — tracking starts next update."]})
    elif st.get("paper"):
        pr, spy = st["paper"].get("total_return"), (st.get("SPY") or {}).get("total_return")
        since = (p.get("entries") or [{}])[0].get("date", "?")
        edge = None if pr is None or spy is None else pr - spy
        out.append({"title": "Paper portfolio (the real test)", "items": [
            f"Since {since}: {_pct(pr)} vs S&P 500 {_pct(spy)} → "
            + ("ahead" if (edge or 0) > 0 else "behind" if (edge or 0) < 0 else "even")
            + (f" by {abs(edge) * 100:.1f} pts" if edge else "")]})

    sn = data.get("since") or {}
    if sn and not sn.get("first"):
        out.insert(0, {"title": "Since last run", "items": [sn["text"]]})

    conf = data.get("confidence") or {}
    cb = conf.get("paper") or conf.get("backtest")
    if cb and cb.get("t") is not None:
        src = "paper portfolio" if conf.get("paper") else "backtest (in-sample)"
        more = f"; ~{cb['more_quarters']} more quarters to reach t = 2" if cb.get("more_quarters") else ""
        out.append({"title": "Is the edge real?", "items": [
            f"{cb['verdict']}: {src} beat SPY by {_pct(cb['mean'])}/quarter over {cb['n']} quarters, "
            f"t = {cb['t']:.1f}{more}."]})
    st = data.get("steady") or {}
    sv = st.get("paper") if (st.get("paper") or {}).get("available") else st.get("backtest")
    if sv and sv.get("available"):
        sec = next((x for x in out if x["title"] == "Is the edge real?"), None)
        if sec is None:
            sec = {"title": "Is the edge real?", "items": []}
            out.append(sec)
        sec["items"].append(("Paper portfolio: " if sv["label"] == "paper" else "Backtest: ") + sv["read"])

    ic = [v for _, v in ((data.get("research") or {}).get("ic") or {}).get("score", []) if v is not None]
    if len(ic) >= 4:
        roll = sum(ic[-4:]) / 4
        out.append({"title": "Model health", "items": [
            f"Last 4 quarters' IC {roll:+.3f} — " + (
                "the score has been predicting returns." if roll > 0.03 else
                "weak signal lately; treat picks with caution." if roll >= 0 else
                "the score has NOT been working lately. Be skeptical.")]})

    up = data.get("upcoming_filings") or []
    if up:
        owned = {h["ticker"] for h in data.get("holdings") or []}
        out.append({"title": "Upcoming filings (scores refresh after)", "items": [
            f"{u['ticker']}{' (yours)' if u['ticker'] in owned else ''}: ≈{u['next_filing']} "
            f"(in {u['days_until']} day{'s' if u['days_until'] != 1 else ''})" for u in up[:8]]})

    dh = (data.get("data_health") or {}).get("summary") or {}
    if dh:
        issues = [r["ticker"] for r in (data.get("data_health") or {}).get("rows", []) if r["status"] == "warn"]
        out.append({"title": "Data", "items": [
            f"{dh.get('ok', 0)}/{dh.get('n', 0)} companies clean"
            + (f"; check: {', '.join(issues[:6])}" if issues else ".")]})
    return out


def to_markdown(data: dict, secs: list[dict]) -> str:
    lines = [f"# SemiScope digest — {data.get('prices_asof', '')}", ""]
    if data.get("mode") == "demo":
        lines += ["> Demo data — not real markets.", ""]
    for s in secs:
        lines.append(f"## {s['title']}")
        lines += [f"- {i}" for i in s["items"] if i]
        lines.append("")
    lines.append("_Research tool, not financial advice._")
    return "\n".join(lines)


def build(data: dict, write: bool = True) -> dict:
    secs = sections(data)
    md = to_markdown(data, secs)
    if write:
        DIGEST_MD.parent.mkdir(exist_ok=True)
        DIGEST_MD.write_text(md)
    return {"sections": secs, "markdown": md}
