"""Practice track: solutions pass, untouched stubs fail gracefully, wrong answers get useful messages."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "practice"))
import check  # noqa: E402
from _jsblocks import page_source  # noqa: E402  (index.html + helpers.js)


@pytest.mark.parametrize("n", list(check.EXERCISES))
def test_solution_passes(n):
    ok, msg = check.check(n, ROOT / "practice" / "solutions")
    assert ok, f"exercise {n}: {msg}"


@pytest.mark.parametrize("n", list(check.EXERCISES))
def test_stub_fails_gracefully(n):
    ok, msg = check.check(n, ROOT / "practice")
    assert not ok and "not done yet" in msg


def test_wrong_answer_message(tmp_path):
    (tmp_path / "ex06_max_drawdown.py").write_text("def max_drawdown(prices):\n    return prices.min() / prices.iloc[0] - 1\n")
    ok, msg = check.check(6, tmp_path)
    assert not ok and "expected" in msg
    (tmp_path / "ex01_last_price.py").write_text("def last_price(px, ticker):\n    px[ticker].dropna().iloc[-1]\n")
    ok, msg = check.check(1, tmp_path)
    assert not ok and "forget `return`" in msg
    (tmp_path / "ex02_daily_returns.py").write_text("def daily_returns(px):\n    return px.pct_change(\n")
    ok, msg = check.check(2, tmp_path)
    assert not ok and "error" in msg                      # syntax error is reported, not crashed on


def test_weak_test_is_caught(tmp_path):
    (tmp_path / "ex12_write_a_test.py").write_text(
        "import pandas as pd\ndef check_max_drawdown(fn):\n    assert fn(pd.Series([1.0, 2.0, 1.0])) <= 0\n")
    ok, msg = check.check(12, tmp_path)
    assert not ok and "buggy version 1" in msg


def test_new_exercises_catch_common_mistakes(tmp_path):
    # 13: including today's move in its own yardstick
    (tmp_path / "ex13_z_move.py").write_text(
        "import numpy as np\ndef z_move(prices, n=1):\n    p = prices.dropna(); r = p.pct_change()\n"
        "    return float((p.iloc[-1]/p.iloc[-1-n]-1) / (r.iloc[-252:].std()*np.sqrt(n)))\n")
    ok, msg = check.check(13, tmp_path)
    assert not ok and "expected" in msg
    # 14: >= 365 instead of > 365 (exactly one year is still short-term)
    (tmp_path / "ex14_fifo_lots.py").write_text(
        "import pandas as pd\ndef fifo_gains(lots, shares, price, sell_date):\n    left, s, l = shares, 0.0, 0.0\n"
        "    for d, n, bp in lots:\n        if left <= 0: break\n        t = min(n, left); g = t*(price-bp)\n"
        "        if (pd.Timestamp(sell_date)-pd.Timestamp(d)).days >= 365: l += g\n        else: s += g\n"
        "        left -= t\n    return pd.Series({'short': s, 'long': l})\n")
    ok, msg = check.check(14, tmp_path)
    assert not ok and "values differ" in msg
    assert set(check.EXERCISES) >= {13, 14, 15, 16}


def test_part3_exercises_catch_common_mistakes(tmp_path):
    good_label = (ROOT / "practice" / "solutions" / "ex17_own_percentile.py").read_text().split("def valuation_label")[1]
    # 17: ties counted fully
    (tmp_path / "ex17_own_percentile.py").write_text(
        "def own_percentile(history, today):\n    h = history.dropna()\n    return float(100 * (h <= today).sum() / len(h))\n"
        "def valuation_label" + good_label)
    ok, msg = check.check(17, tmp_path)
    assert not ok and "count half" in msg
    # 17: NaN weeks not dropped
    (tmp_path / "ex17_own_percentile.py").write_text(
        "def own_percentile(history, today):\n    h = history\n"
        "    return float(100 * ((h < today).sum() + 0.5 * (h == today).sum()) / len(h))\n"
        "def valuation_label" + good_label)
    ok, msg = check.check(17, tmp_path)
    assert not ok and ".dropna()" in msg
    # 17: right percentile, label uses >= instead of > at the 75 edge
    good_pct = (ROOT / "practice" / "solutions" / "ex17_own_percentile.py").read_text().split("def valuation_label")[0]
    bad_label = good_label.replace("if pct <= 75:", "if pct < 75:")
    (tmp_path / "ex17_own_percentile.py").write_text(good_pct + "def valuation_label" + bad_label)
    ok, msg = check.check(17, tmp_path)
    assert not ok and "valuation_label(75)" in msg and "< versus <=" in msg
    # 18: NaN not dropped -> returns NaN for MU / the typo instead of a price / None
    (tmp_path / "ex18_fake_the_network.py").write_text(
        "def latest_close(ticker, download):\n    px = download([ticker])\n"
        "    if ticker not in px: return None\n    return float(px[ticker].iloc[-1])\n")
    ok, msg = check.check(18, tmp_path)
    assert not ok and ".dropna()" in msg
    assert set(check.EXERCISES) >= {17, 18}


def test_ex18_file_runs_its_own_fake_download_test():
    import runpy
    ns = runpy.run_path(str(ROOT / "practice" / "solutions" / "ex18_fake_the_network.py"))
    ns["test_latest_close"]()


def test_part4_exercises_catch_common_mistakes(tmp_path):
    good19 = (ROOT / "practice" / "solutions" / "ex19_rolling_excess.py").read_text()
    worst = "def worst_window" + good19.split("def worst_window")[1]
    # 19: adding daily returns instead of compounding
    (tmp_path / "ex19_rolling_excess.py").write_text(
        "import pandas as pd\ndef rolling_excess(strat, spy):\n    s = lambda p: p.pct_change().rolling(252).sum()\n"
        "    return (s(strat) - s(spy)).dropna()\n" + worst)
    ok, msg = check.check(19, tmp_path)
    assert not ok and "compound" in msg
    # 19: off-by-one window
    (tmp_path / "ex19_rolling_excess.py").write_text(
        "import pandas as pd\ndef rolling_excess(strat, spy):\n    y = lambda p: p / p.shift(251) - 1\n    return (y(strat) - y(spy)).dropna()\n" + worst)
    ok, msg = check.check(19, tmp_path)
    assert not ok and "shift(252)" in msg
    # 19: worst_window not written
    (tmp_path / "ex19_rolling_excess.py").write_text(good19.split("def worst_window")[0])
    ok, msg = check.check(19, tmp_path)
    assert not ok and "worst_window" in msg
    # 20: keeps the first run's entries for the same day
    (tmp_path / "ex20_dedupe_log.py").write_text(
        "def merge_log(old, new, date):\n    out, seen = [], set()\n"
        "    for a in [dict(a, date=date) for a in new] + old:\n"
        "        k = (a['date'], a['text'])\n        if k not in seen:\n            seen.add(k); out.append(a)\n"
        "    return out[:40]\n")
    ok, msg = check.check(20, tmp_path)
    assert not ok and "REPLACES the day" in msg
    # 20: oldest first
    (tmp_path / "ex20_dedupe_log.py").write_text(
        "def merge_log(old, new, date):\n    rest = [a for a in old if a['date'] != date]\n    out, seen = [], set()\n"
        "    for a in [dict(a, date=date) for a in new] + rest:\n        k = (a['date'], a['text'])\n"
        "        if k not in seen:\n            seen.add(k); out.append(a)\n    return list(reversed(out))[:40]\n")
    ok, msg = check.check(20, tmp_path)
    assert not ok and "FIRST" in msg
    # 20: no dedupe at all
    (tmp_path / "ex20_dedupe_log.py").write_text(
        "def merge_log(old, new, date):\n    rest = [a for a in old if a['date'] != date]\n"
        "    return ([dict(a, date=date) for a in new] + rest)[:40]\n")
    ok, msg = check.check(20, tmp_path)
    assert not ok and "duplicate" in msg
    assert set(check.EXERCISES) >= {19, 20}


def test_ex21_catches_common_mistakes(tmp_path):
    sol = (ROOT / "practice" / "solutions" / "ex21_reproduce_the_score.py").read_text()
    skip = 'if c["weight"] <= 0 or x is None or not s:\n            continue'
    cases = [
        ('min(max(x, s["lo"]), s["hi"])', "x", "clip each raw value"),            # no clipping
        (' * c["sign"]', "", "factor's sign"),                                   # no flip
        (skip, 'if c["weight"] <= 0:\n            continue\n'                   # weights of missing stats
               '        if x is None or not s:\n            den += c["weight"]\n            continue',
         "stats the stock HAS"),
    ]
    for old, new, want in cases:
        code = sol.replace(old, new, 1)
        assert code != sol
        (tmp_path / "ex21_reproduce_the_score.py").write_text(code)
        ok, msg = check.check(21, tmp_path)
        assert not ok and want in msg, msg


def test_ex21_checks_against_the_real_data_json():
    """On the shipped demo data.json the solution must round to the stored #1 score."""
    if check._real_data() is None:
        pytest.skip("no docs/data.json with z_stats")
    ok, msg = check.check(21, ROOT / "practice" / "solutions")
    assert ok and "same as the dashboard" in msg


