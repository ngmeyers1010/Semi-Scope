"""Draws the app icon (an original chip + rising line mark). Run: python make_icons.py"""
from pathlib import Path

from PIL import Image, ImageDraw

DOCS = Path(__file__).parent / "docs"
BG, CHIP, PIN, LINE = "#121211", "#262624", "#8f8e86", "#3987e5"


def icon(size: int) -> Image.Image:
    s = size / 512                                    # draw at 512 scale
    im = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(im)
    lo, hi = 136 * s, 376 * s                         # chip body
    for i in range(5):                                # pins on all four sides
        p = (168 + i * 44) * s
        w = 12 * s
        d.rectangle([p - w, 96 * s, p + w, lo], fill=PIN)
        d.rectangle([p - w, hi, p + w, 416 * s], fill=PIN)
        d.rectangle([96 * s, p - w, lo, p + w], fill=PIN)
        d.rectangle([hi, p - w, 416 * s, p + w], fill=PIN)
    d.rounded_rectangle([lo, lo, hi, hi], radius=28 * s, fill=CHIP)
    pts = [(170, 330), (220, 290), (262, 306), (306, 244), (346, 196)]
    d.line([(x * s, y * s) for x, y in pts], fill=LINE, width=max(2, int(22 * s)), joint="curve")
    r = 18 * s
    d.ellipse([346 * s - r, 196 * s - r, 346 * s + r, 196 * s + r], fill=LINE)
    return im


if __name__ == "__main__":
    for n, name in [(192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")]:
        icon(n).save(DOCS / name, optimize=True)
        print("wrote", name)
