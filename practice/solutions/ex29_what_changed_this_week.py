"""Solution: ex29_what_changed_this_week"""


def week_diff(prev, cur, top_n: int, n: int = 3):
    if not prev or not cur:
        return None

    def in_top(r):
        return r is not None and r <= top_n

    entered = sorted((t for t in cur if in_top(cur[t]) and not in_top(prev.get(t))), key=lambda t: cur[t])
    left = sorted((t for t in prev if in_top(prev[t]) and not in_top(cur.get(t))), key=lambda t: prev[t])
    both = [t for t in cur if t in prev and prev[t] != cur[t]]
    up = sorted((t for t in both if cur[t] < prev[t]), key=lambda t: (-(prev[t] - cur[t]), cur[t], t))
    down = sorted((t for t in both if cur[t] > prev[t]), key=lambda t: (-(cur[t] - prev[t]), cur[t], t))

    def item(t):
        return {"ticker": t, "from": prev.get(t), "to": cur.get(t)}

    return {"entered": [item(t) for t in entered], "left": [item(t) for t in left],
            "up": [item(t) for t in up[:n]], "down": [item(t) for t in down[:n]],
            "new": sorted(t for t in cur if t not in prev)}
