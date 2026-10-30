"""
Alerts: compare this run with the previous one and flag what changed.

Only CHANGES trigger alerts, so a daily run doesn't spam you:
- new paper-portfolio picks were recorded (quarterly rebalance)
- one of your holdings changed signal (e.g. Above median -> Bottom quarter)
- a stock entered or left the top-N
- model health: rolling 4-quarter IC of the composite score turned negative

The GitHub workflow opens an issue when there are alerts; GitHub then emails /
push-notifies the repo owner (turn on notifications in the GitHub mobile app).
"""
from __future__ import annotations

from pathlib import Path

ALERTS_MD = Path(__file__).parent / "state" / "alerts.md"
LOG_KEEP = 40


def signal(rank: int | None, n: int | None, top_n: int) -> str:
    """Same buckets as the dashboard's My stocks tab."""
    if rank is None or not n:
        return "Not ranked"
    if rank <= top_n:
        return "Top pick"
    if rank <= n / 2:
        return "Above median"
    if rank <= n * 0.75:
        return "Below median"
    return "Bottom quarter"


ORDER = ["Bottom quarter", "Below median", "Above median", "Top pick"]


PRICE_ONLY = "Price data only"


def holding_signal(h: dict, n: int | None, top_n: int) -> tuple[str, int | None]:
    """(signal, rank) for one holding. A watchlist stock uses where it WOULD rank. A universe
    stock with only a price-only rank (too few stats, e.g. a foreign filer) is never picked,
    so it must not be called a "Top pick": it gets its own bucket."""
    c = h.get("current") or {}
    r = c.get("rank") if c.get("rank") is not None else c.get("would_rank")
    r = int(r) if r is not None else None
    if c.get("rank") is None and r is not None and h.get("in_universe", True):
        return PRICE_ONLY, r
    return signal(r, n, top_n), r


def _holding_signals(data: dict) -> dict[str, tuple[str, int | None]]:
    """{ticker: (signal, rank)} for each of your holdings in a data.json snapshot."""
    return {h["ticker"]: holding_signal(h, data.get("universe_size"), data.get("top_n", 5))
            for h in data.get("holdings") or []}


def _top(data: dict) -> set[str]:
    """Tickers currently in the top N."""
    n = data.get("top_n", 5)
    return {r["ticker"] for r in data.get("rankings") or [] if r.get("rank") is not None and r["rank"] <= n}


def _rolling_ic(data: dict, k: int = 4) -> float | None:
    """Average IC of the composite score over the last k quarters."""
    ic = [v for _, v in ((data.get("research") or {}).get("ic") or {}).get("score", []) if v is not None]
    return sum(ic[-k:]) / len(ic[-k:]) if len(ic) >= k else None


