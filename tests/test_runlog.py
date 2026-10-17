"""Run log + data-staleness tests."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runlog  # noqa: E402
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).resolve().parents[1]


def test_append_and_recent(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    log = tmp_path / "log.json"
    runlog.append("ok", log, when="2026-10-12 22:30 UTC")
    runlog.append("failed", log, skipped=["SMCI", "COHR"], error="SystemExit: ABORT", when="2026-10-13 22:30 UTC")
    r = runlog.recent(log)
    assert [e["status"] for e in r] == ["failed", "ok"]          # newest first
    assert r[0]["skipped"] == 2 and r[0]["skipped_tickers"] == ["COHR", "SMCI"]


def test_same_run_logged_once(tmp_path, monkeypatch):
    """run.py logs its own failure; the workflow's fallback must not add a second line."""
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    log = tmp_path / "log.json"
    runlog.append("failed", log, error="crash in run.py")
    runlog.append("failed", log, error="Failed during: pipeline")
    assert len(runlog.load(log)) == 1 and runlog.load(log)[0]["error"] == "crash in run.py"


def test_log_is_capped_and_survives_bad_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    log = tmp_path / "log.json"
    log.write_text("not json")
    assert runlog.load(log) == []
    monkeypatch.setattr(runlog, "KEEP", 5)
    for i in range(8):
        runlog.append("ok", log, when=f"day {i}")
    assert [e["when"] for e in runlog.load(log)] == [f"day {i}" for i in range(3, 8)]


CASES = [("2026-10-09", "2026-10-09", 0),   # same day
         ("2026-10-09", "2026-10-12", 1),   # Fri -> Mon
         ("2026-10-09", "2026-10-11", 0),   # Fri -> Sun (weekend doesn't count)
         ("2026-10-05", "2026-10-12", 5),   # a full week
         ("2026-10-01", "2026-10-14", 9)]


@pytest.mark.parametrize("asof,today,n", CASES)
def test_business_days_behind(asof, today, n):
    assert runlog.business_days_behind(asof, today) == n


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_dashboard_stale_days_matches_python():
    """The banner's JavaScript must agree with the Python version."""
    html = page_source()
    fn = re.search(r"function staleDays\(asof, today\)\{.*?\n\}", html, re.S).group(0)
    js = fn + "\nconsole.log(JSON.stringify(%s.map(c=>staleDays(c[0],c[1]))));" % json.dumps([c[:2] for c in CASES])
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [c[2] for c in CASES]


def test_failed_run_is_logged(tmp_path, monkeypatch):
    """A crash inside the pipeline still writes a 'failed' line, then re-raises."""
    import run
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.setattr(runlog, "DEMO_LOG", tmp_path / "demo_log.json")
    monkeypatch.setattr(sys, "argv", ["run.py", "--demo"])

    def boom(log=None):
        raise SystemExit("ABORT: no prices for 20/32 stocks")
    monkeypatch.setattr(run, "_main", boom)
    with pytest.raises(SystemExit):
        run.main()
    e = runlog.load(tmp_path / "demo_log.json")[-1]
    assert e["status"] == "failed" and "ABORT" in e["error"]
