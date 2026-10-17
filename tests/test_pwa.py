"""Installable-app pieces: manifest, icons, service worker file list."""
import json
import re
from pathlib import Path

from PIL import Image

DOCS = Path(__file__).resolve().parents[1] / "docs"


def test_manifest_valid():
    m = json.loads((DOCS / "manifest.webmanifest").read_text())
    for k in ("name", "short_name", "start_url", "display", "icons", "theme_color", "background_color"):
        assert m.get(k), k
    assert m["short_name"] == "SemiScope" and m["display"] == "standalone"
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_icons_have_right_sizes():
    for name, n in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        with Image.open(DOCS / name) as im:
            assert im.size == (n, n), name


def test_service_worker_lists_only_existing_files():
    sw = (DOCS / "sw.js").read_text()
    shell = re.search(r"const SHELL = \[(.*?)\];", sw, re.S).group(1)
    files = re.findall(r"'([^']+)'", shell)
    local = [f for f in files if not f.startswith("http") and f != "./"]
    assert local, "no local files in SHELL"
    missing = [f for f in local if not (DOCS / f).exists()]
    assert not missing, missing
    # the CDN file cached must be exactly the one the page loads
    cdn = [f for f in files if f.startswith("http")]
    assert all(c in (DOCS / "index.html").read_text() for c in cdn)


def test_pages_link_manifest_and_register_worker():
    for page in ("index.html", "setup.html", "weekly.html", "practice.html"):
        html = (DOCS / page).read_text()
        assert 'rel="manifest"' in html and "serviceWorker.register('sw.js')" in html
        assert 'apple-touch-icon' in html


def test_weekly_page_is_cached_and_cache_was_bumped():
    sw = (DOCS / "sw.js").read_text()
    assert "'weekly.html'" in sw and "'practice.html'" in sw and "const VERSION = 'semiscope-v5';" in sw and "'helpers.js'" in sw
