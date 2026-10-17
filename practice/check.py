"""
Checks your practice answers.

    python practice/check.py        # check them all
    python practice/check.py 3      # check exercise 3 only
    python practice/check.py --next # progress bar + which exercise to do next (practice/PLAN.md)
    python practice/check.py --plan # the plan with ✓/✗
    python practice/check.py --html # write docs/practice.html (the same plan as a page)
    python practice/check.py 5 --hint        # stuck? a hint for exercise 5; ask again for a stronger one
    python practice/check.py --hint reset    # forget which hints you've seen

Your answer is compared with the reference solution on the same (offline,
simulated) SemiScope data, so the result is the same every time.

Three files: check.py (this one: the command line, check(), hints, the progress page),
_cases.py (the exercise list, study plan and the inputs each exercise is checked on) and
_hints.py (the usual wrong answers, written as code, and the hint for each).
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

# The exercise data and the hint code live in _cases.py and _hints.py; re-exported here so
# `check.SKILLS`, `check._args`, `check.SLIPS` ... keep working.
from _cases import (  # noqa: E402,F401
    EX23_HEADLINES,
    EX23_W,
    EX27_CASES,
    EX28_COLOURS,
    EX28_PAIRS,
    EX29_CASES,
    EX30_QUARTERS,
    EXERCISES,
    HINT_LADDER,
    LABEL_PCTS,
    LEVEL3_FROM,
    PLAN,
    PLAN_ORDER,
    SKILLS,
    _args,
    _beta_args,
    _boot_args,
    _capture_args,
    _dd_args,
    _dd_curve,
    _dd_norm,
    _decay_args,
    _eb_args,
    _fake_download,
    _load,
    _log_old,
    _paper_args,
    _paper_px,
    _q30,
    _real_data,
    _real_quarters_args,
    _real_score_args,
    _real_week_args,
    _same,
    _score_data,
    _sharpe_args,
    _spy,
    _table,
    _var_args,
    _weekly_ps,
    data,
)
from _hints import (  # noqa: E402,F401
    EARLY_SLIPS,
    EB_SLIPS,
    EX29_HINTS,
    EX30_CLASSIFY_HINTS,
    HINTS,
    SLIPS,
    VAR_SLIPS,
    _beta_positional,
    _buggy_drawdowns,
    _eb,
    _ex02_wrong_shift,
    _ex11,
    _ex13,
    _ex14,
    _ex15,
    _ex16,
    _ex27_variant,
    _ex28_variants,
    _ex29_variant,
    _ex30_classify_variant,
    _ex30_gap_variant,
    _hint17,
    _hint18,
    _hint19,
    _hint20,
    _hint21,
    _hint22,
    _hint23,
    _hint24,
    _hint25,
    _hint26,
    _hint27,
    _hint28,
    _hint29,
    _paper,
    _r32,
    _rows_close,
    _slip_hint,
)


def progress(folder: Path = HERE) -> dict[int, bool]:
    """{exercise: passed} for every exercise, without printing."""
    return {n: check(n, folder)[0] for n in EXERCISES}


def _bar(done: int, total: int, width: int = 25) -> str:
    k = round(width * done / total) if total else 0
    return "[" + "#" * k + "." * (width - k) + f"] {done}/{total} done"


def next_text(folder: Path = HERE, done: dict | None = None) -> str:
    done = progress(folder) if done is None else done
    n_done = sum(done.values())
    lines = [_bar(n_done, len(PLAN_ORDER))]
    todo = [n for n in PLAN_ORDER if not done.get(n)]
    if not todo:
        lines.append(f"All {len(PLAN_ORDER)} done. Next: add a feature to one dashboard card yourself, with a test.")
        return "\n".join(lines)
    n = todo[0]
    session = PLAN_ORDER.index(n) + 1
    week = next(w for w, ns in PLAN if n in ns)
    lines += [f"Next: session {session} ({week.split(':')[0]}): ex{n:02d} {EXERCISES[n][0][5:]}",
              f"  Skill: {SKILLS[n]}",
              f"  Open practice/{EXERCISES[n][0]}.py, then run: python practice/check.py {n}",
              "  Warm-up question and stretch goal: practice/PLAN.md"]
    return "\n".join(lines)


def plan_text(folder: Path = HERE, done: dict | None = None) -> str:
    done = progress(folder) if done is None else done
    out = []
    for week, ns in PLAN:
        out.append(week)
        for n in ns:
            out.append(f"  {'✓' if done.get(n) else '✗'} session {PLAN_ORDER.index(n) + 1:2d}: ex{n:02d} "
                       f"{EXERCISES[n][0][5:]:24s} {SKILLS[n]}")
    out.append(_bar(sum(done.values()), len(PLAN_ORDER)))
    return "\n".join(out)


def _esc(x) -> str:
    import html
    return html.escape(str(x), quote=True)


def _page_style() -> str:
    """Reuse weekly.html's <style> (same colours, light/dark) so the pages can't drift apart."""
    import re
    try:
        m = re.search(r"<style>(.*?)</style>", (HERE.parent / "docs" / "weekly.html").read_text(), re.S)
        base = m.group(1) if m else ""
    except OSError:
        base = ""
    return base + """
