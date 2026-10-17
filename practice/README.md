# Practice track

33 short exercises that use SemiScope's own (simulated) data. Each one is a file with a
plain-English goal, a hint, and a `# YOUR CODE HERE` spot.

```bash
python practice/check.py 1     # check one exercise
python practice/check.py       # check them all
python practice/check.py --next  # where am I? progress + the next session
python practice/check.py --plan  # the 6-week plan with ✓/✗
python practice/check.py --html  # write docs/practice.html: the plan as a checklist page
python practice/check.py 5 --hint  # stuck? a hint; ask again for a stronger one (3 levels)
```

The daily GitHub Action refreshes `docs/practice.html` from the exercises in the repo, and it only
commits when a ✓ changed. To refresh it on your own computer every time you commit, install the
optional hook once (from the repo root):

```
ln -s ../../scripts/pre-commit-practice.sh .git/hooks/pre-commit
```

It never blocks a commit; `rm .git/hooks/pre-commit` removes it.

How the checker is organised: `check.py` is the command line, `_cases.py` holds the exercise list
and the inputs each one is checked on, `_hints.py` the usual wrong answers and their hints.

**Not sure where to start?** Follow [PLAN.md](PLAN.md): 33 sessions over 6 weeks (the 6th is a bonus week) in an order where
each one builds on the last, each with a 10-minute warm-up question, the dashboard card it
unlocks, and a stretch goal. The table below is in exercise-number order, not study order.

| # | Exercise | Skill |
|---|---|---|
| 1 | last_price | selecting a column, `.dropna()`, `.iloc` |
| 2 | daily_returns | `.pct_change()` |
| 3 | total_return | slicing by date with `.loc` |
| 4 | best_stock | math on whole rows, `.idxmax()` |
| 5 | annual_vol | `.std()`, `.tail()`, annualizing |
| 6 | max_drawdown | `.cummax()` |
| 7 | monthly_returns | `groupby` by month |
| 8 | group_median | `groupby` by category (how `cycle.py` works) |
| 9 | gross_margin | `merge` two tables (how `fundamentals.py` works) |
| 10 | momentum_z | your first factor + z-score (how `factors.py` works) |
| 11 | mini_backtest | pick by factor, hold, measure, with no peeking (how `backtest.py` works) |
| 12 | write_a_test | write a test that catches two buggy functions (how `tests/` works) |
| 13 | z_move | "is this move unusual?" with `.std()` on a window (mirrors `moves.py`) |
| 14 | fifo_lots | loops, `min`, dates: tax lots first-in-first-out (mirrors `mytrades.fifo_sell`) |
| 15 | t_test | mean, sd, t-stat, solving for n (mirrors `confidence.py`) |
| 16 | inverse_vol | volatility weights that add to 1 (mirrors `sizing.py`) |
| 17 | own_percentile | boolean masks + `.sum()`, ties count half, `<` vs `<=` at the edges (mirrors `valuation.py`) |
| 18 | fake_the_network | pass a function in as an argument, then test with a fake download, offline (mirrors `tests/fixtures/live_sim.py`) |
| 19 | rolling_excess | `.shift(252)`, compounding vs adding returns, `.idxmin()` (mirrors `steady.py`) |
| 20 | dedupe_log | lists of dicts, tuples in a set, "replace the day" (mirrors `alerts.merge_log`) |
| 21 | reproduce_the_score | clip, z-score, sign flip, weighted average over the stats a stock has; must match the dashboard (mirrors `walkthrough.py`) |
| 22 | signal_decay | `pd.DateOffset` + `index.searchsorted` for "next trading day", `None` for the future, a t-stat corrected for overlap (mirrors `decay.py`) |
| 23 | explain_a_score_change | split a weighted average's change into exact pieces when factors appear or disappear; an honest one-word headline (mirrors `explain.py`, `score_moves.py`) |
| 24 | up_down_capture | `resample("ME")`, boolean masks (`df[df["b"] > 0]`), a ratio of averages vs an average of ratios (mirrors `capture.py`) |
| 25 | drawdown_episodes | `cummax()`, walking a Series with `enumerate(s.items())`, remembering a start position, an episode still open at the end (mirrors `drawdowns.py`) |
| 26 | bootstrap_a_range | numpy random numbers with a seed, fancy indexing, `np.cumprod` along rows, percentiles of the last column (mirrors `outcomes.py`) |
| 27 | catch_a_bad_number | a loop that remembers what it dropped, median vs mean, no look-ahead (mirrors `sanity.py`) |
| 28 | readable_colours | hex parsing with `int(x, 16)`, the WCAG luminance/contrast formula, picking the readable ink (mirrors `inkOn` in `docs/index.html`) |
| 29 | what_changed_this_week | two dicts of ranks, `.get()` for missing keys, sorting with a tuple key for ties (mirrors `week_diff.py`) |
| 30 | stayers_vs_new | `zip(xs, xs[1:])` to pair each quarter with the one before, a t-stat by hand with the sample sd (mirrors `streak_edge.py`) |
| 31 | beta_and_a_bad_day | aligning by date with `pd.concat(...).dropna()`, `.cov()` / `.var()`, `np.percentile` for value at risk (mirrors `risk.py`) |
| 32 | sharpe_and_effective_bets | annualizing returns vs volatility, `DataFrame.cov()`, `np.diag`, `@` for a portfolio's risk (mirrors `backtest.stats` and `risk.effective_bets`) |
| 33 | paper_portfolio_return | a loop over holding periods keeping value and drifted weights, trading costs, no look-ahead (mirrors `paper.performance`) |

One per practice session is a good pace. Stuck for 20+ minutes? Read the hint again, print
intermediate results (`print(x.head())`), and only then look in `solutions/`.
