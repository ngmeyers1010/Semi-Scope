"""
Dry-run of the LIVE pipeline (python run.py, no --demo) without the internet.

Nothing in SemiScope has run on real SEC/Yahoo data yet, and the demo path skips
load_live() entirely. This script fakes the two outside services at the lowest
level, so the real download/parsing code still runs:

  * Yahoo:  a fake `yfinance` module whose download() returns the same shape the
            real one does (columns = (field, ticker) MultiIndex, tz-aware dates).
  * SEC:    data_sources._get_json() is swapped for a function that serves the
            company_tickers.json list and companyfacts JSON for each CIK.

Realistic quirks baked in (each one has bitten a real pipeline somewhere):
  1. a typo in my_stocks.csv (NVDAA): Yahoo returns an all-NaN column for it
  2. a stale last bar: MU's last 2 prices are missing (Yahoo hiccup)
  3. a 10:1 stock split (every 4th stock, like the demo) with raw share counts
  4. foreign filers (ASML, TSM) — no SEC data, price factors only
  5. a stock whose SEC download fails (HTTP 500 after retries): ADI
  6. a stock missing from the SEC ticker list: SWKS
  7. a 53-week fiscal year + duplicates + restatements: AAPL uses the round-17
     fixture tests/fixtures/aapl_like.json (old data, so it's "stale" too)
  8. Yahoo returns the first batch with a transient error (the retry path)

Usage:
    python tests/fixtures/live_sim.py [workdir]     # prints a summary
    from tests.fixtures.live_sim import simulate    # used by tests/test_live_sim.py

The run happens in a COPY of the repo inside `workdir`, so your real
docs/data.json, state/ and reports/ are never touched.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

TYPO = "NVDAA"
STALE = "MU"
SEC_FAILS = "ADI"
NOT_IN_SEC = "SWKS"
UNITS = "LRCX"            # its latest 10-Q revenue is filed in thousands of dollars by mistake (×1000)
FIXTURE_FOR = {"AAPL": "aapl_like.json"}
DAY1, DAY2 = "2026-10-12", "2026-10-13"      # two runs on consecutive trading days

# Runs inside the copied repo (a fresh Python process, so module state is clean).
RUNNER = r'''
import json, sys, types
from pathlib import Path
import numpy as np
import pandas as pd

END, FAST = sys.argv[1], "--fast" in sys.argv
CFG = json.loads(Path("_sim_config.json").read_text())

import config, demo_data
tickers = list(config.UNIVERSE) + list(config.WATCHLIST)
raw = {}
# one fixed "world" (through the last sim day), cut off at END: day 2 sees day 1's data plus one bar
_, px, bench, _, splits = demo_data.generate(tickers, list(config.BENCHMARKS), config.BACKTEST_START,
                                             return_market=True, end=CFG["last_day"], raw_facts=raw)
px, bench, splits = px.loc[:END].copy(), bench.loc[:END], splits.loc[:END]
for facts in raw.values():                                   # only filings made by END
    for tag in facts["facts"]["us-gaap"].values():
        tag["units"]["USD"] = [f for f in tag["units"]["USD"] if f["filed"] <= END]
for t, fname in CFG["fixture_for"].items():
    raw[t] = json.loads(Path(CFG["fixtures"], fname).read_text())
# quirk 9: a units error. The latest quarterly revenue fact for one company is 1,000x too big
rev = raw[CFG["units"]]["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]
q = max((f for f in rev if f["form"] == "10-Q"), key=lambda f: (f["end"], f["filed"]))
q["val"] *= 1000

px = px.drop(columns=[CFG["typo"]], errors="ignore")       # Yahoo has never heard of it
# prices are split-ADJUSTED (like Yahoo); a dividend-free "Close" is the same series here
px.loc[px.index[-2]:, CFG["stale"]] = np.nan            # quirk 2: stale last bars

calls = {"n": 0}
def fake_download(tickers, start=None, auto_adjust=False, actions=True, progress=False, threads=True):
    calls["n"] += 1
    if calls["n"] == 1:
        raise ConnectionError("simulated Yahoo timeout")    # quirk 8: retry path
    idx = px.index[px.index >= pd.Timestamp(start)]
    cols, data = [], {}
    for t in tickers:
        if t in px:
            s = px.loc[idx, t]
        elif t in bench:
            s = bench.loc[idx, t]
        else:
            s = pd.Series(np.nan, index=idx)                # quirk 1: unknown ticker -> all-NaN
        sp = splits[t].reindex(idx).fillna(0.0) if t in splits else pd.Series(0.0, index=idx)
        for field, v in (("Adj Close", s), ("Close", s), ("Stock Splits", sp),
                         ("Dividends", pd.Series(0.0, index=idx)), ("Volume", pd.Series(1e6, index=idx))):
            data[(field, t)] = v.values
    df = pd.DataFrame(data, index=idx.tz_localize("America/New_York"))
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["Price", "Ticker"])
    return df

yf = types.ModuleType("yfinance")
yf.download = fake_download
sys.modules["yfinance"] = yf

import data_sources as ds
ds.time.sleep = lambda s: None
ciks = {t: 1000 + i for i, t in enumerate(tickers) if t != CFG["not_in_sec"]}
ciks.pop(CFG["typo"], None)                                   # a typo isn't in the SEC list either

class HTTPError(Exception):
    pass

def fake_get_json(url, cache_file, max_age_hours=20):
    if url.endswith("company_tickers.json"):
        return {str(i): {"cik_str": c, "ticker": t, "title": t} for i, (t, c) in enumerate(ciks.items())}
    cik = int(url.rsplit("CIK", 1)[1][:10])
    t = next(k for k, v in ciks.items() if v == cik)
    if t == CFG["sec_fails"]:
        raise HTTPError("500 Server Error (simulated)")     # quirk 5
    return raw[t]

ds._get_json = fake_get_json

import run
sys.argv = ["run.py"] + (["--fast"] if FAST else [])
run.main()
'''


def _reset_to_demo_data(dst: Path) -> None:
    """Make the copy look like a brand-new install, even if the real repo holds LIVE data.

    On GitHub the daily pipeline runs BEFORE the slow tests, so docs/data.json is already live
    (with today's alerts) by the time this simulation copies the repo. The test expects the
    shipped DEMO data, so if the copy is not demo, rebuild demo data inside the copy.
    """
    data_file = dst / "docs" / "data.json"
    try:
        is_demo = json.loads(data_file.read_text()).get("mode") == "demo"
    except (OSError, ValueError):
        is_demo = False
    if is_demo:
        return
    for rel in ("docs/data.json", "docs/detail.json"):
        (dst / rel).unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, "run.py", "--demo"], cwd=dst, env=env, check=True,
                   capture_output=True, text=True, timeout=300)


def _copy_repo(dst: Path) -> None:
    ignore = shutil.ignore_patterns("tests", "cache", ".git", "__pycache__", "reports_demo", "*.zip",
                                    "node_modules", ".pytest_cache")
    shutil.copytree(REPO, dst, ignore=ignore)
    _reset_to_demo_data(dst)
    # a brand-new install: the DEMO data.json/detail.json from the zip are still there (as on
    # GitHub before the first real run), but no run log, paper portfolio or reports
    for rel in ("docs/run_log.json", "state/paper_portfolio.json",
                "state/prev_snapshot.json", "state/digest.md", "state/alerts.md"):
        (dst / rel).unlink(missing_ok=True)
    for p in (dst / "state").glob("*_demo*"):
        p.unlink()
        # the rehearsal checks the price-only path; hand-entered data is tested in test_foreign.py
    (dst / "state" / "foreign_fundamentals.csv").unlink(missing_ok=True)
    for p in (dst / "reports").glob("*.md"):
        if p.name != "README.md":
            p.unlink()
       
    # your list, with a typo in it
    with open(dst / "state" / "my_stocks.csv", "a") as f:
        f.write(f"\n{TYPO},watch,typo on purpose\n")
    with open(dst / "state" / "my_trades.csv", "a") as f:
        f.write("\n2025-03-03,NVDA,buy,10,110.50,first buy\n2025-06-02,AMD,buy,5,115.00,\n")


def simulate(workdir: str | Path, timeout: int = 300) -> dict:
    """Run the live pipeline twice (day 1 full, day 2 --fast) in a copy of the repo.
    Returns {'repo': Path, 'logs': [stdout1, stdout2], 'codes': [rc1, rc2]}."""
    workdir = Path(workdir)
    repo = workdir / "repo"
    if repo.exists():
        shutil.rmtree(repo)
    _copy_repo(repo)
    (repo / "_sim_config.json").write_text(json.dumps({
        "fixtures": str(HERE), "last_day": DAY2, "fixture_for": FIXTURE_FOR, "stale": STALE, "typo": TYPO,
        "sec_fails": SEC_FAILS, "not_in_sec": NOT_IN_SEC, "units": UNITS}))
    (repo / "_sim_runner.py").write_text(RUNNER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    logs, codes = [], []
    for end, extra in ((DAY1, []), (DAY2, ["--fast"])):
        p = subprocess.run([sys.executable, "_sim_runner.py", end, *extra], cwd=repo, env=env,
                           capture_output=True, text=True, timeout=timeout)
        logs.append(p.stdout + p.stderr)
        codes.append(p.returncode)
        if p.returncode:
            break
    return {"repo": repo, "logs": logs, "codes": codes}


if __name__ == "__main__":
    import tempfile
    wd = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="semiscope_live_"))
    r = simulate(wd)
    for i, (log, rc) in enumerate(zip(r["logs"], r["codes"]), 1):
        print(f"===== run {i} (exit {rc}) =====\n{log[-3000:]}")
    print("Output in", r["repo"])