.bar{width:100%;height:12px;accent-color:var(--series-1);margin:8px 0 2px}
ol.plan{list-style:none;padding:0;margin:6px 0 0} ol.plan li{display:flex;gap:10px;align-items:baseline;padding:6px 0;border-top:1px solid var(--grid)}
ol.plan li:first-child{border-top:0}
.mark{flex:0 0 1.4em;font-weight:700;text-align:center} .done .mark{color:var(--pos)} .todo .mark{color:var(--text-muted)}
.next{background:var(--accent-soft);border-radius:8px;padding:6px 8px;margin:0 -8px}
code{font-size:13px;overflow-wrap:anywhere}
"""


def html_page(done: dict, when: str | None = None, hints: dict | None = None) -> str:
    """docs/practice.html: the plan as a checklist. Static: no scripts, works offline."""
    n_done, total = sum(1 for n in PLAN_ORDER if done.get(n)), len(PLAN_ORDER)
    todo = [n for n in PLAN_ORDER if not done.get(n)]
    nxt = todo[0] if todo else None
    out = ['<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           '<meta name="theme-color" content="#121211">\n<link rel="manifest" href="manifest.webmanifest">\n'
           '<link rel="icon" href="icon-192.png">\n<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
           '<title>SemiScope practice progress</title>\n<style>' + _page_style() + '</style>\n</head>\n<body>\n<div class="wrap">\n',
           '  <h1>Your practice progress</h1>\n',
           f'  <div class="sub">{_esc(n_done)} of {_esc(total)} exercises done'
           + (f' · checked {_esc(when)}' if when else '') + '</div>\n',
           '  <div class="sub noprint" style="margin-top:4px"><a href="index.html">← Dashboard</a> · '
           '<a href="weekly.html">Weekly review</a></div>\n',
           f'  <progress class="bar" max="{total}" value="{n_done}" aria-label="Exercises done: {n_done} of {total}">'
           f'{n_done}/{total}</progress>\n']
    if nxt is None:
        out.append('  <div class="card"><h2>All done</h2><p>Next: add a feature to one dashboard card yourself, with a test.</p></div>\n')
    else:
        mod = EXERCISES[nxt][0]
        out.append(f'  <div class="card" id="next-card"><h2>Next: session {PLAN_ORDER.index(nxt) + 1}, ex{nxt:02d} '
                   f'{_esc(mod[5:])}</h2><p class="sub">Skill: {_esc(SKILLS[nxt])}</p>'
                   f'<p>Open <code>practice/{_esc(mod)}.py</code>, then run <code>python practice/check.py {nxt}</code>. '
                   'The warm-up question and stretch goal are in <code>practice/PLAN.md</code>.</p></div>\n')
    for week, ns in PLAN:
        k = sum(1 for n in ns if done.get(n))
        out.append(f'  <div class="card"><h2>{_esc(week)} <span class="muted" style="font-weight:400">({k}/{len(ns)})</span></h2>'
                   '<ol class="plan">')
        for n in ns:
            ok = bool(done.get(n))
            cls = ("done" if ok else "todo") + (" next" if n == nxt else "")
            out.append(f'<li class="{cls}" id="ex-{n}" data-ex="{n}"><span class="mark" aria-hidden="true">{"✓" if ok else "○"}</span>'
                       f'<span><b>Session {PLAN_ORDER.index(n) + 1}: ex{n:02d} {_esc(EXERCISES[n][0][5:])}</b>'
                       f'<span class="sr-only"> ({"done" if ok else "not done yet"})</span><br>'
                       f'<span class="sub">{_esc(SKILLS[n])}</span>'
                       + (f' <span class="sub muted hints">· hints used: {int((hints or {})[n])}</span>' if (hints or {}).get(n) else '')
                       + '</span></li>')
        out.append('</ol></div>\n')
    out.append('  <p class="sub muted" style="margin-top:16px">Made by <code>python practice/check.py --html</code>: '
               'run it again after you pass an exercise.</p>\n</div>\n'
               "<script>if ('serviceWorker' in navigator && (location.protocol === 'https:' || "
               "['localhost','127.0.0.1'].includes(location.hostname))) navigator.serviceWorker.register('sw.js').catch(()=>{});</script>\n"
               '</body>\n</html>\n')
    return "".join(out).replace("</style>", ".sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}\n</style>", 1)


def _without_date(page: str) -> str:
    import re
    return re.sub(r" · checked \d{4}-\d{2}-\d{2}", "", page)


def write_html(path: Path | None = None, folder: Path = HERE, done: dict | None = None,
               today: str | None = None, hints_path: Path | None = None) -> tuple[Path, bool]:
    """Write the page; (path, changed). Left alone when only the 'checked <date>' text would
    change, so the daily job doesn't make a commit just because a day passed."""
    import datetime as _dt
    path = path or (HERE.parent / "docs" / "practice.html")
    done = progress(folder) if done is None else done
    page = html_page(done, today or _dt.date.today().isoformat(), _hint_levels(hints_path))
    try:
        old = path.read_text()
    except OSError:
        old = None
    if old is not None and _without_date(old) == _without_date(page):
        return path, False
    path.write_text(page)
    return path, True


