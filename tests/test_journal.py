"""Weekly page journal: docs/journal.md parsing (the JS in weekly.html), escaping, setup check."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PAGE = (ROOT / "docs" / "weekly.html").read_text()


def _parse(text, n=3):
    js_fn = re.search(r"// journal:start\n(.*?)// journal:end", PAGE, re.S).group(1)
    js = js_fn + f"\nconsole.log(JSON.stringify(parseJournal({json.dumps(text)}, {n})));"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_last_three_dated_entries_newest_first():
    text = ("# Title\nintro text is ignored\n\n## 2026-10-01\nfirst\n\n## 2026-10-15\nthird <b>bold</b>\nline 2\n"
            "## not a date\nstill part of 10-15\n## 2026-10-08\nsecond\n## 2026-10-22\n\n## 2026-09-01\nold\n")
    got = _parse(text)
    assert [e["date"] for e in got] == ["2026-10-15", "2026-10-08", "2026-10-01"]   # empty 10-22 skipped
    assert got[0]["body"].startswith("third <b>bold</b>\nline 2") and "## not a date" in got[0]["body"]
    assert _parse("no headings at all") == [] and _parse("") == []
    assert len(_parse(text, 10)) == 4


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_shipped_journal_parses():
    got = _parse((ROOT / "docs" / "journal.md").read_text())
    assert got and re.fullmatch(r"\d{4}-\d{2}-\d{2}", got[0]["date"])


def test_page_escapes_and_hides_by_default():
    assert 'id="journal-card" hidden' in PAGE
    assert "${hEsc(e.date)}" in PAGE and "${hEsc(e.body.replace(" in PAGE          # never raw markdown/HTML
    assert "fetch('journal.md?" in PAGE and ".catch(()=>{})" in PAGE         # missing file: card stays hidden


def test_check_setup_requires_journal():
    import check_setup
    assert "docs/journal.md" in check_setup.REQUIRED
