"""Static accessibility checks on the HTML files (no browser): the full axe-core audit is
tests/fixtures/a11y_smoke.mjs. These catch the regressions that are easy to see in source."""
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

DOCS = Path(__file__).resolve().parents[1] / "docs"
PAGES = ["index.html", "weekly.html", "setup.html"]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.problems, self._btn = [], [], None
        self.labels_for = set()
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "label" and a.get("for"):
            self.labels_for.add(a["for"])
        if tag == "button":
            self._btn = {"attrs": a, "text": ""}
        if tag in ("img", "canvas") and not (a.get("alt") or a.get("aria-label") or a.get("aria-labelledby")):
            self.problems.append(f"<{tag} id={a.get('id')!r}> has no alt/aria-label")
        if tag in ("input", "select", "textarea") and a.get("type") != "hidden":
            self.inputs.append(a)

    def handle_data(self, data):
        if self._btn is not None:
            self._btn["text"] += data

    def handle_endtag(self, tag):
        if tag == "button" and self._btn is not None:
            a = self._btn["attrs"]
            # buttons filled in by script are fine if they have an id the script writes to
            if not (self._btn["text"].strip() or a.get("aria-label") or a.get("title")):
                self.problems.append(f"<button id={a.get('id')!r}> has no text or aria-label")
            self._btn = None


@pytest.mark.parametrize("page", PAGES)
def test_static_accessibility(page):
    html = (DOCS / page).read_text()
    s = Scan()
    s.feed(html)
    dupes = sorted({i for i in s.ids if s.ids.count(i) > 1})
    assert not dupes, f"duplicate ids in {page}: {dupes}"
    assert not s.problems, s.problems
    for a in s.inputs:
        named = a.get("aria-label") or a.get("aria-labelledby") or (a.get("id") in s.labels_for) or a.get("title")
        assert named, f"form field without a label in {page}: {a}"
    assert re.search(r'<html[^>]* lang="en"', html), f"{page} needs <html lang>"


def test_scrollable_tables_are_keyboard_reachable():
    html = page_source()
    assert 'class="tbl-wrap"' not in html.replace('class="tbl-wrap" tabindex="0"', "")


def test_heat_cells_pick_their_ink():
    """No fixed white text on heat-map colours (it failed contrast on light cells)."""
    html = page_source()
    assert "t>0.55 ? '#fff'" not in html and "a>50?'#fff'" not in html
    assert html.count("inkOn(") >= 4
