"""
"How did #1 get its score?" — the real arithmetic, step by step, for studying.

Every number comes from data.json, so you can redo it by hand (or with the pandas snippet in
the last step). For each stat that counts (weight > 0):

  1. raw value             e.g. Revenue growth YoY = +45%
  2. trim the extremes     values outside the universe's 5th-95th percentile are clipped to it
  3. z-score               (clipped value − universe mean) ÷ universe std
  4. flip if lower=better  inventory days and volatility: z × −1
  5. weighted average      Σ weight × z ÷ Σ weight (over the stats this stock has)

data["z_stats"] holds the universe numbers from step 2-3 (factors.z_stats, the same function
the scorer uses), so the result here matches the stored score to rounding.
"""
from __future__ import annotations

import math

import explain


def _pct_like(f: str) -> bool:
    return f not in ("inv_days_change",)


def _fmt(f: str, v: float) -> str:
    if f == "inv_days_change":
        return f"{v:+.1f} days"
    return f"{v * 100:+.1f}%"


def _paren(f: str, v: float) -> str:
    """A subtracted number: no '+', negatives in parentheses ('− (−1.5%)' reads better than '− -1.5%')."""
    t = _fmt(f, v).lstrip("+")
    return f"({t.replace('-', '−')})" if v < 0 else t


def rebuild(rec: dict, factors: dict, zstats: dict) -> dict:
    """Recompute one stock's composite from its raw stats. Returns {'rows', 'score', 'num', 'den'}."""
    rows, num, den = [], 0.0, 0.0
    for f, c in factors.items():
        w = c.get("weight", 0)
        x = (rec.get("raw") or {}).get(f)
        st = zstats.get(f)
        if w <= 0 or x is None or st is None or not isinstance(x, (int, float)) or not math.isfinite(x):
            continue
        clipped = min(max(x, st["lo"]), st["hi"])
        z = (clipped - st["mean"]) / st["sd"] if st["sd"] else 0.0
        z *= c.get("sign", 1)
        rows.append({"factor": f, "label": c["label"].split(" (")[0], "raw": x, "clipped": clipped,
                     "mean": st["mean"], "sd": st["sd"], "sign": c.get("sign", 1), "z": z, "w": w})
        num += w * z
        den += w
    return {"rows": rows, "num": num, "den": den, "score": num / den if den else None}


def steps(data: dict, ticker: str | None = None) -> list[dict] | None:
    """Ordered steps [{title, body, code?}] for `ticker` (default: today's #1). None if unavailable."""
    factors, zs = data.get("factors") or {}, data.get("z_stats") or {}
    ranked = sorted((r for r in data.get("rankings") or [] if r.get("rank") is not None), key=lambda r: r["rank"])
    if not ranked or not zs:
        return None
    rec = next((r for r in ranked if r["ticker"] == ticker), ranked[0]) if ticker else ranked[0]
    rb = rebuild(rec, factors, zs)
    if not rb["rows"] or rb["score"] is None:
        return None
    t = rec["ticker"]
    out = [{"title": f"1. {t}'s raw stats",
            "body": "; ".join(f"{r['label']} {_fmt(r['factor'], r['raw'])}" for r in rb["rows"]) + "."}]
    lines = []
    for r in rb["rows"]:
        clip = "" if abs(r["clipped"] - r["raw"]) < 1e-12 else f" (raw {_fmt(r['factor'], r['raw'])}, clipped)"
        flip = " × −1 (lower is better)" if r["sign"] < 0 else ""
        lines.append(f"{r['label']}: ({_fmt(r['factor'], r['clipped'])} − {_paren(r['factor'], r['mean'])}) ÷ "
                     f"{_fmt(r['factor'], r['sd']).lstrip('+')}{flip} = {r['z']:+.2f}{clip}")
    out.append({"title": "2. Compare each stat with the other stocks (z-scores)",
                "body": "z = (value − universe average) ÷ universe spread. Extreme values are first clipped to the "
                        "5th-95th percentile so one wild number can't dominate.\n" + "\n".join(lines)})
    terms = "".join((("−" if r["z"] < 0 else "") if i == 0 else (" − " if r["z"] < 0 else " + "))
                    + f"{abs(r['z']):.2f}×{r['w']:g}" for i, r in enumerate(rb["rows"]))
    out.append({"title": "3. Weighted average = the score",
                "body": f"({terms}) ÷ {rb['den']:g} = {rb['score']:+.2f}. "
                        f"The dashboard's stored score is {rec['score']:+.2f}."})
    nxt = next((r for r in ranked if r["ticker"] != t), None)
    if nxt:
        cmp = explain.compare(rec, nxt, factors)
        out.append({"title": f"4. Why it beats #{int(nxt['rank'])} {nxt['ticker']}", "body": cmp["sentence"]})
    out.append({"title": "5. Do it yourself in pandas",
                "body": "Run this next to docs/data.json (after `python run.py --demo`). It should print the same score.",
                "code": snippet(t), "expect": f"{rec['score']:.2f}"})
    return out


def snippet(ticker: str) -> str:
    """≤ 8 lines that reproduce a stock's score from data.json."""
    return (f'import json, pathlib, slim; d = slim.unpack(json.loads(pathlib.Path("docs/data.json").read_text()))\n'
            f'r = next(x for x in d["rankings"] if x["ticker"] == "{ticker}"); num = den = 0\n'
            f'for f, c in d["factors"].items():\n'
            f'    x, s = r["raw"].get(f), d["z_stats"].get(f)\n'
            f'    if c["weight"] > 0 and x is not None and s:\n'
            f'        z = (min(max(x, s["lo"]), s["hi"]) - s["mean"]) / s["sd"] * c["sign"]\n'
            f'        num += c["weight"] * z; den += c["weight"]\n'
            f'print(f"{{num / den:.2f}}")')
