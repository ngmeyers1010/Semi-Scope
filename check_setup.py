"""
Before you upload: checks this folder is complete and working.

    python check_setup.py            # full check, including the tests (~1-2 min)
    python check_setup.py --quick    # skip the tests

Prints a ✓ / ✗ list and exits with 1 if anything needs fixing.
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
REQUIRED = [
    ".github/workflows/update.yml", "requirements.txt", "config.py", "run.py", "data_sources.py",
    "fundamentals.py", "factors.py", "backtest.py", "paper.py", "docs/index.html", "docs/setup.html",
    "docs/setup_steps.js", "docs/sw.js", "docs/manifest.webmanifest", "docs/icon-192.png", "state/my_trades.csv", "tests/test_pipeline.py", "reports/README.md",
    "pytest.ini", "docs/weekly.html", "docs/LAUNCH.md", "docs/detail.json", "state/my_stocks.csv",
    "docs/journal.md",
]
PACKAGES = {"pandas": "pandas", "numpy": "numpy", "requests": "requests", "yfinance": "yfinance", "pytest": "pytest"}


def steps_done(data: dict | None, runlog: list | None, hosted: bool = False, manual: dict | None = None) -> dict:
    """Python mirror of stepsDone() in docs/setup_steps.js."""
    live = bool(data) and data.get("mode") == "live"
    log = runlog if isinstance(runlog, list) else []
    rows = ((data or {}).get("data_health") or {}).get("rows") or []
    failed = sum(any(re.search(r"SEC download failed|SEC ticker list", f) for f in r.get("flags", [])) for r in rows) if live else 0
    hosted = hosted or live
    mt = (data or {}).get("my_trades") or {}
    return {
        "upload": hosted, "pages": hosted,
        "secret": live and failed == 0,
        "perms": len(log) >= 2,
        "firstrun": live,
        "healthy": len(log) > 0 and log[-1].get("status") == "ok",
        "alerts": bool((manual or {}).get("alerts")),
        "trades": live and bool(mt) and not mt.get("demo") and (mt.get("n_trades") or 0) > 0,
    }


def checks(run_tests: bool = True) -> list[tuple[bool, str, str]]:
    """(ok, what, how-to-fix) for each check."""
    out = []
    missing = [f for f in REQUIRED if not (ROOT / f).exists()]
    out.append((not missing, "All required files present",
                "Missing: " + ", ".join(missing) + ". The .github folder is hidden on Mac: press Cmd+Shift+. in Finder."))
    try:
        sys.path.insert(0, str(ROOT))
        cfg = importlib.import_module("config")
        out.append((True, "config.py loads", ""))
        ua = getattr(cfg, "SEC_USER_AGENT_DEFAULT", "")
        out.append((bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", ua)), "SEC contact email set in config.py",
                    "Put your email in SEC_USER_AGENT_DEFAULT; the SEC blocks requests without one."))
        n_sec = sum(1 for m in cfg.UNIVERSE.values() if m.get("sec"))
        out.append((len(cfg.UNIVERSE) >= cfg.TOP_N * 2 and n_sec > 0, f"Universe has {len(cfg.UNIVERSE)} stocks",
                    "UNIVERSE needs at least twice TOP_N stocks."))
    except Exception as e:  # noqa: BLE001
        out.append((False, "config.py loads", f"{type(e).__name__}: {e}"))
    missing_pk = [p for p, mod in PACKAGES.items() if importlib.util.find_spec(mod) is None]
    out.append((not missing_pk, "Python packages installed",
                f"Run: pip install -r requirements.txt (missing: {', '.join(missing_pk)})"))
    wf = (ROOT / ".github/workflows/update.yml")
    if wf.exists():
        t = wf.read_text()
        out.append(("SEC_USER_AGENT" in t and "deploy-pages" in t, "Workflow file looks complete",
                    "Re-copy .github/workflows/update.yml from the zip."))
    if run_tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT, capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        out.append((r.returncode == 0, f"Tests pass ({last})", "Paste the pytest output to Claude."))
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    res = checks(run_tests="--quick" not in argv)
    for ok, what, fix in res:
        print(f"{'✓' if ok else '✗'} {what}" + ("" if ok else f"\n    → {fix}"))
    bad = sum(not ok for ok, _, _ in res)
    print("\nReady to upload! Next: docs/setup.html walks you through GitHub." if not bad else f"\n{bad} thing(s) to fix first.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