def _check30(f_classify, folder, mod):
    import copy
    sol = HERE / "solutions"
    want_c = _load(sol, mod, "classify")
    for (qs,) in _args(30):
        try:
            got = f_classify(copy.deepcopy(qs))
        except NotImplementedError:
            return False, "not done yet (still raises NotImplementedError)"
        except Exception as e:  # noqa: BLE001
            tb = traceback.extract_tb(e.__traceback__)[-1]
            return False, f"classify crashed: {type(e).__name__}: {e} (line {tb.lineno})"
        want = want_c(qs)
        if not _rows_close(got, want):
            where = "the demo backtest's quarters" if len(qs) > 10 else f"{len(qs)} hand-made quarters ({[q['date'] for q in qs]})"
            msg = f"classify on {where}: expected {len(want)} rows starting {str(want[:2])[:150]},\n    you returned {str(got)[:150]}"
            for mode, hint in EX30_CLASSIFY_HINTS:
                if _rows_close(got, _ex30_classify_variant(qs, mode)):
                    return False, msg + f"\n    Hint: {hint}"
            return False, msg
    try:
        mine = _load(folder, mod, "gap_t")
    except AttributeError:
        return False, "classify is right; now write gap_t too"
    want_g = _load(sol, mod, "gap_t")
    flat = {"date": "z", "stay": [0.02], "new": [0.01]}
    cases = [want_c(qs) for (qs,) in _args(30)] + [[flat, dict(flat, date="y")], [flat], []]
    for rows in cases:
        try:
            g = mine(copy.deepcopy(rows))
        except NotImplementedError:
            return False, "classify is right; gap_t is not done yet"
        except Exception as e:  # noqa: BLE001
            return False, f"gap_t crashed: {type(e).__name__}: {e}"
        w = want_g(rows)
        if w is None and g is None:
            continue
        try:
            if w is not None and g is not None and abs(float(g) - w) < 1e-9:
                continue
        except (TypeError, ValueError):
            pass
        msg = f"gap_t on {len(rows)} rows: expected {w if w is None else round(w, 4)}, got {g!r}"
        if w is None:
            return False, msg + ". Hint: return None with fewer than 2 quarterly gaps, or when every gap is the same (sd 0)."
        for mode, hint in (("pool", "one gap per QUARTER (mean stay - mean new), then the t-test on those gaps; not all picks pooled together."),
                           ("ddof0", "use the SAMPLE sd: divide by (n - 1), not n.")):
            v = _ex30_gap_variant(rows, mode)
            try:
                if v is not None and g is not None and abs(float(g) - v) < 1e-9:
                    return False, msg + f"\n    Hint: {hint}"
            except (TypeError, ValueError):
                pass
        return False, msg
    return True, "both right: you can now test whether a streak means anything."


