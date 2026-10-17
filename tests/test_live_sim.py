"""
End-to-end dry run of the LIVE pipeline with fake SEC + Yahoo (tests/fixtures/live_sim.py).
Two runs on consecutive days in a copy of the repo: a brand-new install, then a --fast update.
Slow (~60 s), but it's the only test that goes through load_live().
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import live_sim  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.slow          # ~60 s: runs after the data is saved in CI
sys.path.insert(0, str(ROOT))
import slim  # noqa: E402


def strict(path: Path):
    """json.loads that rejects NaN/Infinity (browsers' JSON.parse does too)."""
    def bad(c):
        raise ValueError(f"non-standard JSON constant {c} in {path.name}")
    return json.loads(path.read_text(), parse_constant=bad)


@pytest.fixture(scope="module")
def sim(tmp_path_factory):
    before = {p: p.stat().st_mtime for p in (ROOT / "docs").glob("*.json")}
    r = live_sim.simulate(tmp_path_factory.mktemp("live"))
    r["before"] = before
    return r


@pytest.fixture(scope="module")
def data(sim):
    return slim.unpack(strict(sim["repo"] / "docs" / "data.json"))


def test_both_runs_finish(sim):
    assert sim["codes"] == [0, 0], sim["logs"][-1][-3000:]
    assert "simulated Yahoo timeout" in sim["logs"][0]           # first download failed...
    assert "Done → docs/data.json" in sim["logs"][1]              # ...and the retry carried on
    # the repo ships with demo data.json: the first live run must replace it, not compare to it
    assert "Switched from demo to live data" in sim["logs"][0]


def test_outputs_are_strict_json(sim, data):
    detail = strict(sim["repo"] / "docs" / "detail.json")
    assert data["mode"] == "live" and data["prices_asof"] == live_sim.DAY2
    assert data["detail_file"] == "detail.json"
    assert len(data["rankings"]) >= 25 and "NVDA" in detail
    assert detail["AAPL"]["history"]        # the 53-week-year fixture parsed


def test_run_log_ok(sim):
    log = json.loads((sim["repo"] / "docs" / "run_log.json").read_text())
    assert [e["status"] for e in log] == ["ok", "ok"]
    assert [e["kind"] for e in log] == ["full", "fast"]
    assert log[-1]["skipped_tickers"] == sorted([live_sim.TYPO, live_sim.SEC_FAILS, live_sim.NOT_IN_SEC])


def test_expected_warnings(data):
    ms = data["my_stocks"]
    assert ms["unknown"] == [live_sim.TYPO]                       # typo in my_stocks.csv
    assert ms["stale"] == {live_sim.STALE: 2}                      # stale last bars
    health = {r["ticker"]: r for r in data["data_health"]["rows"]}
    assert data["data_health"]["summary"]["stale_price"] == [live_sim.STALE]
    assert health["ASML"]["status"] == health["TSM"]["status"] == "missing"     # foreign filers
    assert "SEC download failed" in " ".join(health[live_sim.SEC_FAILS]["flags"])
    assert "not found in SEC ticker list" in " ".join(health[live_sim.NOT_IN_SEC]["flags"])
    assert health["AAPL"]["stale"]                                 # old fixture = no recent filing
    mu = next(r for r in data["rankings"] if r["ticker"] == live_sim.STALE)
    assert mu["stale_days"] == 2 and mu["rank"] is not None        # flagged, still ranked


def test_foreign_filers_get_a_price_only_rank(data):
    """Live-only bug this dry run found: ASML/TSM have just 2 (price) factors, below
    MIN_FACTORS, so they were silently 'unranked' forever. Now they get a would_rank."""
    for t in ("ASML", "TSM"):
        r = next(r for r in data["rankings"] if r["ticker"] == t)
        assert r["rank"] is None and r["would_rank"] is not None
    asml = next(h for h in data["holdings"] if h["ticker"] == "ASML")
    assert asml["current"]["would_rank"] is not None


def test_second_run_sees_the_first(sim, data):
    assert data["since"]["text"].startswith("Since Oct 12:")
    snap = json.loads((sim["repo"] / "state" / "prev_snapshot.json").read_text())
    assert snap["asof"] == live_sim.DAY2
    digest = (sim["repo"] / "state" / "digest.md").read_text()
    assert "## Since last run" in digest and "ASML: " in digest and "price data only" in digest
    assert (sim["repo"] / "state" / "paper_portfolio.json").exists()
    assert data["my_trades"]["n_trades"] == 2


def test_real_repo_untouched(sim):
    for p, m in sim["before"].items():
        assert p.stat().st_mtime == m, f"{p.name} was modified by the simulation"
    assert not (ROOT / "docs" / "run_log.json").exists() or (ROOT / "docs" / "run_log.json") in sim["before"]


def test_alert_log_has_no_duplicates_and_stays_small(data):
    log = data["alert_log"]
    keys = [(a["date"], a["text"]) for a in log]
    assert len(keys) == len(set(keys))
    per_day = {}
    for d, _ in keys:
        per_day[d] = per_day.get(d, 0) + 1
    assert set(per_day) == {live_sim.DAY1, live_sim.DAY2}
    assert max(per_day.values()) <= 12, per_day          # a normal day shouldn't flood the log
    assert sum("52-week high" in t for _, t in keys if _ == live_sim.DAY2) <= 1   # grouped into one line


def test_score_moves_on_the_second_run(data):
    """Day 2 has a previous run to compare with, so score moves are computed (may be empty if nothing
    moved 0.15+); each names a stock that is in today's rankings."""
    moves = data["score_moves"]
    assert isinstance(moves, list) and len(moves) <= 5
    tickers = {r["ticker"] for r in data["rankings"] + data["watchlist"]}
    for m in moves:
        assert m["ticker"] in tickers and m["text"].startswith(m["ticker"] + " ")
        assert abs(m["delta"]) >= 0.15


def test_units_error_is_caught_and_ignored(sim, data):
    """Quirk 9: one company's latest 10-Q revenue is 1,000x too big. sanity.py must flag it in
    Data health and drop that quarter, so the stock is scored on its real numbers."""
    h = {r["ticker"]: r for r in data["data_health"]["rows"]}[live_sim.UNITS]
    assert h["status"] == "warn" and any("revenue" in t and "units error" in t for t in h.get("sanity", []))
    assert live_sim.UNITS in data["data_health"]["summary"]["sanity"]
    r = next(r for r in data["rankings"] + data["watchlist"] if r["ticker"] == live_sim.UNITS)
    g = (r.get("raw") or {}).get("rev_growth")
    assert g is None or abs(g) < 5, g                         # a 1,000x quarter would be ~ +100,000%
    assert "Sanity:" in sim["logs"][0] and live_sim.UNITS in sim["logs"][0]
