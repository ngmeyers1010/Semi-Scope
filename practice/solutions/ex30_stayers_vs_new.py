"""Solution: ex30_stayers_vs_new"""
import math


def classify(quarters) -> list:
    out = []
    for prev, q in zip(quarters, quarters[1:]):
        if not q.get("picks") or q.get("universe") is None:
            continue
        before = set(prev.get("picks") or []) if prev.get("end") == q.get("date") else set()
        row = {"date": q["date"], "stay": [], "new": []}
        for t in q["picks"]:
            r = (q.get("pick_returns") or {}).get(t)
            if r is None:
                continue
            row["stay" if t in before else "new"].append(r - q["universe"])
        out.append(row)
    return out


def gap_t(rows):
    gaps = [sum(r["stay"]) / len(r["stay"]) - sum(r["new"]) / len(r["new"]) for r in rows if r["stay"] and r["new"]]
    n = len(gaps)
    if n < 2:
        return None
    mean = sum(gaps) / n
    sd = math.sqrt(sum((g - mean) ** 2 for g in gaps) / (n - 1))
    if sd <= 1e-12 * max(1.0, abs(mean)):
        return None
    return mean / (sd / math.sqrt(n))