def check(n: int, folder: Path = HERE) -> tuple[bool, str]:
    """(passed, message) for exercise n using the code in `folder`."""
    mod, fn = EXERCISES[n]
    try:
        f = _load(folder, mod, fn)
    except Exception as e:  # noqa: BLE001  (a typo in their file shouldn't crash the checker)
        return False, f"your file has an error: {type(e).__name__}: {e}"
    if n == 12:
        right = _load(HERE / "solutions", "ex06_max_drawdown", "max_drawdown")
        try:
            f(right)
        except NotImplementedError:
            return False, "not done yet (still raises NotImplementedError)"
        except AssertionError as e:
            return False, f"your test FAILED a correct max_drawdown. Check your expected values. ({e})"
        except Exception as e:  # noqa: BLE001
            return False, f"your test crashed: {type(e).__name__}: {e}"
        for i, bad in enumerate(_buggy_drawdowns(), 1):
            try:
                f(bad)
            except AssertionError:
                continue
            except Exception as e:  # noqa: BLE001
                return False, f"your test crashed on buggy version {i}: {type(e).__name__}: {e}"
            return False, (f"your test let buggy version {i} pass. "
                           + ["Hint: that bug measures from the first price, not the peak." ,
                              "Hint: that bug returns a POSITIVE number."][i - 1])
        return True, "caught both bugs and passed the correct version. You wrote a real test!"
    want_f = _load(HERE / "solutions", mod, fn)
    for args in (_args(n) if n not in (25, 26, 29, 30) else []):   # 25, 26, 29, 30 compare their own way below
        try:
            got = f(*[a.copy() if hasattr(a, "copy") else a for a in args])
        except NotImplementedError:
            return False, "not done yet (still raises NotImplementedError)"
        except Exception as e:  # noqa: BLE001
            tb = traceback.extract_tb(e.__traceback__)[-1]
            return False, f"crashed: {type(e).__name__}: {e} (line {tb.lineno})"
        problem = _same(got, want_f(*args))
        if problem and n in HINTS:
            problem += HINTS[n](got, *args)
        if problem:
            return False, _where(args) + problem
    if n == 19:                                    # the worst-window function too
        try:
            mine = _load(folder, mod, "worst_window")
        except AttributeError:
            return False, "rolling_excess is right; now write worst_window too"
        right = _load(HERE / "solutions", mod, "worst_window")
        ex = _load(HERE / "solutions", mod, "rolling_excess")(*_args(19)[0])
        try:
            g = mine(ex.copy())
        except NotImplementedError:
            return False, "rolling_excess is right; worst_window is not done yet"
        except Exception as e:  # noqa: BLE001
            return False, f"worst_window crashed: {type(e).__name__}: {e}"
        w = right(ex)
        if not (isinstance(g, tuple) and len(g) == 2 and g[0] == w[0] and abs(float(g[1]) - w[1]) < 1e-9):
            return False, f"worst_window should return ({w[0].date()}, {w[1]:.4f}), got {g!r}. Hint: .idxmin()"
    if n == 27:                                    # the nonpositive() function too
        try:
            mine = _load(folder, mod, "nonpositive")
        except AttributeError:
            return False, "flag_jumps is right; now write nonpositive too"
        right = _load(HERE / "solutions", mod, "nonpositive")
        for v in EX27_CASES:
            try:
                g = mine(list(v))
            except NotImplementedError:
                return False, "flag_jumps is right; nonpositive is not done yet"
            except Exception as e:  # noqa: BLE001
                return False, f"nonpositive crashed on {v}: {type(e).__name__}: {e}"
            if list(g or []) != right(v):
                return False, (f"nonpositive({v}) should be {right(v)}, got {g!r}. "
                               "Hint: <= 0 (zero revenue is impossible too), and skip missing values (None).")
        return True, "both right: one bad SEC number can no longer fake a #1 stock."
    if n == 32:                                    # the effective_bets() function too
        try:
            mine = _load(folder, mod, "effective_bets")
        except AttributeError:
            return False, "sharpe is right; now write effective_bets too"
        right = _load(HERE / "solutions", mod, "effective_bets")
        for r, w in _eb_args():
            try:
                g = mine(r.copy(), dict(w))
            except NotImplementedError:
                return False, "sharpe is right; effective_bets is not done yet"
            except Exception as e:  # noqa: BLE001
                return False, f"effective_bets crashed: {type(e).__name__}: {e}"
            want = right(r, w)
            try:
                if abs(float(g) - want) < 1e-6:
                    continue
            except (TypeError, ValueError):
                return False, f"effective_bets should return a number like {want:.2f}, got {g!r}"
            msg = f"effective_bets for {', '.join(f'{k} {v}' for k, v in w.items())}: expected {want:.4f}, got {float(g):.4f}"
            for wrong, h in EB_SLIPS:
                try:
                    if abs(float(g) - wrong(r, w)) < 1e-6:
                        return False, msg + f"\n    Hint: {h}"
                except Exception:  # noqa: BLE001
                    pass
            return False, msg
        return True, "both right: the Backtest tab's Sharpe and the Risk card's effective bets, by hand."
    if n == 31:                                    # the var95() function too
        try:
            mine = _load(folder, mod, "var95")
        except AttributeError:
            return False, "beta is right; now write var95 too"
        right = _load(HERE / "solutions", mod, "var95")
        for r, amt in _var_args():
            try:
                g = mine(r.copy() if hasattr(r, "copy") else r, amt)
            except NotImplementedError:
                return False, "beta is right; var95 is not done yet"
            except Exception as e:  # noqa: BLE001
                return False, f"var95 crashed: {type(e).__name__}: {e}"
            w = right(r, amt)
            try:
                if abs(float(g) - w) < 1e-6:
                    continue
            except (TypeError, ValueError):
                return False, f"var95 should return a number like {w:.2f}, got {g!r}"
            msg = f"var95 for ${amt:,.0f}: expected {w:.2f}, got {float(g):.2f}"
            for wrong, h in VAR_SLIPS:
                try:
                    if abs(float(g) - wrong(r, amt)) < 1e-6:
                        return False, msg + f"\n    Hint: {h}"
                except Exception:  # noqa: BLE001
                    pass
            return False, msg
        return True, "both right: the Risk card's beta and bad-day loss, by hand."
    if n == 30:                                    # classify rows (floats, approx) then gap_t
        return _check30(f, folder, mod)
    if n == 29:                                    # dicts of lists: compare exactly, hint from known slips
        import copy
        for args in _args(29):
            try:
                got = f(*copy.deepcopy(args))
            except NotImplementedError:
                return False, "not done yet (still raises NotImplementedError)"
            except Exception as e:  # noqa: BLE001
                tb = traceback.extract_tb(e.__traceback__)[-1]
                return False, f"crashed on prev={args[0]}, cur={args[1]}: {type(e).__name__}: {e} (line {tb.lineno})"
            want = want_f(*args)
            if got == want:
                continue
            short = lambda d: {k: (v if len(str(v)) < 70 else str(v)[:67] + "...") for k, v in d.items()} if isinstance(d, dict) else d
            where = f"prev={args[0]}, cur={args[1]}, top_n={args[2]}"
            if len(where) > 160:
                where = "the dashboard's real week (docs/data.json)"
            return False, (f"on {where}:\n    expected {short(want)}\n    you returned {short(got)}" + _hint29(got, *args))
        return True, "matches the Rankings tab's 'What changed this week' card."
    if n == 28:                                    # contrast() and best_ink() too
        sol = HERE / "solutions"
        for name in ("contrast", "best_ink"):
            try:
                mine = _load(folder, mod, name)
            except AttributeError:
                return False, f"luminance is right; now write {name} too"
            right = _load(sol, mod, name)
            cases = EX28_PAIRS if name == "contrast" else [(c,) for c in EX28_COLOURS]
            for args in cases:
                try:
                    g = mine(*args)
                except NotImplementedError:
                    return False, f"luminance is right; {name} is not done yet"
                except Exception as e:  # noqa: BLE001
                    return False, f"{name}{args} crashed: {type(e).__name__}: {e}"
                w = right(*args)
                problem = _same(g, w)
                if not problem:
                    continue
                call = f"{name}({', '.join(map(repr, args))})"
                if name == "contrast":
                    try:
                        gf = float(g)
                        if gf < 1 and abs(gf - 1 / w) < 1e-9:
                            return False, f"{call} should be {w:.4f}, got {gf:.4f}. Hint: put the LIGHTER colour on top, so the ratio is >= 1."
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass
                    return False, f"{call}: {problem}. Hint: (L1 + 0.05) / (L2 + 0.05), don't forget the + 0.05s."
                lum = _load(sol, mod, "luminance")
                pure = "#0b0b0b" if (lum(args[0]) + 0.05) / 0.05 >= 1.05 / (lum(args[0]) + 0.05) else "#ffffff"
                hint = (" Hint: compare with the dashboard's dark ink #0b0b0b, not pure #000000."
                        if (g == pure and g != w) or str(g).lower() in ("#000000", "#000") else
                        " Hint: return the hex string \"#0b0b0b\" or \"#ffffff\" (on a tie, \"#0b0b0b\").")
                return False, f"{call}: {problem}.{hint}"
        return True, "all three right: the same maths picks the text colour on every heat-map cell."
    if n == 26:                                    # numpy arrays: shape + values, then summary()
        import numpy as _np
        for args in _args(26):
            try:
                got = f(list(args[0]), *args[1:])
            except NotImplementedError:
                return False, "not done yet (still raises NotImplementedError)"
            except Exception as e:  # noqa: BLE001
                tb = traceback.extract_tb(e.__traceback__)[-1]
                return False, f"crashed: {type(e).__name__}: {e} (line {tb.lineno})"
            want = want_f(*args)
            try:
                g = _np.asarray(got, dtype=float)
            except (TypeError, ValueError):
                return False, f"expected a numpy array, got {type(got).__name__}"
            if g.shape != want.shape:
                return False, f"expected shape {want.shape} (n_paths, 4*years), got {g.shape}" + _hint26(got, *args)
            if not _np.allclose(g, want):
                return False, (f"values differ. First path should start {_np.round(want[0, :3], 2).tolist()}, "
                               f"yours starts {_np.round(g[0, :3], 2).tolist()}" + _hint26(got, *args))
        try:
            mine = _load(folder, mod, "summary")
            paths = want_f(*_args(26)[1])
            s = mine(paths.copy())
        except NotImplementedError:
            return False, "block_paths is right; summary is not done yet"
        except Exception as e:  # noqa: BLE001
            return False, f"summary crashed: {type(e).__name__}: {e}"
        right = _load(HERE / "solutions", mod, "summary")(paths)
        if not isinstance(s, dict) or set(s) != set(right) or any(abs(float(s[k]) - right[k]) > 1e-9 for k in right):
            hint = ""
            if isinstance(s, dict) and "p50" in s and abs(float(s["p50"]) - float(_np.percentile(paths, 50))) < 1e-9:
                hint = " Hint: take percentiles of the LAST column (paths[:, -1]), where each replay ended."
            want_txt = {k: round(v, 2) for k, v in right.items()}
            return False, f"summary should be {want_txt}, got {s!r}.{hint}"
        return True, "both right: you can turn one backtest into an honest range."
    if n == 25:                                    # episodes: compare dates as strings, then underwater()
        for args in _args(25):
            try:
                got = f(args[0].copy())
            except NotImplementedError:
                return False, "not done yet (still raises NotImplementedError)"
            except Exception as e:  # noqa: BLE001
                tb = traceback.extract_tb(e.__traceback__)[-1]
                return False, f"crashed: {type(e).__name__}: {e} (line {tb.lineno})"
            want = _dd_norm(want_f(*args))
            try:
                g = _dd_norm(got) if isinstance(got, list) else None
            except (TypeError, ValueError, AttributeError) as e:
                return False, f"each episode should be a dict with peak/trough/recovery/depth ({e})"
            if g is None:
                return False, f"expected a list of episode dicts, got {type(got).__name__}"
            if g != want:
                return False, (f"expected {len(want)} episode(s): {want[:2]}\n    you returned {len(g)}: {g[:2]}"
                               + _hint25(g, want, args[0]))
        try:
            mine = _load(folder, mod, "underwater")
            uw = mine(_dd_curve([100, 120, 90, 130]))
        except NotImplementedError:
            return False, "episodes is right; underwater is not done yet"
        except Exception as e:  # noqa: BLE001
            return False, f"underwater crashed: {type(e).__name__}: {e}"
        if not isinstance(uw, pd.Series) or [round(float(x), 9) for x in uw] != [0.0, 0.0, -0.25, 0.0]:
            return False, f"underwater([100, 120, 90, 130]) should be [0, 0, -0.25, 0], got {list(uw) if hasattr(uw, '__iter__') else uw!r}"
        return True, "both right: you can measure how long a drop really lasted."
    if n == 23:                                    # the headline function too
        try:
            mine = _load(folder, mod, "headline")
        except AttributeError:
            return False, "explain_change is right; now write headline too"
        right = _load(HERE / "solutions", mod, "headline")
        for contribs, delta in EX23_HEADLINES:
            try:
                g = mine(dict(contribs), delta)
            except NotImplementedError:
                return False, "explain_change is right; headline is not done yet"
            except Exception as e:  # noqa: BLE001
                return False, f"headline crashed on {contribs}: {type(e).__name__}: {e}"
            w = right(contribs, delta)
            if g != w:
                hint = ""
                if w == "spread out" and contribs and isinstance(g, str) and g.startswith("mostly"):
                    top = max(contribs, key=lambda f: abs(contribs[f]))
                    if (contribs[top] > 0) != (delta > 0):
                        hint = " Hint: the top factor points the OTHER way from the move, so it can't be 'mostly' it."
                    else:
                        hint = " Hint: 'mostly' needs at least HALF of the move (abs(top) >= 0.5 * abs(delta))."
                return False, f"headline({contribs}, {delta}) should be {w!r}, got {g!r}.{hint}"
        return True, "both right: you can now say which stat moved a score, honestly."
    if n == 22:                                    # the t-stat function too
        try:
            mine = _load(folder, mod, "overlap_t")
        except AttributeError:
            return False, "excess_at is right; now write overlap_t too"
        right = _load(HERE / "solutions", mod, "overlap_t")
        vals = [0.02, -0.01, 0.035, 0.01, 0.0, 0.025, -0.005]
        for m in (1, 3, 6, 12):
            try:
                g = mine(list(vals), m)
            except NotImplementedError:
                return False, "excess_at is right; overlap_t is not done yet"
            except Exception as e:  # noqa: BLE001
                return False, f"overlap_t crashed: {type(e).__name__}: {e}"
            w = right(vals, m)
            try:
                ok = abs(float(g) - w) < 1e-9
            except (TypeError, ValueError):
                ok = False
            if not ok:
                s = pd.Series(vals)
                raw = s.mean() / (s.std() / np.sqrt(len(s)))
                hint = ""
                if g is not None and abs(float(g) - raw) < 1e-9 and m > 3:
                    hint = " Hint: divide by sqrt(months / 3) for overlapping windows."
                elif g is not None and abs(float(g) - s.mean() / (s.std(ddof=0) / np.sqrt(len(s))) / np.sqrt(max(1, m / 3))) < 1e-9:
                    hint = " Hint: use the SAMPLE std (ddof=1, pandas' .std() default; numpy's np.std uses ddof=0)."
                return False, f"overlap_t(values, {m}) should be {w:.4f}, got {g!r}.{hint}"
        return True, "both right: you measured signal decay and corrected the t-stat for overlap."
    if n == 21:                                    # same number the dashboard shows
        d = _real_data()
        if d is None:
            return True, "matches the reference. Run `python run.py --demo` to also check it against data.json."
        top = min((r for r in d["rankings"] if r.get("rank") is not None), key=lambda r: r["rank"])
        g = round(float(f(d, top["ticker"])), 2)
        if abs(g - round(float(top["score"]), 2)) > 0.011:
            return False, f"data.json says {top['ticker']} scores {top['score']:.2f}, you got {g:.2f}"
        return True, f"you reproduced #1 {top['ticker']}'s score: {g:.2f}, same as the dashboard."
    if n == 17:                                    # the label function, at every edge
        try:
            mine = _load(folder, mod, "valuation_label")
        except AttributeError:
            return False, "own_percentile is right; now write valuation_label too"
        right = _load(HERE / "solutions", mod, "valuation_label")
        for p in LABEL_PCTS:
            try:
                g = mine(p)
            except NotImplementedError:
                return False, "own_percentile is right; valuation_label is not done yet"
            except Exception as e:  # noqa: BLE001
                return False, f"valuation_label({p}) crashed: {type(e).__name__}: {e}"
            if g != right(p):
                edge = " Check < versus <= at that edge." if p in (10, 25, 75, 90) else ""
                return False, f"valuation_label({p}) should be {right(p)!r}, got {g!r}.{edge}"
    return True, "correct!"