def compute(prev: dict | None, cur: dict) -> list[dict]:
    """List of alerts ({level, kind, text}) describing what changed since `prev`."""
    alerts = []

    def add(level, kind, text, ticker=None):
        a = {"level": level, "kind": kind, "text": text}
        why = ((cur.get("explain") or {}).get("run_text") or {}).get(ticker) if ticker else None
        if why:
            a["because"] = why
            a["text"] += f" — because: {why}"
        alerts.append(a)

    # big price moves in your holdings and the model's picks (don't need a previous run)
    if cur.get("moves"):
        from config import MOVE_ALERT_Z
        import moves as moves_mod
        watch = [h["ticker"] for h in cur.get("holdings") or []] + \
                [p["ticker"] for p in (cur.get("order_plan_inputs") or {}).get("picks", [])]
        for a in moves_mod.alerts_for(cur["moves"], watch, MOVE_ALERT_Z):
            add(a["level"], "move", a["text"])

    prev_entries = {e["date"] for e in ((prev or {}).get("paper") or {}).get("entries", [])}
    for e in (cur.get("paper") or {}).get("entries", []):
        if e["date"] not in prev_entries:
            add("action", "paper", f"New paper picks recorded {e['date']} ({e['reason']}): {', '.join(e['picks'])}")

    # comparing a demo run with a live one is meaningless
    if prev is None or prev.get("mode") != cur.get("mode"):
        if prev is not None:
            add("info", "system", f"Switched from {prev.get('mode')} to {cur.get('mode')} data — change alerts start next run.")
        return alerts

    import sellrules                         # holdings where a rule that WORKED in past tests just fired
    for a in sellrules.alerts_for(cur, prev):
        add(a["level"], a["kind"], a["text"])

    p_sig, c_sig = _holding_signals(prev), _holding_signals(cur)
    for t, (sig, r) in c_sig.items():
        if t in p_sig and p_sig[t][0] != sig:
            old = p_sig[t][0]
            up = ORDER.index(sig) > ORDER.index(old) if sig in ORDER and old in ORDER else None
            level = "good" if up else "warning"
            arrow = "↑" if up else "↓"
            add(level, "holding", f"{t} {arrow} {old} → {sig} (rank {p_sig[t][1]} → {r})", t)

    p_top, c_top = _top(prev), _top(cur)
    for t in sorted(c_top - p_top):
        add("info", "top", f"{t} entered the top {cur.get('top_n', 5)}", t)
    for t in sorted(p_top - c_top):
        add("info", "top", f"{t} left the top {cur.get('top_n', 5)}", t)

    # a holding's data went stale (missed filing / delisting / ticker change)
    def _stale(d):
        holds = {h["ticker"] for h in d.get("holdings") or []}
        return {r["ticker"] for r in ((d.get("data_health") or {}).get("rows") or [])
                if r.get("stale") and r["ticker"] in holds}
    for t in sorted(_stale(cur) - _stale(prev)):
        add("warning", "data", f"{t}: no new SEC filing in over "
            f"{(cur.get('data_health') or {}).get('stale_days', 120)} days — its fundamentals are getting stale.")

    p_ic, c_ic = _rolling_ic(prev), _rolling_ic(cur)
    if c_ic is not None and c_ic < 0 and (p_ic is None or p_ic >= 0):
        add("warning", "model", f"Model health: rolling 4-quarter IC turned negative ({c_ic:+.3f}). "
                                "The score hasn't been predicting returns lately — be skeptical of new picks.")
    elif c_ic is not None and c_ic >= 0 and p_ic is not None and p_ic < 0:
        add("good", "model", f"Model health recovered: rolling 4-quarter IC back to {c_ic:+.3f}.")
    return alerts


ISSUE_MAX = 10          # alert lines in the GitHub issue (phone notifications get cut off anyway)
LEVEL_ORDER = {"action": 0, "warning": 1, "good": 2, "info": 3}


def to_markdown(alerts: list[dict], asof: str, max_items: int = ISSUE_MAX) -> str:
    """Format alerts as the body of a GitHub issue: most important first, at most `max_items`
    lines, then "+N more on the dashboard"."""
    icon = {"action": "📌", "warning": "⚠️", "good": "✅", "info": "ℹ️"}
    ranked = sorted(alerts, key=lambda a: LEVEL_ORDER.get(a.get("level"), 9))   # stable: keeps order within a level
    lines = [f"SemiScope alerts — prices as of {asof}", ""]
    lines += [f"- {icon.get(a['level'], '•')} {a['text']}" for a in ranked[:max_items]]
    if len(ranked) > max_items:
        lines.append(f"- … +{len(ranked) - max_items} more on the dashboard (My stocks → Alert log)")
    lines += ["", "_Research tool, not financial advice._"]
    return "\n".join(lines)


def write(alerts: list[dict], asof: str) -> None:
    """Write state/alerts.md if there are alerts (the workflow turns it into an issue)."""
    if alerts:
        ALERTS_MD.parent.mkdir(exist_ok=True)
        ALERTS_MD.write_text(to_markdown(alerts, asof))
    elif ALERTS_MD.exists():
        ALERTS_MD.unlink()


def merge_log(prev: dict | None, alerts: list[dict], asof: str, mode: str | None = None) -> list[dict]:
    """Prepend new alerts to the running log (reset when switching demo <-> live).

    Re-running on the same prices date (a manual run after the scheduled one, or the demo run
    twice) REPLACES that day's entries instead of piling up copies. Exact duplicate
    (date, text) pairs already in an older log are dropped too."""
    same_mode = prev is not None and prev.get("mode") == mode
    old = list(prev.get("alert_log") or []) if same_mode else []
    old = [a for a in old if a.get("date") != asof]            # this day is re-computed below
    log, seen = [], set()
    for a in [dict(a, date=asof) for a in alerts] + old:
        key = (a.get("date"), a.get("text"))
        if key in seen:
            continue
        seen.add(key)
        log.append(a)
    return log[:LOG_KEEP]
