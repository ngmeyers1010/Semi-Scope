"""In-tab jump chips and card deep links (index.html), plus weekly.html's link filter."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HTML = page_source()
WEEKLY = (ROOT / "docs" / "weekly.html").read_text()
node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _js(block_re, expr, page=HTML):
    block = re.search(block_re, page, re.S).group(0)
    out = subprocess.run(["node", "-e", block + f"\nconsole.log(JSON.stringify({expr}));"],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@node
def test_chips_only_for_visible_cards_in_order():
    cards = [{"id": "a", "title": " Backtest "}, {"id": "b", "title": "Hidden", "hidden": True},
             {"id": "c", "title": "Steady"}, {"id": "d", "title": ""}, {"id": "e", "title": "Capture"},
             {"id": "f", "title": "Drawdowns"}, {"id": "", "title": "no id"}]
    got = _js(r"// ---- jump chips ----.*?// ---- end jump chips ----", f"chipItems({json.dumps(cards)})")
    assert got == [{"id": "a", "title": "Backtest"}, {"id": "c", "title": "Steady"},
                   {"id": "e", "title": "Capture"}, {"id": "f", "title": "Drawdowns"}]
    few = _js(r"// ---- jump chips ----.*?// ---- end jump chips ----", f"chipItems({json.dumps(cards[:3])})")
    assert few == []                                       # under 4 visible: no chip row
    assert _js(r"// ---- jump chips ----.*?// ---- end jump chips ----", "chipItems(null)") == []


def test_chip_text_is_never_html():
    fn = re.search(r"function buildJumpChips.*?\n}\n", HTML, re.S).group(0)
    assert "textContent = it.title" in fn and "innerHTML" not in fn


def test_card_deep_link_is_restricted_to_id_characters():
    assert r"card=([\w-]+)" in HTML and "jumpTo(hc[1])" in HTML


@node
def test_weekly_safe_link():
    line = re.search(r"const safeLink = .*", WEEKLY).group(0)
    cases = ["index.html#tab=bt&card=dd-card", "index.html#stock=MU", "index.html", "javascript:alert(1)",
             "https://evil.example/index.html", "index.html#tab=bt\"onclick=x", "//evil.example", None]
    got = _js(r"const safeLink = .*", f"{json.dumps(cases)}.map(safeLink)", page=line)
    assert got[:3] == cases[:3]
    assert all(g == "index.html" for g in got[3:])


def test_weekly_links_point_at_real_cards():
    import weekly
    ids = set(re.findall(r'id="([\w-]+-card)"', HTML))
    src = Path(weekly.__file__).read_text()
    cards = re.findall(r"card=([\w-]+)", src)
    assert len(cards) >= 5
    for card in cards:
        assert card in ids, card


@node
def test_tour_skips_missing_targets_and_picks_first_visible():
    block = r"// ---- tour ----.*?// ---- end tour ----"
    got = _js(block, "visibleSteps(TOUR_STEPS, s => ['nav', '#rank-table', '#out-card'].includes(s)).map(s => [s.tab, s.target])")
    assert got == [[None, "nav"], ["rank", "#rank-table"], ["bt", "#out-card"]]       # paper card and weekly link "missing"
    assert _js(block, "visibleSteps(TOUR_STEPS, () => true).length") == 5
    assert _js(block, "visibleSteps(TOUR_STEPS, () => { throw new Error('x'); }).length") == 0
    assert _js(block, "visibleSteps(null, () => true)") == []


def test_tour_text_is_never_html():
    fn = re.search(r"function startTour.*?\n}\n", HTML, re.S).group(0)
    assert "innerHTML" not in fn and "h.textContent = s.title" in fn and "p.textContent = s.text" in fn
    assert "localStorage.setItem(TOUR_KEY" in fn and "catch(e)" in fn
