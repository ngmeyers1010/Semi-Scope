"""Run every browser smoke test in one go.

    python tests/run_smokes.py            # all of them
    python tests/run_smokes.py tour week  # only the ones whose name contains a word

What it does:
  1. starts `python -m http.server` on a free port, serving docs/
  2. builds the sparse "first live run" fixture into a temp folder
  3. runs each tests/fixtures/*_smoke.mjs with node, passing the port as SMOKE_PORT
  4. prints one line per smoke:  ✓ name   or   ✗ name: <last error line>
  5. always stops the server and removes the temp folder, then exits 1 if any smoke failed

Where it finds things (environment variables):
  SMOKE_NODE_MODULES  a node_modules folder that contains `playwright` (checked first)
  NODE_PATH           folders searched next, then ./node_modules
  CHARTJS             path to chart.umd.js (optional; the smokes stub charts without it)
  AXE                 path to axe.min.js (needed by the a11y and practice smokes; skipped without it)
  CHROMIUM            a Chromium binary, if playwright's own download isn't there

No node or no playwright → prints why and exits 0, so it is safe to run anywhere.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
TIMEOUT = 240          # seconds per smoke


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_node_modules() -> Path | None:
    """The first node_modules folder that has playwright in it."""
    cands = [os.environ.get("SMOKE_NODE_MODULES", "")]
    cands += os.environ.get("NODE_PATH", "").split(os.pathsep)
    cands.append(str(ROOT / "node_modules"))
    for c in cands:
        if c and (Path(c) / "playwright").is_dir():
            return Path(c)
    return None


def smoke_plan(sparse: Path, tmp: Path) -> list[tuple[str, str, list[str], bool]]:
    """(label, script, argv, needs_axe) in the order they run."""
    data = str(ROOT / "docs" / "data.json")
    return [
        ("sparse (first-run data)", "sparse_smoke.mjs", [str(sparse)], False),
        ("sparse (demo data)",      "sparse_smoke.mjs", [data], False),
        ("weekly",                  "weekly_smoke.mjs", [data], False),
        ("tour",                    "tour_smoke.mjs", [data], False),
        ("a11y",                    "a11y_smoke.mjs", [data], True),
        ("week",                    "week_smoke.mjs", [data], False),
        ("practice",                "practice_smoke.mjs", [], True),
        ("explain (demo data)",     "explain_smoke.mjs", [data], False),
        ("explain (first-run data)", "explain_smoke.mjs", [str(sparse)], False),
    ]


CLUES = ("error:", "✗", "fail", "violation", "missing", "expected", "doesn't exist", "cannot", "timed out")


def last_error_line(out: str) -> str:
    """The most useful line to show for a failed smoke: the last one that looks like a complaint."""
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    for l in reversed(lines):
        if any(w in l.lower() for w in CLUES) and not l.startswith(("at ", "Node.js")):
            return l[:160]
    return lines[-1][:160] if lines else "(no output)"


def wait_for(port: int, secs: float = 10) -> bool:
    end = time.time() + secs
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main(argv: list[str]) -> int:
    node = shutil.which("node")
    if not node:
        print("skip: node is not installed, so the browser smokes can't run.")
        return 0
    nm = find_node_modules()
    if nm is None:
        print("skip: playwright not found. Set SMOKE_NODE_MODULES (or NODE_PATH) to a node_modules "
              "folder that has it:  npm install playwright")
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="semiscope_smokes_"))
    server = None
    results: list[tuple[str, bool, str]] = []
    try:
        # node resolves `import 'playwright'` next to the script, so run copies that sit beside a node_modules link
        (tmp / "node_modules").symlink_to(nm, target_is_directory=True)
        for f in FIX.glob("*_smoke.mjs"):
            shutil.copy(f, tmp / f.name)
        sparse = tmp / "sparse_data.json"
        mk = subprocess.run([sys.executable, str(FIX / "make_sparse.py"), str(sparse)], cwd=ROOT,
                            capture_output=True, text=True)
        if mk.returncode != 0:
            print(f"✗ sparse fixture: {last_error_line(mk.stdout + mk.stderr)}")
            return 1

        port = free_port()
        server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                                  cwd=ROOT / "docs", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not wait_for(port):
            print("✗ could not start the web server")
            return 1
        env = dict(os.environ, SMOKE_PORT=str(port))

        words = [w.lower() for w in argv]
        for label, script, args, needs_axe in smoke_plan(sparse, tmp):
            if words and not any(w in label.lower() for w in words):
                continue
            if needs_axe and not (env.get("AXE") and Path(env["AXE"]).is_file()):
                print(f"- {label}: skipped (set AXE=path/to/axe.min.js)")
                continue
            try:
                r = subprocess.run([node, str(tmp / script), *args], cwd=ROOT, env=env,
                                   capture_output=True, text=True, timeout=TIMEOUT)
                ok, out = r.returncode == 0, r.stdout + r.stderr
            except subprocess.TimeoutExpired:
                ok, out = False, f"timed out after {TIMEOUT}s"
            results.append((label, ok, out))
            print(f"✓ {label}" if ok else f"✗ {label}: {last_error_line(out)}", flush=True)
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    bad = sum(not ok for _, ok, _ in results)
    print(f"\n{len(results) - bad}/{len(results)} smokes passed.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
