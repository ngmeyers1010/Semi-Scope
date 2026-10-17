"""'How did #1 get its score?': the walkthrough's arithmetic must reproduce the stored scores."""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import factors  # noqa: E402
import slim  # noqa: E402
import walkthrough  # noqa: E402


@pytest.fixture(scope="module")
def data():
    d = slim.unpack(json.loads((ROOT / "docs" / "data.json").read_text()))
    if not d.get("z_stats"):
        pytest.skip("data.json predates z_stats: run python run.py --demo")
    return d


def test_every_ranked_score_is_reproduced(data):
    ranked = [r for r in data["rankings"] if r.get("rank") is not None]
    assert len(ranked) >= 10
    for r in ranked:
        rb = walkthrough.rebuild(r, data["factors"], data["z_stats"])
        assert rb["score"] is not None and abs(rb["score"] - r["score"]) < 0.01, (r["ticker"], rb["score"], r["score"])


def test_steps_for_number_one(data):
    s = walkthrough.steps(data)
    top = min((r for r in data["rankings"] if r.get("rank") is not None), key=lambda r: r["rank"])
    assert [x["title"][:2] for x in s] == ["1.", "2.", "3.", "4.", "5."]
    assert top["ticker"] in s[0]["title"]
    assert f"{top['score']:+.2f}" in s[2]["body"]
    assert "− -" not in s[1]["body"]                  # negative means shown as (−x), not "− -x"
    assert s[-1]["expect"] == f"{top['score']:.2f}" and len(s[-1]["code"].splitlines()) <= 8


def test_snippet_prints_the_stored_score(data, tmp_path, monkeypatch):
    s = walkthrough.steps(data)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "data.json").write_text((ROOT / "docs" / "data.json").read_text())
    monkeypatch.chdir(tmp_path)
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(s[-1]["code"], {})
    assert buf.getvalue().strip() == s[-1]["expect"]


def test_hand_made_example():
    fac = {"a": {"weight": 2.0, "sign": 1, "label": "A (x)"}, "b": {"weight": 1.0, "sign": -1, "label": "B"},
           "c": {"weight": 0.0, "sign": 1, "label": "C"}}
    zs = {"a": {"lo": 0.0, "hi": 0.5, "mean": 0.1, "sd": 0.2}, "b": {"lo": 0, "hi": 1, "mean": 0.5, "sd": 0.25},
          "c": {"lo": 0, "hi": 1, "mean": 0.5, "sd": 0.1}}
    rb = walkthrough.rebuild({"raw": {"a": 0.9, "b": 0.25, "c": 1.0}}, fac, zs)
    # a clipped to 0.5 -> z=2.0; b: (0.25-0.5)/0.25 = -1 -> flipped +1; c ignored (weight 0)
    assert [r["factor"] for r in rb["rows"]] == ["a", "b"] and rb["rows"][0]["label"] == "A"
    assert rb["score"] == pytest.approx((2 * 2.0 + 1 * 1.0) / 3)
    assert walkthrough.rebuild({"raw": {"a": None}}, fac, zs)["score"] is None


def test_z_stats_matches_the_scorer():
    col = pd.Series([0.0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 100.0])
    st = factors.z_stats(col)
    assert st["hi"] < 100 and st["lo"] >= 0
    z = (col.clip(st["lo"], st["hi"]) - st["mean"]) / st["sd"]
    assert z.round(10).tolist() == factors._z(col).round(10).tolist()


def test_missing_inputs_return_none():
    assert walkthrough.steps({}) is None
    assert walkthrough.steps({"rankings": [{"ticker": "X", "rank": 1, "raw": {}}], "factors": {}, "z_stats": {}}) is None
