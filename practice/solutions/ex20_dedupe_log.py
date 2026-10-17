"""Solution: ex20_dedupe_log"""


def merge_log(old: list, new: list, date: str) -> list:
    rest = [a for a in old if a["date"] != date]          # today's run replaces today's entries
    out, seen = [], set()
    for a in [dict(a, date=date) for a in new] + rest:
        key = (a["date"], a["text"])
        if key not in seen:
            seen.add(key)
            out.append(a)
    return out[:40]
