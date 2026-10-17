"""Group concentration (concentration.py): the 2-per-group cap, today's read, the weekly question."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import concentration as cc  # noqa: E402
import slim  # noqa: E402
import weekly  # noqa: E402

U = {"A1": {"group": "Equip"}, "A2": {"group": "Equip"}, "A3": {"group": "Equip"}, "A4": {"group": "Equip"},
     "B1": {"group": "Memory"}, "B2": {"group": "Memory"}, "C1": {"group": "Analog"}, "D1": {"group": "Compute"}}


def test_cap_changes_picks():
    ranked = ["A1", "A2", "A3", "A4", "B1", "C1", "D1", "B2"]
    assert ranked[:5] != cc.capped_picks(ranked, 5, 2, U)
    assert cc.capped_picks(ranked, 5, 2, U) == ["A1", "A2", "B1", "C1", "D1"]     # A3, A4 skipped
    assert cc.capped_picks(ranked, 5, 3, U) == ["A1", "A2", "A3", "B1", "C1"]


def test_always_n_picks_when_enough_stocks():
    ranked = ["A1", "A2", "A3", "A4", "B1", "B2"]          # only 2 groups: cap alone gives 4
    got = cc.capped_picks(ranked, 5, 2, U)
    assert len(got) == 5 and len(set(got)) == 5
    assert got == ["A1", "A2", "B1", "B2", "A3"]          # best skipped stock fills the gap
    assert cc.capped_picks(["A1", "B1"], 5, 2, U) == ["A1", "B1"]      # fewer stocks than n: all of them
    assert cc.capped_picks([], 5, 2, U) == []


def test_unknown_tickers_never_block_each_other():
    assert cc.group_of("ZZZZ", U) == cc.UNKNOWN and cc.group_of("A1", U) == "Equip"
    assert cc.group_of("X", {"X": None}) == cc.UNKNOWN and cc.group_of("X", {"X": {"group": ""}}) == cc.UNKNOWN
    assert cc.capped_picks(["X1", "X2", "X3", "A1"], 4, 2, U) == ["X1", "X2", "X3", "A1"]


def test_build_and_text():
    quarters = [{"picks": ["A1", "A2", "A3", "B1", "C1"]}, {"picks": ["A1", "B1", "C1", "D1", "B2"]}, {"picks": []}]
    c = cc.build(["A1", "A2", "A3", "B1", "C1"], quarters, U)
    assert (c["group"], c["count"], c["n"]) == ("Equip", 3, 5)
    assert c["past_avg"] == pytest.approx(2.5) and c["past_3plus"] == pytest.approx(0.5)
    assert c["text"].startswith("3 of 5 picks are Equip.") and "one big bet" in c["text"]
    flat = cc.build(["A1", "B1", "C1", "D1"], [], U)
    assert flat["text"] == "All 4 picks are from different groups." and flat["past_avg"] is None
    assert cc.build([], quarters, U) is None


def test_cap_read():
    rob = [{"name": "Baseline", "cagr": 0.212}, {"name": "Max 2 per group", "cagr": 0.205}]
    assert "mostly picking stocks" in cc.cap_read(rob)["text"]
    rob[1]["cagr"] = 0.15
    assert "group timing" in cc.cap_read(rob)["text"]
    assert cc.cap_read([{"name": "Baseline", "cagr": 0.2}]) is None and cc.cap_read(None) is None


def test_weekly_question_only_at_three_or_more():
    q = weekly._concentration({"concentration": {"group": "Equip", "count": 3, "n": 5, "cap": {"text": "hint"}}})
    assert q and "3 of the 5" in q["q"] and q["hint"] == "hint" and q["link"] == "index.html#tab=paper&card=conc-card"
    assert weekly._concentration({"concentration": {"group": "Equip", "count": 2, "n": 5}}) is None
    assert weekly._concentration({}) is None


def test_demo_outputs():
    d = slim.unpack(json.loads((ROOT / "docs" / "data.json").read_text()))
    c = d.get("concentration")
    if not c:
        pytest.skip("data.json predates concentration: run python run.py --demo")
    assert c["n"] == d["top_n"] and sum(c["groups"].values()) == c["n"]
    names = [r["name"] for r in d["research"]["robustness"]]
    assert names[0] == "Baseline" and names[-1] == f"Max {cc.CAP} per group"
    assert c["cap"] and c["cap"]["base_cagr"] == pytest.approx(d["research"]["robustness"][0]["cagr"])