def test_ex22_catches_common_mistakes(tmp_path):
    sol = (ROOT / "practice" / "solutions" / "ex22_signal_decay.py").read_text()
    cases = [
        ("i = px.index.searchsorted(start + pd.DateOffset(months=months))",
         "i = px.index.searchsorted(start + pd.DateOffset(months=months), side='right') - 1", "ON OR AFTER"),
        ("return float(avg(list(picks)) - avg(list(universe)))",
         "return float(avg(list(picks)) - (px.loc[end, universe] / px.loc[start, universe] - 1).dropna().sum())", "AVERAGE"),
        ("(px.loc[end, names] / px.loc[start, names] - 1).dropna().mean()",
         "(px.loc[end, names] / px.loc[start, names] - 1).fillna(0).mean()", "missing price"),
        ("        return None                                                    # hasn't happened yet\n",
         "        i = len(px.index) - 1\n", "return None"),
        ("return float(t / math.sqrt(max(1.0, months / 3)))", "return float(t)", "sqrt(months / 3)"),
        ("s.std()", "s.std(ddof=0)", "SAMPLE std"),
    ]
    for old, new, want in cases:
        code = sol.replace(old, new, 1)
        assert code != sol, old
        (tmp_path / "ex22_signal_decay.py").write_text(code)
        ok, msg = check.check(22, tmp_path)
        assert not ok and want in msg, (want, msg)
    (tmp_path / "ex22_signal_decay.py").write_text(sol.split("def overlap_t")[0])
    ok, msg = check.check(22, tmp_path)
    assert not ok and "overlap_t" in msg


