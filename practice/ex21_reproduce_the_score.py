"""
Exercise 21: reproduce a stock's score from data.json (mirrors walkthrough.rebuild)

The dashboard's "How did #1 get its score?" card shows this arithmetic. Now do it yourself.
Write reproduce_score(data, ticker) -> float, where `data` is the unpacked data.json dict:

  data["factors"]   {"rev_growth": {"weight": 1.0, "sign": 1, ...}, "low_vol": {..., "sign": -1}, ...}
  data["z_stats"]   {"rev_growth": {"lo": -0.10, "hi": 0.43, "mean": 0.098, "sd": 0.168}, ...}
  data["rankings"]  [{"ticker": "ANET", "raw": {"rev_growth": 0.45, ...}, "score": 1.14, ...}, ...]

For each factor with weight > 0 that the stock HAS (raw value not None) and that has z_stats:
  1. clip the raw value into [lo, hi]           (min(max(x, lo), hi))
  2. z = (clipped - mean) / sd
  3. z = z * sign                               (sign is -1 when lower is better)
Score = sum(weight * z) / sum(weight), summing weights ONLY over the factors you used.
Return the unrounded float.

Run `python practice/check.py 21` to check your answer. It also checks that, on the real
docs/data.json, your number rounds to the same score the dashboard shows.
"""


def reproduce_score(data: dict, ticker: str) -> float:
    # HINT: rec = next(r for r in data["rankings"] if r["ticker"] == ticker)
    # HINT: loop over data["factors"].items(); skip weight <= 0, missing raw, missing z_stats
    # HINT: keep two running totals, num and den
    # YOUR CODE HERE
    raise NotImplementedError
