"""Setup checklist: JS step detection matches Python; the pre-upload checker passes on this repo."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_setup  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIVE = {"mode": "live", "data_health": {"rows": [{"flags": []}]}, "my_trades": {"n_trades": 2, "demo": False}}
CASES = [
    (None, None, False, {}),                                            # local copy, nothing yet
    ({"mode": "demo"}, None, True, {}),                                 # uploaded + Pages, demo data
    (LIVE, [{"status": "ok"}], True, {}),                               # first live run
    (LIVE, [{"status": "ok"}, {"status": "failed"}], True, {"alerts": True}),
    ({**LIVE, "data_health": {"rows": [{"flags": ["Download failed this run: SEC download failed (HTTPError)"]}]}},
     [{"status": "ok"}, {"status": "ok"}], True, {}),
    ({**LIVE, "my_trades": {"n_trades": 5, "demo": True}}, [], False, {}),
]


def test_python_steps():
    d = check_setup.steps_done(*CASES[0])
    assert not any(d.values())
    d = check_setup.steps_done(*CASES[1])
    assert d["upload"] and d["pages"] and not d["firstrun"]
    d = check_setup.steps_done(*CASES[3])
    assert d["perms"] and not d["healthy"] and d["alerts"] and d["trades"]
    assert not check_setup.steps_done(*CASES[4])["secret"]          # SEC failures => secret step not done
    assert not check_setup.steps_done(*CASES[5])["trades"]          # demo trades don't count


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_python():
    js = f"""const S = require({json.dumps(str(ROOT / 'docs' / 'setup_steps.js'))});
const C = {json.dumps(CASES)};
console.log(JSON.stringify(C.map(c => S.stepsDone(c[0], c[1], {{hosted: c[2], manual: c[3]}}))));"""
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out == [check_setup.steps_done(*c) for c in CASES]


def test_check_setup_passes_on_this_repo(capsys):
    res = check_setup.checks(run_tests=False)
    bad = [(w, f) for ok, w, f in res if not ok]
    assert not bad, bad
    assert check_setup.main(["--quick"]) == 0
    assert "Ready to upload" in capsys.readouterr().out


def test_check_setup_catches_missing_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(check_setup, "ROOT", tmp_path)
    ok, what, fix = check_setup.checks(run_tests=False)[0]
    assert not ok and ".github" in fix
