"""The daily GitHub Action: quick tests guard the data, slow tests run after it's saved,
every step has a timeout, and failures are logged under the right step name."""
import re
from pathlib import Path

import pytest

import runlog

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "update.yml"


def steps():
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(WF.read_text())["jobs"]["update"]["steps"]


def _idx(name_part):
    return next(i for i, s in enumerate(steps()) if name_part in (s.get("name") or s.get("uses") or s.get("id") or ""))


def test_order_fast_tests_pipeline_commit_slow_tests():
    order = [_idx("Run tests"), _idx("Run pipeline"), _idx("Commit results"), _idx("Run slow tests")]
    assert order == sorted(order)
    st = steps()
    assert '-m "not slow"' in st[_idx("Run tests")]["run"]
    assert "-m slow" in st[_idx("Run slow tests")]["run"]
    assert "continue-on-error" not in st[_idx("Run slow tests")]        # a failure must still fail the job


def test_every_step_has_a_timeout_and_budgets_fit():
    st = steps()
    missing = [s.get("name") or s.get("uses") or s.get("id") for s in st if "timeout-minutes" not in s]
    assert not missing, missing
    assert st[_idx("Run tests")]["timeout-minutes"] <= 8 and st[_idx("Run pipeline")]["timeout-minutes"] <= 20
    import yaml
    job = yaml.safe_load(WF.read_text())["jobs"]["update"]["timeout-minutes"]
    assert job >= sum(s["timeout-minutes"] for s in st if s.get("name", "").startswith("Run "))


def test_failure_logging_names_each_step():
    text = WF.read_text()
    log_step = steps()[_idx("Log the failed run")]["run"]
    for f in ("slow_test_output.txt", "run_output.txt", "test_output.txt"):
        assert f in log_step and f in text.split("Log the failed run")[0]   # written by an earlier step
    assert 'runlog.py warn' in log_step and 'runlog.py fail "$STEP"' in log_step
    assert "steps.commit.outcome == 'success'" in text          # alerts still go out after a slow-test failure


def test_slow_marker_registered_and_used():
    ini = (WF.parents[2] / "pytest.ini").read_text()
    assert re.search(r"^\s+slow:", ini, re.M)
    assert "pytestmark = pytest.mark.slow" in (WF.parents[2] / "tests" / "test_live_sim.py").read_text()


def test_runlog_warn_annotates_this_run(tmp_path, monkeypatch):
    log = tmp_path / "log.json"
    monkeypatch.setenv("GITHUB_RUN_ID", "777")
    runlog.append("ok", log, when="2026-10-15 22:30 UTC")
    e = runlog.warn("slow tests failed after the data was saved", log)
    assert e["status"] == "ok" and "slow tests" in e["warning"] and len(runlog.load(log)) == 1
    monkeypatch.setenv("GITHUB_RUN_ID", "778")                       # no entry for this run yet
    e2 = runlog.warn("something", log)
    assert e2["status"] == "failed" and len(runlog.load(log)) == 2


def test_practice_page_step_runs_after_tests_and_never_fails_the_job():
    st = steps()
    i = _idx("Update practice progress page")
    assert _idx("Run tests") < _idx("Run pipeline") < i < _idx("Commit results")
    run = st[i]["run"]
    assert "python practice/check.py --html" in run and "||" in run          # can't fail the job
    assert st[i].get("timeout-minutes", 99) <= 3
    assert "docs/practice.html" in st[_idx("Commit results")]["run"]
    # --html exits 0 with every exercise unfinished (the starter files)
    import subprocess
    import sys
    from pathlib import Path as _P
    root = _P(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, str(root / "practice" / "check.py"), "--html", "/dev/null"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
