"""
Exercise 23: explain a score change (mirrors explain.explain_change and score_moves.sentence)

A stock's score is a weighted average of the z-scores it HAS:

    score = sum(w_f * z_f) / W        W = sum of the weights of the factors that are not None

When the score changes between two runs, which factor caused it? Write two functions.

1) explain_change(z_prev, z_now, weights) -> dict {factor: contribution}

   z_prev, z_now: {factor: z-score or None (missing)}; weights: {factor: weight}
   * skip factors with weight 0, and factors that are None in BOTH runs
   * contribution c_f = w_f * z_now_f / W_now  -  w_f * z_prev_f / W_prev
     (a None z counts as 0 in its own term; W_prev and W_now are computed separately)
   * the contributions must add up EXACTLY to score_now - score_prev, even when a factor
     appears (new data) or disappears. That's why the simpler w * (z_now - z_prev) / W
     is wrong here: it only works when the same factors exist in both runs.

2) headline(contribs, delta) -> str

   * "mostly <factor>" if the biggest contribution (by absolute size) explains at least half
     of the move AND points the same way (both positive or both negative)
   * otherwise "spread out"

Run `python practice/check.py 23` to check your answer.
"""


def explain_change(z_prev: dict, z_now: dict, weights: dict) -> dict:
    # HINT: w = {f: x for f, x in weights.items() if x > 0}
    # HINT: W_prev = sum(w[f] for f in w if z_prev.get(f) is not None)
    # YOUR CODE HERE
    raise NotImplementedError


def headline(contribs: dict, delta: float) -> str:
    # HINT: top = max(contribs, key=lambda f: abs(contribs[f]))
    # YOUR CODE HERE
    raise NotImplementedError
