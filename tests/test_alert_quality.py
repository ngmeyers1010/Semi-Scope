"""Round 53: no duplicate alerts on re-runs, grouped 52-week highs, short GitHub issues."""
import alerts
import moves


def A(text, level="info", kind="top"):
    return {"level": level, "kind": kind, "text": text}


def test_same_day_rerun_replaces_instead_of_duplicating():
    prev = {"mode": "live", "alert_log": [dict(A("X entered the top 5"), date="2026-10-13"),
                                          dict(A("old"), date="2026-10-12")]}
    log = alerts.merge_log(prev, [A("X entered the top 5"), A("Y left the top 5")], "2026-10-13", "live")
    assert [(a["date"], a["text"]) for a in log] == [("2026-10-13", "X entered the top 5"),
                                                      ("2026-10-13", "Y left the top 5"), ("2026-10-12", "old")]
    # running again with fewer alerts that day: the day's list is replaced, not merged
    log2 = alerts.merge_log({"mode": "live", "alert_log": log}, [A("Y left the top 5")], "2026-10-13", "live")
    assert [a["text"] for a in log2] == ["Y left the top 5", "old"]


def test_new_day_prepends_and_mode_switch_resets():
    prev = {"mode": "live", "alert_log": [dict(A("a"), date="2026-10-12")]}
    assert [a["date"] for a in alerts.merge_log(prev, [A("b")], "2026-10-13", "live")] == ["2026-10-13", "2026-10-12"]
    assert [a["text"] for a in alerts.merge_log(prev, [A("b")], "2026-10-13", "demo")] == ["b"]


def test_old_duplicates_are_cleaned_on_load():
    dup = dict(A("same"), date="2026-10-10")
    prev = {"mode": "demo", "alert_log": [dup, dict(dup), dict(dup), dict(A("other"), date="2026-10-10")]}
    log = alerts.merge_log(prev, [], "2026-10-13", "demo")
    assert [a["text"] for a in log] == ["same", "other"]


def _m(r, z=1.0, hi=False, lo=False):
    return {"r_1d": r, "z_1d": z, "new_52w_high": hi, "new_52w_low": lo}


def test_52_week_highs_grouped_and_sorted():
    mv = {"INTC": _m(0.019, hi=True), "AMD": _m(0.027, hi=True), "AMZN": _m(0.021, hi=True),
          "MU": _m(-0.01, lo=True), "NVDA": _m(-0.08, z=-3.5), "QQQ": _m(0.05, hi=True)}
    out = moves.alerts_for(mv, ["INTC", "AMD", "AMZN", "MU", "NVDA"], 2.5)   # QQQ isn't watched
    texts = [a["text"] for a in out]
    assert texts[0].startswith("NVDA ")                                          # big move: own line
    assert "New 52-week highs: AMD, AMZN, INTC (+1.9% to +2.7% today)" in texts
    assert "MU hit a new 52-week low (-1.0% today)" in texts
    assert len(out) == 3 and all(a["kind"] == "move" for a in out)
    high = next(a for a in out if a["text"].startswith("New 52-week highs"))
    assert high["level"] == "good" and high["tickers"] == ["AMD", "AMZN", "INTC"]


def test_issue_body_is_short_and_important_first():
    many = [A(f"info {i}") for i in range(14)] + [A("picks recorded", level="action")]
    md = alerts.to_markdown(many, "2026-10-13")
    items = [l for l in md.splitlines() if l.startswith("- ")]
    assert len(items) == alerts.ISSUE_MAX + 1 and "picks recorded" in items[0]
    assert items[-1].startswith("- … +5 more on the dashboard")
    assert len(md.splitlines()) <= 15
    few = alerts.to_markdown([A("one")], "2026-10-13")
    assert "more on the dashboard" not in few