def test_ex23_matches_explain_py_and_catches_mistakes(tmp_path):
    sys.path.insert(0, str(ROOT))
    import explain
    sol = check._load(ROOT / "practice" / "solutions", "ex23_explain_a_score_change", "explain_change")
    for zp, zn, w in check._args(23):                          # same numbers as the real module
        real = {d["factor"]: d["contrib"] for d in explain.explain_change(zp, zn, w)["drivers"]}
        assert sol(zp, zn, w) == pytest.approx(real)
    src = (ROOT / "practice" / "solutions" / "ex23_explain_a_score_change.py").read_text()
    old_w = "    W_prev = sum(w[f] for f in w if z_prev.get(f) is not None)\n    W_now = sum(w[f] for f in w if z_now.get(f) is not None)\n"
    simple = ("        z0 = zp if zp is not None else 0.0\n        z1 = zn if zn is not None else 0.0\n"
              "        out[f] = w[f] * (z1 - z0) / W_now\n    return out\n\n\ndef headline")
    body = src[src.index("        before = w[f]"):src.index("def headline")]
    cases = [
        (old_w, "    W_prev = W_now = sum(w.values())\n", "HAS"),                      # all weights
        (body, simple[: -len("def headline")], "breaks when a factor appears"),        # w·Δz/W
        ("if abs(c) >= 0.5 * abs(delta) and (c > 0) == (delta > 0):", "if abs(c) >= 0.5 * abs(delta):", "OTHER way"),
        ("if abs(c) >= 0.5 * abs(delta) and (c > 0) == (delta > 0):", "if (c > 0) == (delta > 0):", "HALF"),
        ("    w = {f: x for f, x in weights.items() if x > 0}", "    w = dict(weights)", "weight is 0"),
    ]
    for old, new, want in cases:
        code = src.replace(old, new, 1)
        assert code != src, old
        (tmp_path / "ex23_explain_a_score_change.py").write_text(code)
        ok, msg = check.check(23, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_ex24_matches_capture_py_and_catches_mistakes(tmp_path):
    sys.path.insert(0, str(ROOT))
    import capture
    sol = check._load(ROOT / "practice" / "solutions", "ex24_up_down_capture", "up_down_capture")
    for strat, bench in check._capture_args():
        real = capture.capture(strat, bench)
        assert sol(strat, bench) == pytest.approx((real["up"], real["down"]))
    src = (ROOT / "practice" / "solutions" / "ex24_up_down_capture.py").read_text()
    ret = 'return float(up["s"].mean() / up["b"].mean()), float(down["s"].mean() / down["b"].mean())'
    cases = [
        ('return p.resample("ME").last().pct_change().dropna()', "return p.pct_change().dropna()", "MONTHLY"),
        ('both[both["b"] > 0]', 'both[both["b"] >= 0]', "flat months"),
        (ret, 'return float(up["b"].mean() / up["s"].mean()), float(down["b"].mean() / down["s"].mean())', "strategy on top"),
        (ret, 'return float((up["s"] / up["b"]).mean()), float((down["s"] / down["b"]).mean())', "ratio of averages"),
    ]
    for old, new, want in cases:
        code = src.replace(old, new, 1)
        assert code != src, old
        (tmp_path / "ex24_up_down_capture.py").write_text(code)
        ok, msg = check.check(24, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_ex25_matches_drawdowns_py_and_catches_mistakes(tmp_path):
    sys.path.insert(0, str(ROOT))
    import drawdowns
    sol = check._load(ROOT / "practice" / "solutions", "ex25_drawdown_episodes", "episodes")
    for (c,) in check._dd_args():
        real = [(e["peak"], e["trough"], e["recovery"], round(e["depth"], 9)) for e in drawdowns.episodes(c)]
        mine = [(str(e["peak"].date()), str(e["trough"].date()),
                 None if e["recovery"] is None else str(e["recovery"].date()), round(e["depth"], 9)) for e in sol(c)]
        assert mine == real
    src = (ROOT / "practice" / "solutions" / "ex25_drawdown_episodes.py").read_text()
    cases = [
        ("start = i - 1", "start = i", "day BEFORE"),
        ("    if start is not None:                      # still underwater when the data ends\n        close(start, len(uw))\n",
         "", "recovery = None"),
        ("return curve / curve.cummax() - 1", "return curve / curve.cummin() - 1", "cummax"),
        ("return [e for e in out if -e[\"depth\"] >= min_depth]", "return out", "wiggles"),
    ]
    for old, new, want in cases:
        code = src.replace(old, new, 1)
        assert code != src, old
        (tmp_path / "ex25_drawdown_episodes.py").write_text(code)
        ok, msg = check.check(25, tmp_path)
        assert not ok and want in msg, (want, msg)
    # episodes right but underwater left as a stub
    (tmp_path / "ex25_drawdown_episodes.py").write_text(
        src.replace("def underwater(curve: pd.Series) -> pd.Series:\n    return curve / curve.cummax() - 1",
                    "def underwater(curve: pd.Series) -> pd.Series:\n    return curve / curve.cummax() - 1\n\n\n"
                    "def _unused():\n    pass").replace("uw = underwater(", "uw = (lambda c: c / c.cummax() - 1)(")
        + "\n\ndef underwater(curve):\n    raise NotImplementedError\n")
    ok, msg = check.check(25, tmp_path)
    assert not ok and "underwater is not done yet" in msg, msg


def test_plan_order_covers_every_exercise_once_and_matches_plan_md():
    assert sorted(check.PLAN_ORDER) == sorted(check.EXERCISES) and len(set(check.PLAN_ORDER)) == len(check.EXERCISES)
    assert set(check.SKILLS) == set(check.EXERCISES)
    import re
    md = (ROOT / "practice" / "PLAN.md").read_text()
    sessions = re.findall(r"^### Session (\d+): ex(\d+) (\w+)", md, re.M)
    assert [int(s) for s, _, _ in sessions] == list(range(1, len(check.PLAN_ORDER) + 1))
    assert [int(n) for _, n, _ in sessions] == check.PLAN_ORDER
    for _, n, name in sessions:                               # names match the files
        assert check.EXERCISES[int(n)][0] == f"ex{n}_{name}"
    weeks = re.findall(r"^## (Week \d: .+)$", md, re.M)
    assert weeks == [w for w, _ in check.PLAN]


def test_next_on_solutions_stubs_and_partial(tmp_path, capsys):
    done = check.progress(ROOT / "practice" / "solutions")
    assert all(done.values())
    n = len(check.PLAN_ORDER)
    assert f"All {n} done" in check.next_text(done=done) and f"{n}/{n} done" in check.next_text(done=done)
    stubs = check.progress(ROOT / "practice")
    assert not any(stubs.values())
    first = check.PLAN_ORDER[0]
    assert f"Next: session 1 (Week 1): ex{first:02d}" in check.next_text(done=stubs)
    # a folder where the first 3 plan sessions are solved, the rest are stubs
    import shutil
    for n in check.EXERCISES:
        mod = check.EXERCISES[n][0]
        src = ROOT / "practice" / ("solutions" if n in check.PLAN_ORDER[:3] else "") / f"{mod}.py"
        shutil.copy(src, tmp_path / f"{mod}.py")
    text = check.next_text(tmp_path)
    fourth = check.PLAN_ORDER[3]
    assert f"3/{len(check.PLAN_ORDER)} done" in text and f"session 4 (Week 1): ex{fourth:02d}" in text
    plan = check.plan_text(tmp_path)
    assert plan.count("✓") == 3 and plan.splitlines()[0] == check.PLAN[0][0]
    assert check.main(["--next"]) == 0 and "done" in capsys.readouterr().out


def test_ex26_matches_outcomes_py_and_catches_mistakes(tmp_path):
    import numpy as np
    sys.path.insert(0, str(ROOT))
    import outcomes
    sol = check._load(ROOT / "practice" / "solutions", "ex26_bootstrap_a_range", "block_paths")
    for r, years, n in check._args(26):
        assert np.allclose(sol(r, years, n), outcomes.simulate(np.array(r), None, years, n, 42)["strategy"])
    src = (ROOT / "practice" / "solutions" / "ex26_bootstrap_a_range.py").read_text()
    cases = [
        ("rng.integers(0, n - block + 1,", "rng.integers(0, n - block,", "upper bound is exclusive"),
        ("    starts = rng.integers(0, n - block + 1, size=(n_paths, n_blocks))\n"
         "    idx = (starts[:, :, None] + np.arange(block)).reshape(n_paths, -1)[:, :q]\n",
         "    idx = rng.integers(0, n, size=(n_paths, q))\n", "BLOCKS"),
        ("return 1000 * np.cumprod(1 + r[idx], axis=1)", "return 1000 * (1 + np.cumsum(r[idx], axis=1))", "compound"),
        ("return 1000 * np.cumprod(1 + r[idx], axis=1)", "return np.cumprod(1 + r[idx], axis=1)", "multiply by 1000"),
        ("    end = np.asarray(paths)[:, -1]", "    end = np.asarray(paths)", "LAST column"),
    ]
    for old, new, want in cases:
        code = src.replace(old, new, 1)
        assert code != src, old
        (tmp_path / "ex26_bootstrap_a_range.py").write_text(code)
        ok, msg = check.check(26, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_ex27_matches_sanity_py_and_catches_mistakes(tmp_path):
    import numpy as np
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    import sanity
    sol_dir = ROOT / "practice" / "solutions"
    flag = check._load(sol_dir, "ex27_catch_a_bad_number", "flag_jumps")
    nonpos = check._load(sol_dir, "ex27_catch_a_bad_number", "nonpositive")
    for v in check.EX27_CASES:
        ends = pd.date_range("2020-03-31", periods=len(v), freq="QE")
        df = pd.DataFrame({"end": ends, "val": [np.nan if x is None else float(x) for x in v], "filed": ends})
        assert sorted(set(flag(v)) | set(nonpos(v))) == sanity.check_series("revenue", df)[0], v
    src = (sol_dir / "ex27_catch_a_bad_number.py").read_text()
    rng = "range(max(0, i - lookback), i)"
    two_sided = "list(range(max(0, i - lookback), i)) + list(range(i + 1, min(len(values), i + 1 + lookback)))"
    cases = [
        ([(rng, two_sided)], "BEFORE"),
        ([("statistics.median(before)", "(sum(before) / len(before))")], "MEDIAN"),
        ([("if j not in dropped and _ok", "if _ok")], "already dropped"),
        ([("r >= jump or r <= 1 / jump", "r > jump or r < 1 / jump")], ">= jump"),
        ([(rng, "range(max(0, i - 1), i)"), ("if len(before) < 2:", "if len(before) < 1:")], "not just the previous one"),
        ([("_ok(x) and x <= 0]", "_ok(x) and x < 0]")], "nonpositive("),
    ]
    for edits, want in cases:
        code = src
        for old, new in edits:
            assert old in code, old
            code = code.replace(old, new, 1)
        (tmp_path / "ex27_catch_a_bad_number.py").write_text(code)
        ok, msg = check.check(27, tmp_path)
        assert not ok and want in msg, (want, msg)


def _ex28():
    sol_dir = ROOT / "practice" / "solutions"
    return {n: check._load(sol_dir, "ex28_readable_colours", n) for n in ("luminance", "contrast", "best_ink")}


def test_ex28_known_answers():
    f = _ex28()
    assert f["contrast"]("#ffffff", "#000000") == pytest.approx(21.0)
    assert f["contrast"]("#000000", "#ffffff") == pytest.approx(21.0)          # order doesn't matter
    assert f["contrast"]("#6b6a65", "#f6f6f4") >= 4.5                          # the muted text we ship
    assert f["contrast"]("#7a7974", "#f6f6f4") < 4.5                           # the old one that failed axe
    assert f["contrast"]("#ec7a7a", "#ec7a7a") == pytest.approx(1.0)
    assert f["luminance"]("fff") == pytest.approx(1.0) and f["luminance"]("#000") == 0.0
    assert f["luminance"](" 1F66C4 ") == pytest.approx(f["luminance"]("#1f66c4"))
    assert f["best_ink"]("#ffffff") == "#0b0b0b" and f["best_ink"]("#000000") == "#ffffff"
    assert f["best_ink"]("#777777") == "#ffffff"        # pure #000000 would (wrongly) pick dark here


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_ex28_agrees_with_index_html_inkOn():
    import json
    import re
    import subprocess
    html = page_source()
    block = re.search(r"// ---- ink ----.*?// ---- end ink ----", html, re.S).group(0)
    cols = check.EX28_COLOURS + ["#3a7d44", "#c0392b", "#f1c40f", "#2e2e2b", "#b3b3b3", "#20201e"]
    js = block + f"\nconst C = {json.dumps(cols)};\n" + \
        "console.log(JSON.stringify(C.map(c => [_lum(_rgb(c)), inkOn(c, c, 100)])));"
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    f = _ex28()
    for c, (lum, ink) in zip(cols, out):
        assert f["luminance"](c) == pytest.approx(lum, abs=1e-12), c
        assert f["best_ink"](c) == ink, c


def test_ex28_hints_catch_the_usual_slips(tmp_path):
    src = (ROOT / "practice" / "solutions" / "ex28_readable_colours.py").read_text()
    cases = [
        ([("int(h[i:i + 2], 16) / 255", "int(h[i:i + 2], 16)")], "divide each channel by 255"),
        ([("    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4", "    return c")], "linearize"),
        ([("return 0.2126 * r + 0.7152 * g + 0.0722 * b", "return (r + g + b) / 3")], "weight the channels"),
        ([("r, g, b = (_linear(c) for c in _channels(hex_colour))", "r, g, b = _channels(hex_colour)"),
          ("return 0.2126 * r + 0.7152 * g + 0.0722 * b", "return (r + g + b) / 3")], "plain average"),
        ([("return (hi + 0.05) / (lo + 0.05)", "return (lo + 0.05) / (hi + 0.05)")], "LIGHTER"),
        ([('DARK, LIGHT = "#0b0b0b", "#ffffff"', 'DARK, LIGHT = "#000000", "#ffffff"')], "not pure #000000"),
        ([("return DARK if contrast(bg, DARK) >= contrast(bg, LIGHT) else LIGHT", "return 'black'")], '"#0b0b0b" or'),
    ]
    for edits, want in cases:
        code = src
        for old, new in edits:
            assert old in code, old
            code = code.replace(old, new, 1)
        (tmp_path / "ex28_readable_colours.py").write_text(code)
        ok, msg = check.check(28, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_ex29_matches_week_diff_py_on_every_case_and_the_real_week():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    import test_week_diff
    import week_diff
    assert check.EX29_CASES == test_week_diff.CASES
    real = check._real_week_args()
    assert real, "docs/data.json should have week_ranks"
    sol = check._load(ROOT / "practice" / "solutions", "ex29_what_changed_this_week", "week_diff")
    for args in check.EX29_CASES + real:
        assert sol(*args) == week_diff.diff(*args), args


def test_ex29_hints_catch_the_usual_slips(tmp_path):
    src = (ROOT / "practice" / "solutions" / "ex29_what_changed_this_week.py").read_text()
    cases = [
        ([("    if not prev or not cur:\n        return None\n", "    prev, cur = prev or {}, cur or {}\n")], "return None"),
        ([("up[:n]", "up"), ("down[:n]", "down")], "at most n movers"),
        ([('"up": [item(t) for t in up[:n]], "down": [item(t) for t in down[:n]]',
           '"up": [item(t) for t in down[:n]], "down": [item(t) for t in up[:n]]')], "SMALLER rank"),
        ([("both = [t for t in cur if t in prev and prev[t] != cur[t]]",
           "prev = {**{t: 10 ** 9 for t in cur}, **prev}\n    both = [t for t in cur if prev[t] != cur[t]]"),
          ("\"from\": prev.get(t)", "\"from\": (prev.get(t) if prev.get(t) != 10 ** 9 else None)"),
          ("(t for t in prev if in_top", "(t for t in prev if prev[t] != 10 ** 9 and in_top"),
          ("sorted(t for t in cur if t not in prev)", "sorted(t for t in cur if prev[t] == 10 ** 9)")], "not a climber"),
        ([("return r is not None and r <= top_n", "return r is not None and r < top_n")], "rank <= top_n"),
        ([("(-(prev[t] - cur[t]), cur[t], t)", "(-(prev[t] - cur[t]),)"), ("(-(cur[t] - prev[t]), cur[t], t)", "(-(cur[t] - prev[t]),)")], "on a tie"),
    ]
    for edits, want in cases:
        code = src
        for old, new in edits:
            assert old in code, old
            code = code.replace(old, new, 1)
        (tmp_path / "ex29_what_changed_this_week.py").write_text(code)
        ok, msg = check.check(29, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_ex30_matches_streak_edge_on_hand_made_and_demo_quarters():
    sys.path.insert(0, str(ROOT))
    import streak_edge
    sol = ROOT / "practice" / "solutions"
    classify = check._load(sol, "ex30_stayers_vs_new", "classify")
    gap_t = check._load(sol, "ex30_stayers_vs_new", "gap_t")
    # the first hand-made set is the known answer in tests/test_streak_edge.py
    assert [q["picks"] for q in check.EX30_QUARTERS[0]] == [["A", "B"], ["A", "C"], ["C", "D"]]
    real = check._real_quarters_args()
    assert real and len(real[0][0]) > 40
    for (qs,) in [(q,) for q in check.EX30_QUARTERS] + real:
        assert classify(qs) == streak_edge.classify(qs)
        b = streak_edge.build(qs)
        t = gap_t(classify(qs))
        if b is None or b["t"] is None:
            assert t is None or b is None
        else:
            assert t == pytest.approx(b["t"], abs=1e-3)


def test_ex30_hints_catch_the_usual_slips(tmp_path):
    src = (ROOT / "practice" / "solutions" / "ex30_stayers_vs_new.py").read_text()
    cases = [
        ([("for prev, q in zip(quarters, quarters[1:]):", "for prev, q in zip([{}] + quarters[:-1], quarters):")], "skip the first quarter"),
        ([(' if prev.get("end") == q.get("date") else set()', " if prev else set()")], "prev['end'] == q['date']"),
        ([('append(r - q["universe"])', "append(r)")], "MINUS q['universe']"),
        ([("    gaps = [sum(r[\"stay\"]) / len(r[\"stay\"]) - sum(r[\"new\"]) / len(r[\"new\"]) for r in rows if r[\"stay\"] and r[\"new\"]]\n    n = len(gaps)\n    if n < 2:\n        return None\n    mean = sum(gaps) / n\n    sd = math.sqrt(sum((g - mean) ** 2 for g in gaps) / (n - 1))\n    if sd <= 1e-12 * max(1.0, abs(mean)):\n        return None\n    return mean / (sd / math.sqrt(n))",
           "    s = [x for r in rows for x in r['stay']]\n    w = [x for r in rows for x in r['new']]\n    if len(s) < 2 or len(w) < 2 or not any(r['stay'] and r['new'] for r in rows):\n        return None\n"
           "    ms, mn = sum(s) / len(s), sum(w) / len(w)\n    vs = sum((x - ms) ** 2 for x in s) / (len(s) - 1)\n    vn = sum((x - mn) ** 2 for x in w) / (len(w) - 1)\n"
           "    if len([1 for r in rows if r['stay'] and r['new']]) < 2:\n        return None\n    return (ms - mn) / math.sqrt(vs / len(s) + vn / len(w))")], "one gap per QUARTER"),
        ([("/ (n - 1))", "/ n)")], "divide by (n - 1)"),
        ([("    if sd <= 1e-12 * max(1.0, abs(mean)):\n        return None\n", ""), ("return mean / (sd / math.sqrt(n))", "return mean / (sd / math.sqrt(n)) if sd else 0.0")], "every gap is the same"),
    ]
    for edits, want in cases:
        code = src
        for old, new in edits:
            assert old in code, old
            code = code.replace(old, new, 1)
        (tmp_path / "ex30_stayers_vs_new.py").write_text(code)
        ok, msg = check.check(30, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_practice_html_page(monkeypatch):
    import re
    done = {n: (n % 3 == 0) for n in check.EXERCISES}
    page = check.html_page(done)
    order = [int(x) for x in re.findall(r'<li class="[^"]*" id="ex-\d+" data-ex="(\d+)"', page)]
    assert order == check.PLAN_ORDER and len(set(order)) == len(check.EXERCISES)        # each once, in plan order
    assert page.count('<li class="done') == sum(done.values())
    assert f'value="{sum(done.values())}"' in page and f'max="{len(check.PLAN_ORDER)}"' in page
    nxt = next(n for n in check.PLAN_ORDER if not done[n])
    assert f'data-ex="{nxt}"' in re.search(r'<li class="todo next" id="ex-\d+" data-ex="\d+"', page).group(0)
    assert f"python practice/check.py {nxt}</code>" in page
    # no outside scripts or styles: works offline
    assert not re.search(r"<script[^>]+src=", page) and "<link rel=\"stylesheet\"" not in page
    assert "--text-muted:#6b6a65" in page and "prefers-color-scheme:dark" in page     # weekly.html's tokens
    # everything that comes from the plan is escaped
    monkeypatch.setitem(check.SKILLS, 1, '<img src=x onerror=alert(1)> & "quotes"')
    bad = check.html_page(done)
    assert "<img src=x" not in bad and "&lt;img src=x onerror=alert(1)&gt; &amp; &quot;quotes&quot;" in bad
    all_done = check.html_page({n: True for n in check.EXERCISES})
    assert "All done" in all_done and "next" not in re.findall(r'<li class="([^"]*)"', all_done)


def test_practice_html_cli_and_committed_copy(tmp_path):
    out = tmp_path / "p.html"
    assert check.main(["--html", str(out)]) == 0
    page = out.read_text()
    assert page.count("data-ex=") == len(check.PLAN_ORDER) and page.count('<li class="done') == 0   # starter files
    committed = (ROOT / "docs" / "practice.html").read_text()
    assert committed.count("data-ex=") == len(check.PLAN_ORDER)
    assert 'href="practice.html"' in page_source()
    assert 'href="practice.html"' in (ROOT / "docs" / "weekly.html").read_text()


def test_practice_html_not_rewritten_when_only_the_date_changes(tmp_path):
    import os
    p = tmp_path / "practice.html"
    done = {n: False for n in check.EXERCISES}
    _, changed = check.write_html(p, done=done, today="2026-10-01")
    assert changed and "checked 2026-10-01" in p.read_text()
    os.utime(p, (1_000_000_000, 1_000_000_000))                       # an old, known mtime
    _, changed = check.write_html(p, done=done, today="2026-10-16")    # a new day, same ✓s
    assert not changed and p.stat().st_mtime == 1_000_000_000 and "checked 2026-10-01" in p.read_text()
    done[1] = True
    _, changed = check.write_html(p, done=done, today="2026-10-16")    # a ✓ changed: rewritten
    assert changed and "checked 2026-10-16" in p.read_text() and p.read_text().count('<li class="done') == 1


def test_pre_commit_hook_is_opt_in_and_never_blocks():
    hook = (ROOT / "scripts" / "pre-commit-practice.sh").read_text()
    assert hook.startswith("#!/bin/sh") and "practice/check.py --html" in hook and "git add docs/practice.html" in hook
    assert hook.rstrip().endswith("exit 0") and "exit 1" not in hook
    assert "ln -s ../../scripts/pre-commit-practice.sh .git/hooks/pre-commit" in (ROOT / "practice" / "README.md").read_text()
    import os
    assert os.access(ROOT / "scripts" / "pre-commit-practice.sh", os.X_OK)


EARLY_WRONG = {   # (exercise, wrong body) -> words the hint must contain (exercises 1-16, not 12)
    (1, "return float(px[ticker].iloc[0])"): "FIRST row",
    (1, "return float(px[ticker].dropna().iloc[0])"): "first price on record",
    (1, "return float(px[ticker].max())"): "highest price ever",
    (2, "return px.pct_change()"): "Drop it: .iloc[1:]",
    (2, "return px.diff().iloc[1:]"): "DOLLARS",
    (2, "return (px / px.shift(-1) - 1).iloc[1:]"): "TOMORROW",
    (3, "s = px.loc[start:end, ticker].dropna()\n    return float(s.iloc[0] / s.iloc[-1] - 1)"): "upside down",
    (3, "s = px.loc[start:end, ticker].dropna()\n    return float(s.iloc[-1] / s.iloc[0])"): "Subtract 1",
    (3, "s = px[ticker].dropna()\n    return float(s.iloc[-1] / s.iloc[0] - 1)"): "Slice the dates",
    (4, "return str((px.iloc[-1] / px.iloc[-days] - 1).dropna().idxmin())"): ".idxmin() finds the WORST",
    (4, "return str((px.iloc[-1] / px.iloc[days] - 1).dropna().idxmax())"): "counts from the START",
    (4, "return str(px.iloc[-1].idxmax())"): "highest PRICE today",
    (5, "return float(px[ticker].pct_change().dropna().tail(days).std())"): "DAILY volatility",
    (5, "return float(px[ticker].pct_change().dropna().tail(days).std() * 252)"): "SQUARE ROOT",
    (5, "return float(px[ticker].dropna().tail(days).std() * 252 ** 0.5)"): "spread of PRICES",
    (6, "return float(-(prices / prices.cummax() - 1).min())"): "NEGATIVE",
    (6, "return float(prices.min() / prices.iloc[0] - 1)"): "FIRST price",
    (6, "return float((prices / prices.cummax() - 1).max())"): ".max() is always 0",
    (7, "return px[ticker].dropna().resample('ME').last().pct_change().dropna()"): "to_period('M')",
    (7, "s = px[ticker].dropna()\n    return s.groupby(s.index.to_period('M')).first().pct_change().dropna()"): "LAST price",
    (7, "s = px[ticker].dropna()\n    return s.groupby(s.index.to_period('M')).last().pct_change()"): "Drop it with .dropna()",
    (8, "return table.groupby('group')['rev_growth'].mean().sort_values(ascending=False)"): "MEDIAN",
    (8, "return table.groupby('group')['rev_growth'].median()"): "sort it",
    (8, "return table.groupby('group')['rev_growth'].median().sort_values()"): "biggest first",
    (9, "m = revenue.merge(cogs, on='end', suffixes=('_rev', '_cogs'))\n    m['gross_margin'] = m['val_cogs'] / m['val_rev']\n"
        "    return m[['end', 'gross_margin']].sort_values('end').reset_index(drop=True)"): "what's LEFT",
    (9, "m = revenue.merge(cogs, on='end', suffixes=('_rev', '_cogs'))\n    m['gross_margin'] = 1 - m['val_rev'] / m['val_cogs']\n"
        "    return m[['end', 'gross_margin']].sort_values('end').reset_index(drop=True)"): "flipped",
    (9, "m = revenue.merge(cogs, on='end', suffixes=('_rev', '_cogs'))\n    m['gross_margin'] = m['val_rev'] - m['val_cogs']\n"
        "    return m[['end', 'gross_margin']].sort_values('end').reset_index(drop=True)"): "gross PROFIT",
    (10, "m = (px.iloc[-1] / px.iloc[-126] - 1).dropna()\n    return ((m - m.mean()) / m.std()).sort_values(ascending=False)"): "skip the most recent month",
    (10, "m = (px.iloc[-21] / px.iloc[-126] - 1).dropna()\n    return ((m - m.mean()) / m.std(ddof=0)).sort_values(ascending=False)"): "ddof=0",
    (10, "m = (px.iloc[-21] / px.iloc[-126] - 1).dropna()\n    return (m - m.mean()) / m.std()"): "highest first",
    (11, "past = px.loc[:end]\n    mom = (past.iloc[-21] / past.iloc[-126] - 1).dropna()\n    picks = mom.nlargest(k).index\n"
         "    window = px.loc[start:end, picks]\n    return float((window.iloc[-1] / window.iloc[0] - 1).mean())"): "LOOK-AHEAD",
    (11, "past = px.loc[:start]\n    mom = (past.iloc[-21] / past.iloc[-126] - 1).dropna()\n    picks = mom.nsmallest(k).index\n"
         "    window = px.loc[start:end, picks]\n    return float((window.iloc[-1] / window.iloc[0] - 1).mean())"): "WORST k",
    (11, "past = px.loc[:start]\n    mom = (past.iloc[-21] / past.iloc[-126] - 1).dropna()\n    picks = mom.nlargest(k).index\n"
         "    window = px.loc[start:end, picks]\n    return float((window.iloc[-1] / window.iloc[0] - 1).sum())"): "AVERAGE",
    (13, "import numpy as np\n    p = prices.dropna()\n    r = p.pct_change()\n    sigma = r.iloc[-252:].std()\n"
         "    ret = p.iloc[-1] / p.iloc[-1 - n] - 1\n    return float(ret / (sigma * np.sqrt(n)))"): "inside its own volatility window",
    (13, "p = prices.dropna()\n    r = p.pct_change()\n    sigma = r.iloc[-253:-1].std()\n"
         "    ret = p.iloc[-1] / p.iloc[-1 - n] - 1\n    return float(ret / sigma)"): "sigma * sqrt(n)",
    (13, "import numpy as np\n    p = prices.dropna()\n    sigma = p.iloc[-253:-1].std()\n"
         "    ret = p.iloc[-1] / p.iloc[-1 - n] - 1\n    return float(ret / (sigma * np.sqrt(n)))"): "not of prices",
    (14, "import pandas as pd\n    left, short, long_ = shares, 0.0, 0.0\n    for buy_date, n, buy_price in reversed(lots):\n"
         "        if left <= 0:\n            break\n        take = min(n, left)\n        gain = take * (price - buy_price)\n"
         "        if (pd.Timestamp(sell_date) - pd.Timestamp(buy_date)).days > 365:\n            long_ += gain\n        else:\n"
         "            short += gain\n        left -= take\n    return pd.Series({'short': short, 'long': long_})"): "LIFO",
    (14, "import pandas as pd\n    left, short, long_ = shares, 0.0, 0.0\n    for buy_date, n, buy_price in lots:\n"
         "        if left <= 0:\n            break\n        take = min(n, left)\n        gain = take * (price - buy_price)\n"
         "        if (pd.Timestamp(sell_date) - pd.Timestamp(buy_date)).days >= 365:\n            long_ += gain\n        else:\n"
         "            short += gain\n        left -= take\n    return pd.Series({'short': short, 'long': long_})"): "MORE than 365 days",
    (14, "import pandas as pd\n    left, short, long_ = shares, 0.0, 0.0\n    for buy_date, n, buy_price in lots:\n"
         "        if left <= 0:\n            break\n        take = min(n, left)\n        gain = take * price\n"
         "        if (pd.Timestamp(sell_date) - pd.Timestamp(buy_date)).days > 365:\n            long_ += gain\n        else:\n"
         "            short += gain\n        left -= take\n    return pd.Series({'short': short, 'long': long_})"): "sale proceeds",
    (15, "import math\n    import pandas as pd\n    s = pd.Series(excess, dtype=float)\n    mean, sd, n = s.mean(), s.std(ddof=0), len(s)\n"
         "    t = mean / (sd / math.sqrt(n))\n    need = math.ceil((2 * sd / mean) ** 2) if mean > 0 else float('nan')\n"
         "    return pd.Series({'mean': mean, 'sd': sd, 't': t, 'quarters_needed': need})"): "SAMPLE sd",
    (15, "import math\n    import pandas as pd\n    s = pd.Series(excess, dtype=float)\n    mean, sd, n = s.mean(), s.std(), len(s)\n"
         "    t = mean / sd\n    need = math.ceil((2 * sd / mean) ** 2) if mean > 0 else float('nan')\n"
         "    return pd.Series({'mean': mean, 'sd': sd, 't': t, 'quarters_needed': need})"): "square root of the sample size",
    (16, "import numpy as np\n    vol = px[tickers].tail(lookback + 1).pct_change().std() * np.sqrt(252)\n    inv = 1 / vol ** 2\n"
         "    return inv / inv.sum()"): "1 / variance",
    (16, "import numpy as np\n    vol = px[tickers].tail(lookback + 1).pct_change().std() * np.sqrt(252)\n    return 1 / vol"): "add up to 1",
    (16, "import numpy as np\n    vol = px[tickers].tail(lookback + 1).pct_change().std() * np.sqrt(252)\n    return vol / vol.sum()"): "jumpiest",
}


def test_every_slip_differs_from_the_right_answer_somewhere():
    for n, slips in check.SLIPS.items():
        right = check._load(ROOT / "practice" / "solutions", *check.EXERCISES[n])
        for wrong, msg in slips:
            assert any(check._same(wrong(*a), right(*a)) for a in check._args(n)), (n, msg)
    assert check.EARLY_SLIPS is check.SLIPS and 12 not in check.SLIPS
    assert sorted(check.SLIPS) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 31, 32, 33]


@pytest.mark.parametrize("key", list(EARLY_WRONG), ids=lambda k: f"ex{k[0]:02d}-{EARLY_WRONG[k][:14]}")
def test_early_exercise_slips_get_a_specific_hint(tmp_path, key):
    import re
    n, body = key
    mod, fn = check.EXERCISES[n]
    src = (ROOT / "practice" / "solutions" / f"{mod}.py").read_text()
    head = re.search(rf"def {fn}\(.*?\):\n", src).group(0)
    start = src.index(head) + len(head)
    code = src[:start] + "    " + body + "\n"
    (tmp_path / f"{mod}.py").write_text(code)
    ok, msg = check.check(n, tmp_path)
    assert not ok and "Hint:" in msg and EARLY_WRONG[key] in msg, msg


def test_where_prefix_reads_naturally():
    import pandas as pd
    px = pd.DataFrame()
    assert check._where((px, "MU")) == "for MU: "
    assert check._where((px, "MU", 252)) == "for MU, 252: "
    assert check._where((px,)) == "" and check._where((px, [1, 2])) == ""


def test_hint_ladder_has_three_levels_and_never_shows_the_whole_answer(tmp_path):
    store = tmp_path / "levels.json"
    assert sorted(check.HINT_LADDER) == sorted(check.EXERCISES)          # every exercise has a ladder
    for n in check.HINT_LADDER:
        body = check._body_lines(n)
        texts = [check.hint(n, store) for _ in range(4)]
        assert [t.split()[1] for t in texts] == ["1/3", "2/3", "3/3", "3/3"]         # stays at 3
        assert check.SKILLS[n] in texts[0] and check.HINT_LADDER[n][1] in texts[1]
        third = check.first_line_hint(n)
        assert third in texts[2]
        whole = "\n".join(body)
        assert whole not in texts[2] and "\n".join(b for b in body) not in "".join(texts)
        if n in check.LEVEL3_FROM:                                       # a helper's first line instead
            sol = (ROOT / "practice" / "solutions" / f"{check.EXERCISES[n][0]}.py").read_text()
            assert third in [ln.strip() for ln in sol.splitlines()]
        elif len(body) > 1:
            assert body[0].splitlines()[0].startswith(third)                # (a trailing comment dropped)
        else:
            assert third.endswith(" ...") and third[:-4] in body[0] and len(third[:-4]) < len(body[0])


def test_hint_counter_increments_resets_and_is_git_ignored(tmp_path):
    import json
    store = tmp_path / "levels.json"
    check.hint(5, store), check.hint(5, store), check.hint(2, store)
    assert json.loads(store.read_text()) == {"2": 1, "5": 2}
    check.reset_hints(5, store)
    assert json.loads(store.read_text()) == {"2": 1}
    check.reset_hints(None, store)
    assert not store.exists() and check._hint_levels(store) == {}
    assert "No hint ladder" in check.hint(99, store)            # future exercise numbers
    assert "practice/.hint_levels.json" in (ROOT / ".gitignore").read_text().splitlines()
    assert check.HINT_FILE == ROOT / "practice" / ".hint_levels.json"


def test_practice_html_shows_hints_used(tmp_path):
    import json
    store = tmp_path / "levels.json"
    store.write_text(json.dumps({"3": 2, "7": 3}))
    page_path, _ = check.write_html(tmp_path / "p.html", done={n: False for n in check.EXERCISES},
                                    today="2026-10-16", hints_path=store)
    page = page_path.read_text()
    assert page.count("hints used:") == 2 and "hints used: 2" in page and "hints used: 3" in page
    plain, _ = check.write_html(tmp_path / "q.html", done={n: False for n in check.EXERCISES},
                                today="2026-10-16", hints_path=tmp_path / "missing.json")
    assert "hints used" not in plain.read_text()


def test_hint_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check, "HINT_FILE", tmp_path / "h.json")
    assert check.main(["5", "--hint"]) == 0 and "Hint 1/3 for ex05" in capsys.readouterr().out
    assert check.main(["5", "--hint"]) == 0 and "Hint 2/3" in capsys.readouterr().out
    assert check.main(["--hint", "reset"]) == 0 and "cleared" in capsys.readouterr().out
    assert check.main(["5", "--hint"]) == 0 and "Hint 1/3" in capsys.readouterr().out



def test_hint_ladder_texts_are_short_and_name_real_methods():
    import re
    for n, (look, steps) in check.HINT_LADDER.items():
        assert look.count("\n") == 0 and steps.count("\n") <= 1, n           # each level fits in 2 lines
        sol = (ROOT / "practice" / "solutions" / f"{check.EXERCISES[n][0]}.py").read_text()
        names = set(re.findall(r"\.?([A-Za-z_][A-Za-z_0-9]*)\(", look)) | set(re.findall(r"\.([A-Za-z_]+)", look))
        names |= set(re.findall(r"\b(zip|enumerate|next|min|max|sorted|set|dict|assert|in)\b", look))
        assert any(re.search(rf"\b{re.escape(x)}\b", sol) for x in names), (n, names)
        assert check.first_line_hint(n) not in ("", "...")


def test_ex31_matches_risk_py_on_the_demo_and_catches_slips(tmp_path):
    import numpy as np
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    import risk
    sol = ROOT / "practice" / "solutions"
    b = check._load(sol, "ex31_beta_and_a_bad_day", "beta")
    v = check._load(sol, "ex31_beta_and_a_bad_day", "var95")
    for args in check._beta_args():
        assert b(*args) == pytest.approx(risk.beta(*args), abs=1e-12)
    for r, amt in check._var_args():
        assert v(r, amt) == pytest.approx(risk.var_95(r) * amt, abs=1e-9)
    # the real Risk card numbers: same portfolio returns risk.portfolio_risk builds
    _, px = check.data()
    w = pd.Series({"MU": 1.0, "NVDA": 1.0, "TXN": 1.0})
    r1 = risk._port(risk._returns(px, list(w.index), risk.TRADING_DAYS), w)
    r2 = risk._port(risk._returns(px, list(w.index), 2 * risk.TRADING_DAYS), w)
    out = risk.portfolio_risk(px, dict(w), pd.DataFrame({"SPY": check._spy()}), amount=1000.0)
    assert b(r1, check._spy().pct_change().reindex(r1.index)) == pytest.approx(out["beta_spy"], abs=1e-12)
    assert v(r2, 1000.0) == pytest.approx(out["var95_dollars"], abs=1e-9)
    assert np.isnan(b(pd.Series([0.01, 0.02]), pd.Series([0.0, 0.0])))
    src = (sol / "ex31_beta_and_a_bad_day.py").read_text()
    cases = [
        ([("v = j.iloc[:, 1].var()\n    return float(j.iloc[:, 0].cov(j.iloc[:, 1]) / v) if v > 0 else float(\"nan\")",
           "return float(j.corr().iloc[0, 1])")], "CORRELATION"),
        ([("v = j.iloc[:, 1].var()", "v = j.iloc[:, 0].var()")], "MARKET's variance"),
        ([("v = j.iloc[:, 1].var()", "v = j.iloc[:, 1].var(ddof=0)")], "same n"),
        ([("j = pd.concat([stock_returns, market_returns], axis=1, sort=True).dropna()\n    v = j.iloc[:, 1].var()\n"
           "    return float(j.iloc[:, 0].cov(j.iloc[:, 1]) / v) if v > 0 else float(\"nan\")",
           "a, c = stock_returns.dropna().to_numpy(), market_returns.dropna().to_numpy()\n    k = min(len(a), len(c))\n"
           "    a, c = a[-k:], c[-k:]\n    return float(np.cov(a, c)[0, 1] / np.var(c, ddof=1))")], "by DATE"),
        ([("-np.percentile(r, 5) * amount", "np.percentile(r, 95) * amount")], "95th percentile"),
        ([("-np.percentile(r, 5) * amount", "np.percentile(r, 5) * amount")], "POSITIVE"),
        ([("-np.percentile(r, 5) * amount", "-np.percentile(r, 5)")], "Multiply by `amount`"),
        ([("-np.percentile(r, 5) * amount", "-r.mean() * amount")], "average day"),
    ]
    for edits, want in cases:
        code = src
        for old, new in edits:
            assert old in code, old
            code = code.replace(old, new, 1)
        (tmp_path / "ex31_beta_and_a_bad_day.py").write_text(code)
        ok, msg = check.check(31, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_ex32_matches_backtest_and_risk_and_catches_slips(tmp_path):
    import numpy as np
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    import backtest
    import risk
    sol = ROOT / "practice" / "solutions"
    sh = check._load(sol, "ex32_sharpe_and_effective_bets", "sharpe")
    eb = check._load(sol, "ex32_sharpe_and_effective_bets", "effective_bets")
    # the Backtest tab's Sharpe is backtest.stats(daily curve)["sharpe"]; data.json only keeps a weekly,
    # rounded copy of the curve, so compare with the function itself on daily curves
    for (c,) in check._sharpe_args():
        assert sh(c) == pytest.approx(backtest.stats(c)["sharpe"], abs=1e-9)
    for r, w in check._eb_args():
        assert eb(r, w) == pytest.approx(risk.effective_bets(r, pd.Series(w, dtype=float)), abs=1e-9)
    flat = pd.Series([1.0] * 10, index=pd.bdate_range("2024-01-01", periods=10))
    assert np.isnan(sh(flat))
    src = (sol / "ex32_sharpe_and_effective_bets.py").read_text()
    s1 = "    vol = r.std() * np.sqrt(252)\n    return float((r.mean() * 252) / vol) if vol else float(\"nan\")"
    cases = [
        ([(s1, "    return float(r.mean() / r.std())")], "DAILY Sharpe"),
        ([(s1, "    return float(r.mean() / r.std() * 252)")], "SQUARE ROOT"),
        ([(s1, "    return float(curve.mean() * 252 / (curve.std() * np.sqrt(252)))")], "daily RETURNS"),
        ([(s1, "    years = (curve.index[-1] - curve.index[0]).days / 365.25\n"
               "    return float((curve.iloc[-1] ** (1 / years) - 1) / (r.std() * np.sqrt(252)))")], "not the CAGR"),
        ([("sigma = np.sqrt(np.diag(cov))", "sigma = np.diag(cov)")], "STD (sqrt"),
        ([("return float((wv.values @ sigma / port) ** 2)", "return float(wv.values @ sigma / port)")], "square it"),
        ([("cov = r.cov().values", "cov = r.corr().values")], "COVARIANCE"),
        ([("wv = pd.Series(w, dtype=float).reindex(r.columns).fillna(0)", "wv = pd.Series(1.0, index=r.columns)")], "weights you were given"),
    ]
    for edits, want in cases:
        code = src
        for old, new in edits:
            assert old in code, old
            code = code.replace(old, new, 1)
        (tmp_path / "ex32_sharpe_and_effective_bets.py").write_text(code)
        ok, msg = check.check(32, tmp_path)
        assert not ok and want in msg, (want, msg)


def test_ex33_matches_paper_performance_and_catches_slips(tmp_path):
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    import config
    import paper
    sol = ROOT / "practice" / "solutions"
    pr = check._load(sol, "ex33_paper_portfolio_return", "paper_return")
    for args in check._args(33):
        entries, px = args[0], args[1]
        if len(args) == 2:                       # the dashboard's own function, default cost
            perf = paper.performance({"entries": entries}, px, pd.DataFrame(index=px.index))
            assert pr(entries, px, config.COST_BPS) == pytest.approx(perf["stats"]["paper"]["total_return"], abs=1e-12)
    src = (sol / "ex33_paper_portfolio_return.py").read_text()
    cases = [
        ([('w = pd.Series(1 / len(e["picks"]), index=e["picks"])', 'w = pd.Series(1 / len(entries[0]["picks"]), index=entries[0]["picks"])'),
          ('.reindex(columns=e["picks"])', '.reindex(columns=entries[0]["picks"])')], "REPLACES the picks"),
        ([('w = pd.Series(1 / len(e["picks"]), index=e["picks"])',
           'last = px.loc[:d].ffill().iloc[-1].reindex(e["picks"]).fillna(0)\n        w = last / last.sum()')], "not weights by price"),
        ([("(daily.index > d)", "(daily.index >= d)")], "day AFTER"),
        ([("        value *= 1 - w.subtract(prev_w, fill_value=0).abs().sum() * cost_bps / 1e4\n", "")], "trading cost"),
    ]
    for edits, want in cases:
        code = src
        for old, new in edits:
            assert old in code, old
            code = code.replace(old, new, 1)
        (tmp_path / "ex33_paper_portfolio_return.py").write_text(code)
        ok, msg = check.check(33, tmp_path)
        assert not ok and want in msg, (want, msg)


PUBLIC = ["EXERCISES", "PLAN", "PLAN_ORDER", "SKILLS", "HINT_LADDER", "LEVEL3_FROM", "HINT_FILE", "SLIPS", "EARLY_SLIPS",
          "VAR_SLIPS", "EB_SLIPS", "HINTS", "EX27_CASES", "EX28_COLOURS", "EX28_PAIRS", "EX29_CASES", "EX30_QUARTERS",
          "check", "report", "progress", "main", "hint", "reset_hints", "first_line_hint", "html_page", "write_html",
          "plan_text", "next_text", "data", "_args", "_load", "_same", "_spy", "_beta_args", "_var_args", "_sharpe_args",
          "_eb_args", "_paper_args", "_real_week_args", "_real_quarters_args", "_body_lines", "_hint_levels", "_where"]


def test_check_py_still_exposes_everything_after_the_split():
    import _cases
    import _hints
    for name in PUBLIC:
        assert hasattr(check, name), name
    assert check.SKILLS is _cases.SKILLS and check.SLIPS is _hints.SLIPS and check.HINTS is _hints.HINTS
    assert len((ROOT / "practice" / "check.py").read_text().splitlines()) < 900          # it stays small
