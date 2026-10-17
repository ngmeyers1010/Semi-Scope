"""
Run log: one line per pipeline run (ok or failed), so you can see at a glance
whether the daily update is actually working.

- run.py appends an entry at the end of every run, including runs that crash.
- The GitHub workflow calls `python runlog.py fail "<step>"` if an earlier step
  (install, tests) failed before run.py could log anything. It skips the write
  if this run already logged itself.
- The log lives in docs/ so the dashboard can read it even when data.json is old.

    python runlog.py fail "tests"     # used by the workflow
    python runlog.py warn "slow tests failed (data was saved)"   # a failure AFTER the commit
    python runlog.py show             # print the last 10 runs
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
LOG = ROOT / "docs" / "run_log.json"
DEMO_LOG = ROOT / "state" / "run_log_demo.json"
KEEP = 200          # entries kept in the file (oldest dropped)
SHOW = 10           # entries shown on the dashboard
STALE_BUSINESS_DAYS = 4


def load(path: Path = LOG) -> list[dict]:
    """All logged runs, oldest first ([] if the file is missing or broken)."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return []


def append(status: str, path: Path = LOG, skipped: list[str] | None = None,
           error: str | None = None, mode: str = "live", when: str | None = None,
           kind: str | None = None) -> dict:
    """Add one run to the log and save it. Returns the entry."""
    run_id = os.environ.get("GITHUB_RUN_ID")
    log = load(path)
    if run_id and any(e.get("run_id") == run_id for e in log):
        return next(e for e in log if e.get("run_id") == run_id)  # already logged this run
    entry = {
        "when": when or pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC"),
        "status": status,
        "skipped": len(skipped or []),
        "skipped_tickers": sorted(skipped or []),
        "error": (error or "")[:300] or None,
        "mode": mode,
        "kind": kind,              # "full" or "fast" (fast reuses the robustness grid)
        "run_id": run_id,
    }
    log = (log + [entry])[-KEEP:]
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(log, indent=1))
    return entry


def recent(path: Path = LOG, n: int = SHOW) -> list[dict]:
    """The last n runs, NEWEST first (what the dashboard shows)."""
    return list(reversed(load(path)[-n:]))


def business_days_behind(asof: str | date, today: str | date) -> int:
    """Weekdays strictly after `asof` up to and including `today`.
    Prices dated Friday, viewed Monday -> 1 (Monday's close isn't in yet).
    The dashboard has the same function in JavaScript (staleDays); a test
    checks they agree."""
    a, t = pd.Timestamp(asof).date(), pd.Timestamp(today).date()
    n, d = 0, a
    while d < t:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def warn(text: str, path: Path = LOG) -> dict | None:
    """Attach a warning to THIS run's entry without changing its status. Used when a step
    after the data was saved fails (the slow tests): the day's data is fine, but you should
    know. Without a GITHUB_RUN_ID (or an entry for it) a separate 'failed' line is logged."""
    run_id = os.environ.get("GITHUB_RUN_ID")
    log = load(path)
    for e in reversed(log):
        if run_id and e.get("run_id") == run_id:
            e["warning"] = text[:300]
            path.write_text(json.dumps(log, indent=1))
            return e
    return append("failed", path, error=text)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "fail":
        step = sys.argv[2] if len(sys.argv) > 2 else "unknown step"
        e = append("failed", error=f"Failed during: {step}")
        print("logged:", e)
    elif cmd == "warn":
        e = warn(sys.argv[2] if len(sys.argv) > 2 else "a step after saving the data failed")
        print("logged:", e)
    else:
        for e in recent():
            print(f"{e['when']}  {e['status']:6s}  skipped {e['skipped']}  {e.get('error') or ''}")
