"""Where the dashboard's JavaScript lives, for tests that run pieces of it in node.

The pure helper blocks ("// ---- name ----" ... "// ---- end name ----") moved from docs/index.html
to docs/helpers.js in round 98. Tests read page_source() (both files) or js_block("name"), so a
block can move between the two files again without touching every test.
"""
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
FILES = ("index.html", "helpers.js")


def page_source() -> str:
    """index.html followed by helpers.js: everything the dashboard runs."""
    return "\n".join((DOCS / f).read_text() for f in FILES if (DOCS / f).exists())


def js_block(name: str) -> str:
    """The text between '// ---- name' and '// ---- end name ----', from whichever file has it."""
    pat = re.compile(rf"// ---- {re.escape(name)}\b.*?// ---- end {re.escape(name)} ----", re.S)
    for f in FILES:
        m = pat.search((DOCS / f).read_text())
        if m:
            return m.group(0)
    raise KeyError(f"no '// ---- {name} ----' block in {FILES}")
