"""Side-by-side compare: gap math, sum to score difference, JS/Python match, hash parsing."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import explain
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).parents[1]
F = {"mom": {"weight": 2.0, "label": "Price momentum (12-1m)"},
     "gm": {"weight": 1.0, "label": "Gross margin"},
     "val": {"weight": 1.0, "label": "Sales yield"},
     "info": {"weight": 0.0, "label": "Info only"}}


def score(z):
    w = {f: c["weight"] for f, c in F.items() if c["weight"] > 0 and z.get(f) is not None}
    return sum(w[f] * z[f] for f in w) / sum(w.values())


A = {"ticker": "AAA", "z": {"mom": 1.0, "gm": 0.5, "val": -1.0, "info": 3.0}}
B = {"ticker": "BBB", "z": {"mom": -0.5, "gm": 0.5, "val": 1.0, "info": -3.0}}
C = {"ticker": "CCC", "z": {"mom": 0.2, "gm": None, "val": 0.1}}


def test_gap_math_by_hand():
    c = explain.compare(A, B, F)
    g = {x["factor"]: x["gap"] for x in c["gaps"]}
    # same factor set, W = 4: gap = w * (zA - zB) / 4
    assert g["mom"] == pytest.approx(2 * 1.5 / 4)
    assert g["gm"] == pytest.approx(0.0)
    assert g["val"] == pytest.approx(1 * -2.0 / 4)
    assert "info" not in g                                   # weight 0 never counts
    assert [x["factor"] for x in c["top"]][:2] == ["mom", "val"]


def test_gaps_sum_to_score_difference_even_with_missing_factors():
    for a, b in [(A, B), (A, C), (C, B)]:
        c = explain.compare(a, b, F)
        assert sum(x["gap"] for x in c["gaps"]) == pytest.approx(score(a["z"]) - score(b["z"]))
        assert c["diff"] == pytest.approx(score(a["z"]) - score(b["z"]))


def test_sentence():
    s = explain.compare(A, B, F)["sentence"]
    assert s.startswith("AAA scores 0.25 above BBB, mostly from Price momentum (0.75)")
    assert "BBB is better on Sales yield (0.50)" in s
    s2 = explain.compare(B, A, F)["sentence"]
    assert s2.startswith("AAA scores 0.25 above BBB")


def _js(names):
    html = page_source()
    block = re.search(r"// ---- compare .*?// ---- end compare ----", html, re.S).group(0)
    return block


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_matches_python():
    pairs = [(A, B), (A, C), (C, B), (B, A)]
    js = _js(None) + "\nconst F=%s, P=%s;\nconsole.log(JSON.stringify(P.map(p=>compareStocks(p[0],p[1],F))));" % (
        json.dumps(F), json.dumps(pairs))
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    for (a, b), j in zip(pairs, out):
        p = explain.compare(a, b, F)
        assert j["diff"] == pytest.approx(p["diff"])
        assert [g["factor"] for g in j["gaps"]] == [g["factor"] for g in p["gaps"]]
        assert [g["gap"] for g in j["gaps"]] == pytest.approx([g["gap"] for g in p["gaps"]])


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_hash_parsing_ignores_unknown():
    cases = ["#compare=nvda,ZZZZ,amd", "#compare=NVDA,NVDA,AMD,MU,INTC", "#other=1", "", "#x=1&compare=MU%2CAMD"]
    js = _js(None) + "\nconst K=['NVDA','AMD','MU','INTC'];console.log(JSON.stringify(%s.map(h=>parseCompareHash(h,K))));" % json.dumps(cases)
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out == [["NVDA", "AMD"], ["NVDA", "AMD", "MU"], [], [], ["MU", "AMD"]]
