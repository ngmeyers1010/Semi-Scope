"""Solution: ex28_readable_colours"""
DARK, LIGHT = "#0b0b0b", "#ffffff"


def _channels(hex_colour: str) -> list:
    h = str(hex_colour).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    r, g, b = (_linear(c) for c in _channels(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def best_ink(bg: str) -> str:
    return DARK if contrast(bg, DARK) >= contrast(bg, LIGHT) else LIGHT
