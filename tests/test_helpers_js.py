"""docs/helpers.js: the dashboard's pure helper blocks, loaded before the page script."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from _jsblocks import DOCS, js_block

BLOCKS = ["explain tile", "ink", "since", "streaks", "valpct", "ranksort", "compare", "slim", "underwater",
          "week diff", "lots", "tour", "jump chips"]


def test_blocks_live_in_helpers_js_once_and_page_loads_it_first():
    page, helpers = (DOCS / "index.html").read_text(), (DOCS / "helpers.js").read_text()
    for b in BLOCKS:
        assert helpers.count(f"// ---- end {b} ----") == 1 and f"// ---- end {b} ----" not in page, b
        assert js_block(b).startswith(f"// ---- {b}")
    scripts = re.findall(r"<script(?: src=\"([^\"]+)\")?>", page)
    assert scripts.index("helpers.js") < scripts.index("")            # before the first inline script
    sw = (DOCS / "sw.js").read_text()
    assert "'helpers.js'" in sw and "semiscope-v5" in sw


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_helpers_js_runs_on_its_own():
    """Only definitions at the top level: loading it touches no page globals."""
    out = subprocess.run(["node", "-e", (DOCS / "helpers.js").read_text() +
                          "\nconsole.log([typeof explainTile, typeof weekDiff, typeof unpackPairs, typeof inkOn].join(','))"],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert out == "function,function,function,function"


def test_js_block_errors_clearly():
    with pytest.raises(KeyError):
        js_block("no such block")
