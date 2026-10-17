"""
Exercise 28: readable colours (mirrors _lum / inkOn in docs/index.html)

The heat-map cells on the dashboard pick black or white text so you can read every number.
"Readable" has a real definition (WCAG): the contrast ratio between text and background
must be at least 4.5. Write three functions.

1) luminance(hex) -> a number from 0 (black) to 1 (white)

   * accept "#1f66c4", "1f66c4", "#fff" or "fff" (3 digits: each one doubled, "fff" = "ffffff")
   * split into red, green, blue: int("1f", 16) = 31, then divide by 255 so each is 0..1
   * linearize each channel c:  c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
     (screens don't show brightness in a straight line; this undoes that)
   * 0.2126 * R + 0.7152 * G + 0.0722 * B   (eyes see green as much brighter than blue)

2) contrast(a, b) -> (L1 + 0.05) / (L2 + 0.05) where L1 is the LIGHTER of the two
   Always >= 1. White on black is 21.0; the same colour on itself is 1.0.

3) best_ink(bg) -> "#0b0b0b" or "#ffffff", whichever has more contrast with bg
   (the dashboard's "black" text is #0b0b0b, not pure #000000). On a tie, pick "#0b0b0b".

Run `python practice/check.py 28` to check your answer.
"""


def luminance(hex_colour: str) -> float:
    # HINT: h = hex_colour.strip().lstrip("#"); if len(h) == 3: h = "".join(c * 2 for c in h)
    # HINT: [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    # YOUR CODE HERE
    raise NotImplementedError


def contrast(a: str, b: str) -> float:
    # HINT: hi, lo = max(...), min(...)
    # YOUR CODE HERE
    raise NotImplementedError


def best_ink(bg: str) -> str:
    # YOUR CODE HERE
    raise NotImplementedError
