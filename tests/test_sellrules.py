"""Sell rules (sellrules.py): the rules, the honest test of each one, and the alerts that follow."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import sellrules as sr

ROOT = Path(__file__).resolve().parents[1]


def frame(cols: dict, n=None) -> pd.DataFrame:
    n = n or len(next(iter(cols.values())))
    return pd.DataFrame(cols, index=pd.bdate_range("2018-01-01", periods=n))


def iid(T=1600, N=14, seed=1, sigma=0.015):
    rng = np.random.default_rng(seed)
    return frame({f"S{i}": 100 * np.exp(np.cumsum(rng.normal(0, sigma, T))) for i in range(N)})


def momentum_market(T=1600, N=14, seed=3, sigma=0.012, pull=0.003):
    """Stocks that are 20% under their 6-month high keep sinking (drift -pull a day): the stop rule should WORK."""
    rng = np.random.default_rng(seed)
    px = np.full((T, N), 100.0)
    for t in range(1, T):
        lo = max(0, t - sr.STOP_WINDOW)
        hi = px[lo:t].max(axis=0)
        sink = px[t - 1] <= (1 - sr.STOP_DROP) * hi
        px[t] = px[t - 1] * np.exp(rng.normal(0, sigma, N) - pull * sink)
    return frame({f"S{i}": px[:, i] for i in range(N)})


# ----------------------------------------------------------------------------- the rules by hand
def test_stop_fires_at_20_percent_below_the_six_month_high_and_not_before():
    px = frame({"A": [100.0] * 150 + [81.0, 79.0], "B": [100.0] * 152})
    f = sr.price_flags(px)["stop"]
    assert f["A"].iloc[-2] == 0.0 and f["A"].iloc[-1] == 1.0            # -19% no, -21% yes
    assert (f["B"].dropna() == 0).all() and f["B"].iloc[:100].isna().all()   # needs 126 days of history


def test_trend_runup_and_breakdown_by_hand():
    up = frame({"A": list(np.linspace(100, 400, 300)) + [90.0]})
    fl = sr.price_flags(up)
    assert fl["trend"]["A"].iloc[-2] == 0.0 and fl["trend"]["A"].iloc[-1] == 1.0      # a sharp drop under the 200-day average
    assert fl["runup"]["A"].iloc[200] == 1.0 and fl["runup"]["A"].iloc[:100].isna().all()
    rng = np.random.default_rng(0)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400)))
    p2 = np.append(p, p[-1] * np.exp(-0.30))                                           # one huge down-day
    f2 = sr.price_flags(frame({"A": p2}))["breakdown"]["A"]
    assert f2.iloc[-1] == 1.0 and f2.iloc[:250].isna().all()
    assert sr.price_flags(frame({"A": p}))["breakdown"]["A"].iloc[-1] == 0.0


def test_no_rule_can_see_the_future():
    px = iid(T=700, N=3, seed=5)
    a = sr.price_flags(px)
    px2 = px.copy()
    px2.iloc[500:] *= 3.0                                  # change only the future of day 499
    b = sr.price_flags(px2)
    for k in a:
        pd.testing.assert_frame_equal(a[k].iloc[:500], b[k].iloc[:500])


# ----------------------------------------------------------------------------- the honest test
def test_verdict_needs_enough_dates_and_a_big_enough_t():
    assert sr.verdict([-0.01] * 5)["verdict"] == "too few to tell"
    rng = np.random.default_rng(0)
    assert sr.verdict(list(rng.normal(-0.02, 0.01, 40)))["verdict"] == "worked"
    assert sr.verdict(list(rng.normal(0.02, 0.01, 40)))["verdict"] == "hurt"
    assert sr.verdict(list(rng.normal(0.0, 0.05, 40)))["verdict"] == "no clear edge"
    assert sr.verdict([0.01] * 20)["verdict"] == "no clear edge"        # no spread: t undefined


def test_the_study_finds_a_planted_edge_and_stays_quiet_on_pure_noise():
    res = sr.study_price(momentum_market())
    assert res["stop"]["verdict"] == "worked" and res["stop"]["fired"] < res["stop"]["not_fired"]
    for seed in (1, 2, 3):
        noise = sr.study_price(iid(seed=seed))
        assert all(r["verdict"] != "worked" for r in noise.values()), (seed, noise)


def test_rank_study_by_hand():
    idx = list("ABCDEFGH")

    def q(scores, fwd):
        return {"score": pd.Series(scores, index=idx, dtype=float), "fwd": pd.Series(fwd, index=idx, dtype=float)}

    panel = [q([8, 7, 6, 5, 4, 3, 2, 1], [0] * 8),
             # held = A,B (top 2). Now A fell to the bottom and lost; B stayed and won
             q([1, 8, 7, 6, 5, 4, 3, 2], [-0.10, 0.10, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]
    out = sr.study_rank(panel, top_n=2)
    assert out["rank_drop"]["n_events"] == 1
    ex_a = -0.10                                                        # universe mean fwd is 0 -> excess is the raw return
    assert out["rank_drop"]["fired"] == pytest.approx(ex_a, abs=1e-9)
    assert out["rank_drop"]["not_fired"] == pytest.approx(0.10, abs=1e-9)
    assert out["rank_drop"]["verdict"] == "too few to tell"             # one quarter is nothing


# ----------------------------------------------------------------------------- today's flags and alerts
def test_now_flags_marks_validated_rules_and_uses_rank_only_for_last_picks():
    px = frame({"A": [100.0] * 150 + [70.0], "B": [100.0] * 151})
    study = {"stop": {"verdict": "worked"}, "rank_drop": {"verdict": "no clear edge"}}
    out = sr.now_flags(px, ["A", "B", "Z"], {"A": 20, "B": 1}, ["A", "B"], 5, 30, study)
    assert set(out) == {"A"}                                            # B is fine, Z has no prices
    rules = {h["rule"]: h for h in out["A"]}
    assert rules["stop"]["validated"] and not rules["rank_drop"]["validated"] and "bottom_half" in rules
    assert "30% from its 6-month high" in rules["stop"]["detail"]
    out2 = sr.now_flags(px, ["A"], {"A": 20}, ["B"], 5, 30, study)      # A was not a last pick: no rank rules
    assert {h["rule"] for h in out2["A"]} == {"stop"}


def _data(now):
    return {"research": {"sell_rules": {"now": now}}}


def test_alerts_only_for_validated_rules_and_only_when_new():
    hit = {"rule": "stop", "label": "20% off its high", "detail": "-25% from its 6-month high", "validated": True}
    soft = {"rule": "runup", "label": "Up 50% in 6 months", "detail": "up 60%", "validated": False}
    cur = _data({"MU": [hit, soft]})
    a = sr.alerts_for(cur, _data({}))
    assert len(a) == 1 and a[0]["kind"] == "sell" and a[0]["level"] == "warning" and "MU" in a[0]["text"]
    assert sr.alerts_for(cur, cur) == []                                # still firing: not repeated
    assert sr.alerts_for(_data({}), cur) == []                          # stopped firing: nothing to say
    assert sr.alerts_for(None, None) == [] and sr.alerts_for({}, {}) == []


def test_alerts_hook_runs_through_alerts_compute():
    import alerts
    hit = {"rule": "stop", "label": "20% off its high", "detail": "x", "validated": True}
    cur = {"mode": "live", "research": {"sell_rules": {"now": {"MU": [hit]}}}, "holdings": []}
    prev = {"mode": "live", "research": {"sell_rules": {"now": {}}}, "holdings": []}
    assert any(a["kind"] == "sell" for a in alerts.compute(prev, cur))
    assert not any(a["kind"] == "sell" for a in alerts.compute(cur, cur))


# ----------------------------------------------------------------------------- the report
def test_build_shape_json_and_not_enough_prices():
    px = momentum_market(T=1000, N=10)
    panel = [{"score": pd.Series(np.arange(10.0), index=px.columns), "fwd": pd.Series(np.zeros(10), index=px.columns)}] * 3
    out = sr.build(px, panel, ["S0", "S1"], {"S0": 1, "S1": 9}, ["S0"], 3, 10, list(px.columns))
    assert out["available"] and [r["key"] for r in out["rules"]] == list(sr.PRICE_RULES + sr.RANK_RULES)
    assert out["validated"] == [r["key"] for r in out["rules"] if r["verdict"] == "worked"]
    assert out["asof"] == px.index[-1].strftime("%Y-%m-%d") and out["read"]
    json.loads(json.dumps(out))
    assert len(json.dumps(out)) < 6000
    assert sr.build(iid(T=100, N=3), [], [], {}, [], 5, 3)["available"] is False


def test_dashboard_card_is_wired():
    html = (ROOT / "docs" / "index.html").read_text()
    assert 'id="sell-card" hidden' in html and "renderSell(); renderMine();" in html
    fn = re.search(r"function renderSell\(\).*?\n}\n", html, re.S).group(0)
    assert "research||{}).sell_rules" in fn.replace(" ", "") or "sell_rules" in fn
    assert "not validated" in fn and "S.read" in fn