def _where(args) -> str:
    """'for MU: ' / 'for MU, 252: ' - the arguments after the data, so you know which case failed."""
    def show(a):
        if isinstance(a, str):
            return a
        if isinstance(a, (int, float)) and not isinstance(a, bool):
            return repr(a)
        return None
    parts = [show(a) for a in args[1:]]
    parts = [p for p in parts if p is not None]
    return f"for {', '.join(parts)}: " if parts else ""


HINT_FILE = HERE / ".hint_levels.json"


def _body_lines(n) -> list[str]:
    """The answer's code lines (no imports, docstrings or comments), from the reference solution."""
    import ast
    mod, fn = EXERCISES[n]
    src = (HERE / "solutions" / f"{mod}.py").read_text()
    node = next(x for x in ast.parse(src).body if isinstance(x, ast.FunctionDef) and x.name == fn)
    lines = src.splitlines()
    out = []
    for st in node.body:
        if isinstance(st, (ast.Import, ast.ImportFrom)) or (isinstance(st, ast.Expr) and isinstance(getattr(st, "value", None), ast.Constant)):
            continue
        out.append("\n".join(lines[st.lineno - 1:st.end_lineno]).strip())
    return out


def first_line_hint(n) -> str:
    """Level 3: the first line of the answer. If the whole answer IS one line, only its start."""
    import re
    if n in LEVEL3_FROM:
        return LEVEL3_FROM[n]
    body = _body_lines(n)
    first = re.sub(r"\s{2,}#.*$", "", body[0].splitlines()[0])     # drop a trailing comment
    if len(body) > 1:
        return first
    cut = [i for i, c in enumerate(first) if c == "."]                # stop before the last method call
    keep = first[:cut[len(cut) // 2]] if cut else first[: len(first) // 2]
    return keep + " ..."


def _hint_levels(path: Path | None = None) -> dict:
    import json
    try:
        return {int(k): int(v) for k, v in json.loads((path or HINT_FILE).read_text()).items()}
    except (OSError, ValueError, AttributeError):
        return {}


def hint(n: int, path: Path | None = None) -> str:
    """The next hint for exercise n (1, 2, then 3; stays at 3). Remembers what you've seen."""
    import json
    if n not in HINT_LADDER:
        return f"No hint ladder for exercise {n} yet: read the HINT lines in its file and practice/PLAN.md."   # future exercises
    levels = _hint_levels(path)
    lv = min(levels.get(n, 0) + 1, 3)
    levels[n] = lv
    try:
        (path or HINT_FILE).write_text(json.dumps({str(k): v for k, v in sorted(levels.items())}))
    except OSError:
        pass
    text = {1: f"Skill: {SKILLS[n]}\n  {HINT_LADDER[n][0]}", 2: f"Steps: {HINT_LADDER[n][1]}",
            3: f"First line of the answer:\n    {first_line_hint(n)}"}[lv]
    more = "Run it again for a stronger hint." if lv < 3 else "That's the strongest hint. Try it, then check."
    return f"Hint {lv}/3 for ex{n:02d} {EXERCISES[n][0][5:]}:\n  {text}\n({more})"


def reset_hints(n: int | None = None, path: Path | None = None) -> str:
    import json
    p = path or HINT_FILE
    if n is None:
        try:
            p.unlink()
        except OSError:
            pass
        return "Hint levels cleared."
    levels = _hint_levels(path)
    levels.pop(n, None)
    p.write_text(json.dumps({str(k): v for k, v in sorted(levels.items())}))
    return f"Hint level for exercise {n} cleared."


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--html":
        p, changed = write_html(Path(argv[1]) if len(argv) > 1 else None)
        print(f"wrote {p}" if changed else f"{p} is already up to date")
        return 0
    if "--hint" in argv:
        rest = [a for a in argv if a != "--hint"]
        nums_ = [int(a) for a in rest if a.isdigit()]
        if "reset" in rest:
            print(reset_hints(nums_[0] if nums_ else None))
        elif nums_:
            print("\n\n".join(hint(n) for n in nums_))
        else:
            print("Which exercise? e.g. python practice/check.py 5 --hint")
        return 0
    if argv and argv[0] in ("--next", "--plan"):
        print(next_text() if argv[0] == "--next" else plan_text())
        return 0
    nums = [int(a) for a in argv] or list(EXERCISES)
    text, passed = report(nums)
    print(text)
    return 0 if passed == len(nums) else 1


def report(nums, folder: Path = HERE) -> tuple[str, int]:
    """What `python practice/check.py 1 2 ...` prints, and how many passed (docs/START_HERE.md
    quotes this output; a test checks the quote is still exact)."""
    lines, passed = [], 0
    for n in nums:
        ok, msg = check(n, folder)
        passed += ok
        lines.append(f"{'✓' if ok else '✗'} {n:2d}. {EXERCISES[n][1]:20s} {msg}")
    lines.append(f"\n{passed}/{len(nums)} done." + ("  Nice work!" if passed == len(nums) else ""))
    return "\n".join(lines), passed


if __name__ == "__main__":
    raise SystemExit(main())
