"""Solution: ex23_explain_a_score_change"""


def explain_change(z_prev: dict, z_now: dict, weights: dict) -> dict:
    w = {f: x for f, x in weights.items() if x > 0}
    W_prev = sum(w[f] for f in w if z_prev.get(f) is not None)
    W_now = sum(w[f] for f in w if z_now.get(f) is not None)
    out = {}
    for f in w:
        zp, zn = z_prev.get(f), z_now.get(f)
        if zp is None and zn is None:
            continue
        before = w[f] * zp / W_prev if zp is not None else 0.0
        after = w[f] * zn / W_now if zn is not None else 0.0
        out[f] = after - before
    return out


def headline(contribs: dict, delta: float) -> str:
    if not contribs:
        return "spread out"
    top = max(contribs, key=lambda f: abs(contribs[f]))
    c = contribs[top]
    if abs(c) >= 0.5 * abs(delta) and (c > 0) == (delta > 0):
        return f"mostly {top}"
    return "spread out"
