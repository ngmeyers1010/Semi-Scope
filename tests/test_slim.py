"""Phone-friendly data.json: split/pack round-trip, size budget, JS unpack matches Python."""
import gzip
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import slim
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).parents[1]


def sample():
    return {
        "backtest": {"curves": {"strategy": [["2020-01-03", 1.0], ["2020-01-10", 1.1]],
                                "SPY": [["2020-01-10", 1.05]]}},
        "research": {"ic": {"a": [["2020-03-01", 0.1], ["2020-06-01", None]],
                            "b": [["2020-03-01", None], ["2020-06-01", -0.2]]}},
        "rankings": [{"ticker": "MU", "score": 0.4, "history": [{"q": "2026-06-30", "rev": 1.0}],
                      "px_1y": [["2026-01-02", 90.0]], "earnings": {"avg_abs": 0.05, "n": 8}}],
        "watchlist": [{"ticker": "AMZN", "history": []}],
        "holdings": [{"ticker": "MU", "current": {"ticker": "MU", "history": [], "px_1y": []}},
                     {"ticker": "ZZ", "current": None}],
        "single": {"only": [["2020-01-01", 1.0]]},
    }


def test_pack_unpack_roundtrip_keeps_nulls():
    s = sample()
    p = slim.pack(json.loads(json.dumps(s)))
    assert p["backtest"]["curves"]["_d"] == ["2020-01-03", "2020-01-10"]
    assert p["research"]["ic"]["_same"] == 1                  # identical dates: nulls survive
    assert "_d" not in p["single"]                             # a lone series isn't packed
    assert slim.unpack(p) == s


def test_split_merge_roundtrip():
    s = sample()
    data, det = slim.split(json.loads(json.dumps(s)))
    r = data["rankings"][0]
    assert "history" not in r and "px_1y" not in r and r["earn_avg_abs"] == 0.05
    assert "history" not in data["holdings"][0]["current"]
    back = slim.merge(data, det)
    assert back["rankings"][0]["history"] == s["rankings"][0]["history"]
    assert back["holdings"][0]["current"]["px_1y"] == s["rankings"][0]["px_1y"]   # holdings reuse the ranking row


GZ_BUDGET = 70_000          # ~70 KB over the wire: loads in well under a second on 4G


def test_real_file_budget_and_roundtrip():
    """The shipped data.json stays small for phones: under GZ_BUDGET bytes gzipped (what actually
    travels), and the slim tricks still save a third or more vs the unpacked, unsplit version.
    (Until round 67 this was only a 0.6 ratio. That ratio rises with every compact new card even
    when the file is fine, so the absolute size is now the main limit.)"""
    p, dp = ROOT / "docs" / "data.json", ROOT / "docs" / "detail.json"
    if not p.exists() or not dp.exists():
        pytest.skip("run python run.py --demo first")
    small = p.read_text()
    full = json.dumps(slim.merge(slim.unpack(json.loads(small)), json.loads(dp.read_text())), separators=(",", ":"))
    # Loose guard only: demo data packs to ~0.55 of the full size, real data to ~0.63. The gzipped
    # budget below is what actually matters for phones.
    assert len(small) <= 0.7 * len(full), (len(small), len(full))
    gz_small, gz_full = len(gzip.compress(small.encode())), len(gzip.compress(full.encode()))
    assert gz_small <= GZ_BUDGET, f"data.json is {gz_small:,} bytes gzipped (budget {GZ_BUDGET:,})"
    assert gz_small <= 0.67 * gz_full, (gz_small, gz_full)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_unpack_matches_python():
    html = page_source()
    block = re.search(r"// ---- slim .*?// ---- end slim ----", html, re.S).group(0)
    s = sample()
    data, det = slim.split(json.loads(json.dumps(s)))
    packed = slim.pack(data)
    js = block + "\nconst P=%s, DET=%s;console.log(JSON.stringify(mergeDetail(unpackPairs(P), DET)));" % (
        json.dumps(packed), json.dumps(det))
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out == slim.merge(slim.unpack(packed), det)
