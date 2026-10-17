"""Build a 'first real run' style data.json from the demo one: fields that a fresh
live run won't have yet are stripped or emptied. Used by the browser smoke test
(tests/fixtures/sparse_smoke.mjs) to make sure no tab crashes on missing data.

    python run.py --demo && python tests/fixtures/make_sparse.py
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def sparse(d: dict) -> dict:
    sys.path.insert(0, str(ROOT))
    import slim
    d = slim.unpack(copy.deepcopy(d))
    d["mode"] = "live"
    d["paper"] = None                                    # paper portfolio hasn't started
    d["reports"] = []                                    # no finished quarter yet
    d["run_log"] = []
    d["my_trades"] = {"n_trades": 0, "errors": [], "demo": False, "file": "my_trades.csv"}
    d["confidence"] = {"backtest": d["confidence"]["backtest"], "paper": None, "dsr": None}
    d["since"] = {"first": True, "items": [], "moved": {}, "text": "Welcome!"}
    d["alert_log"], d["alerts"] = [], []
    d["moves"] = {}
    d.pop("explain", None)
    d["research"].pop("oos", None)
    # a holding whose prices failed today, and a typo'd one
    for h in d["holdings"]:
        if h["ticker"] in ("MU", "GOOGL"):
            h["current"], h["rank_history"] = None, []
    d["my_stocks"] = {**d.get("my_stocks", {}), "unknown": ["ZZZZ"], "problems": []}
    # a foreign filer: no SEC history, no earnings/filing info, no 1y prices
    for r in d["rankings"] + d["watchlist"]:
        if r["ticker"] in ("ASML", "TSM", "AMZN"):
            r["history"], r["earnings"], r["filing"] = [], None, None   # (detail.json is ignored here)
            r.pop("px_1y", None)
            r["z"] = {k: None for k in r["z"]}
    # a stock with a missing last price bar
    for r in d["rankings"][:2]:
        r["stale_days"] = 2
    d["my_stocks"]["stale"] = {"NVDA": 2}
    d["groups"] = None                                   # older data.json without the groups block
    d.pop("steady", None)                                # older data.json without the steady block
    d["earnings_cal"] = {"asof": d.get("prices_asof"), "rows": []}   # no estimates yet
    d["rebalance"] = None                                # paper portfolio not started yet
    d["research"].pop("start_luck", None)                # older data.json without it
    d["upcoming_filings"] = []
    d.pop("walkthrough", None)                           # older data.json without it
    d.pop("z_stats", None)
    d["research"].pop("decay", None)
    d.pop("concentration", None)
    d.pop("score_moves", None)
    d.pop("capture", None)
    d.pop("drawdowns", None)
    d.pop("outcomes", None)
    # a sanity flag like a live run would add (text must be escaped when shown)
    row = d["data_health"]["rows"][0]
    row["sanity"] = ["Q2 2026 revenue is about 1,000× the quarters before it: probably a units error, ignored <b>"]
    row["flags"] = row["flags"] + row["sanity"]                         # older data.json without it                     # older data.json without it
    return d


if __name__ == "__main__":
    src = ROOT / "docs" / "data.json"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tests" / "fixtures" / "sparse_data.json"
    out.write_text(json.dumps(sparse(json.loads(src.read_text()))))
    print("wrote", out)
