"""Solution: ex21_reproduce_the_score"""


def reproduce_score(data: dict, ticker: str) -> float:
    rec = next(r for r in data["rankings"] if r["ticker"] == ticker)
    num = den = 0.0
    for f, c in data["factors"].items():
        x, s = (rec.get("raw") or {}).get(f), data["z_stats"].get(f)
        if c["weight"] <= 0 or x is None or not s:
            continue
        z = (min(max(x, s["lo"]), s["hi"]) - s["mean"]) / s["sd"] * c["sign"]
        num += c["weight"] * z
        den += c["weight"]
    return num / den
