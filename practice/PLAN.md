# Study plan: 25 sessions in 5 weeks, plus a bonus

One exercise per session (about an hour of your ~2 h/day; use the rest to read the matching
part of `CODE_TOUR.md` or poke at the dashboard). The order builds skills in sequence:
each week uses what the last one taught.

**Where am I?** Run `python practice/check.py --next`. It checks everything quietly and tells
you which session is next. `python practice/check.py --plan` shows this whole table with ✓/✗.

Each session has:
- **Warm-up (10 min):** answer it in your head or in `docs/journal.md` before you code.
- **Unlocks:** the dashboard card you'll be able to read like an expert afterwards.
- **Stretch:** for a day when it clicked fast.

---

## Week 1: pandas basics

### Session 1: ex01 last_price
- **Skill:** pick a column, drop missing values, take the last row (`.dropna()`, `.iloc[-1]`).
- **Unlocks:** the price column of the Rankings table.
- **Warm-up:** why would a stock's last row be empty (NaN) on some days?
- **Stretch:** return the last price *and* its date.

### Session 2: ex02 daily_returns
- **Skill:** `.pct_change()`, which is today ÷ yesterday − 1 for every column at once.
- **Unlocks:** every chart built on returns (the backtest curve starts here).
- **Warm-up:** a stock goes 100 → 110 → 99. What are the two daily returns? Why doesn't it end at 0%?
- **Stretch:** find the single biggest one-day move in the table.

### Session 3: ex03 total_return
- **Skill:** slice by date with `.loc["2020-01-01":"2021-06-30"]`.
- **Unlocks:** "Since Oct 12: …" lines and every "return over a period" number.
- **Warm-up:** what's the total return if a stock goes 50 → 75?
- **Stretch:** compute it from daily returns instead (`(1 + r).prod() - 1`) and check they match.

### Session 4: ex04 best_stock
- **Skill:** math on whole rows, `.idxmax()` to get *which* stock won.
- **Unlocks:** the momentum idea behind the "Price momentum" factor.
- **Warm-up:** why does the dashboard skip the last month when it measures momentum?
- **Stretch:** return the top 3, not just the best.

### Session 5: ex07 monthly_returns
- **Skill:** `groupby` by month (or `resample`).
- **Unlocks:** the month-by-month view behind Up/down capture.
- **Warm-up:** why are monthly returns less noisy than daily ones?
- **Stretch:** which calendar month (Jan, Feb, ...) was best on average?

## Week 2: risk, and checking your own work

### Session 6: ex05 annual_vol
- **Skill:** `.std()` on recent returns, × √252 to annualize.
- **Unlocks:** the "Volatility" factor and the risk numbers on the paper portfolio.
- **Warm-up:** why √252 and not 252?
- **Stretch:** compare 1-month and 1-year volatility for the same stock. Which moves more?

### Session 7: ex06 max_drawdown
- **Skill:** `.cummax()`, the running high.
- **Unlocks:** "Max DD" in every backtest table.
- **Warm-up:** 100 → 150 → 75 → 120. What's the max drawdown?
- **Stretch:** also return the date of the bottom.

### Session 8: ex12 write_a_test
- **Skill:** write a test that catches two buggy versions of your own function.
- **Unlocks:** `tests/`: why the dashboard can change every 30 minutes without breaking.
- **Warm-up:** what's one input that would expose a drawdown function that measures from the first price?
- **Stretch:** add a third bug and make sure your test catches it too.

### Session 9: ex09 gross_margin
- **Skill:** combine two tables (revenue and cost of goods) by date.
- **Unlocks:** "Gross-margin change YoY" in the stock details.
- **Warm-up:** a company sells $100 of chips that cost $40 to make. What's the gross margin?
- **Stretch:** compute the year-over-year change in margin.

### Session 10: ex08 group_median
- **Skill:** `groupby` by a category, using the median instead of the mean.
- **Unlocks:** the Semis cycle card and the group leadership view.
- **Warm-up:** why median and not mean when one company grows 300%?
- **Stretch:** add a count per group so tiny groups stand out.

## Week 3: factors and backtests

### Session 11: ex10 momentum_z
- **Skill:** your first factor, plus a z-score (how unusual is it vs the other stocks?).
- **Unlocks:** the colored cells in the Rankings heatmap.
- **Warm-up:** a z-score of +2 means what, in plain words?
- **Stretch:** clip the extremes to the 5th/95th percentile first, like `factors.py` does.

### Session 12: ex13 z_move
- **Skill:** "is today's move unusual?" using the std of a recent window.
- **Unlocks:** the "unusual move" alerts.
- **Warm-up:** a stock that usually moves ±1% a day moves −4%. Unusual?
- **Stretch:** list every day in the last year with |z| > 3.

### Session 13: ex11 mini_backtest
- **Skill:** pick by a factor on one date, hold, measure, without peeking at the future.
- **Unlocks:** the whole Backtest tab: you've now built a small one yourself.
- **Warm-up:** what's look-ahead bias, and how could it sneak into a backtest?
- **Stretch:** run it for every quarter and average the results.

### Session 14: ex16 inverse_vol
- **Skill:** weights that add to 1, bigger for calmer stocks.
- **Unlocks:** the "Inverse-vol weights" row in the robustness table.
- **Warm-up:** two stocks, vol 20% and 40%. What inverse-vol weights do they get?
- **Stretch:** cap any single weight at 40% and re-spread the rest.

### Session 15: ex14 fifo_lots
- **Skill:** loops, `min()`, and dates: selling the oldest shares first.
- **Unlocks:** the tax-lot view on My stocks (short- vs long-term gains).
- **Warm-up:** you bought 10 shares at $50, then 5 at $80. You sell 12. Which shares went?
- **Stretch:** total the short-term and long-term gains separately.

## Week 4: is the edge real?

### Session 16: ex15 t_test
- **Skill:** mean, standard deviation, t-stat, and how many quarters you'd need.
- **Unlocks:** "Is the edge real?" on the Backtest tab.
- **Warm-up:** why does a bigger sample make the same average more convincing?
- **Stretch:** what t-stat would 5 more quarters at the same average give?

### Session 17: ex17 own_percentile
- **Skill:** boolean masks + `.sum()`, ties counting half.
- **Unlocks:** "P/S vs own 5y" in the Rankings table.
- **Warm-up:** is a stock at its 90th percentile of P/S cheap or expensive vs its own history?
- **Stretch:** compute it for every stock and sort.

### Session 18: ex19 rolling_excess
- **Skill:** `.shift(252)` for one-year returns, compounding vs adding.
- **Unlocks:** "Is the edge steady?" (rolling 1-year excess vs SPY).
- **Warm-up:** +10% then −10%: why isn't that 0%?
- **Stretch:** what share of 1-year windows beat SPY?

### Session 19: ex22 signal_decay
- **Skill:** "next trading day" with `DateOffset` + `searchsorted`; `None` for the future.
- **Unlocks:** "How long does a pick's edge last?"
- **Warm-up:** why might a signal work for 3 months but not 12?
- **Stretch:** add an 18-month horizon and see what happens.

### Session 20: ex24 up_down_capture
- **Skill:** monthly `resample`, boolean masks, a ratio of averages.
- **Unlocks:** the Up/down capture card.
- **Warm-up:** what would 120% up / 80% down capture mean for your account in a bad year?
- **Stretch:** compute it against both SPY and SOXX and explain the difference.

## Week 5: rebuild the dashboard's own logic

### Session 21: ex18 fake_the_network
- **Skill:** pass a function in as an argument, and test with a fake download, offline.
- **Unlocks:** how the live pipeline is rehearsed without the internet (`tests/fixtures/live_sim.py`).
- **Warm-up:** why test with fake data instead of calling Yahoo every time?
- **Stretch:** make your fake download fail once, then succeed, and handle it.

### Session 22: ex20 dedupe_log
- **Skill:** lists of dicts, tuples in a set, "a re-run replaces the day".
- **Unlocks:** the alert log (and why it never shows the same alert twice).
- **Warm-up:** why can't you put a dict in a set, but you can put a tuple?
- **Stretch:** keep the log sorted even if `old` arrives shuffled.

### Session 23: ex21 reproduce_the_score
- **Skill:** clip, z-score, sign flip, weighted average, matching the dashboard to 0.01.
- **Unlocks:** "How did #1 get its score?"
- **Warm-up:** why is low volatility a *negative*-sign factor?
- **Stretch:** reproduce #2 and #3 too.

### Session 24: ex23 explain_a_score_change
- **Skill:** split a change into exact pieces, even when a stat appears or disappears.
- **Unlocks:** "Biggest score moves" in the weekly digest.
- **Warm-up:** a stock's score rose but none of its own numbers changed. How?
- **Stretch:** explain the change for every stock, then find the one where "spread out" applies.

### Session 25: ex25 drawdown_episodes
- **Skill:** walk a Series with a bit of state, closing an episode that's still open at the end.
- **Unlocks:** "How long was it underwater?"
- **Warm-up:** which hurts more: −30% for 3 months, or −20% for 2 years? Why?
- **Stretch:** find the longest stretch the strategy spent *above* water.

## Week 6: bonus

### Session 26: ex26 bootstrap_a_range
- **Skill:** numpy random numbers with a seed, fancy indexing (`r[idx]`), `np.cumprod` along rows, percentiles.
- **Unlocks:** "What could $1,000 become?" on the Backtest tab.
- **Warm-up:** why replay quarters in blocks of 4 instead of one at a time?
- **Stretch:** replay SPY with the same `idx` and count how often the strategy finished ahead.

### Session 27: ex27 catch_a_bad_number
- **Skill:** a loop that remembers what it already threw away; median vs mean; no look-ahead.
- **Unlocks:** the "probably a units error, ignored" lines in How it works → Data health.
- **Warm-up:** revenue goes 100, 105, 110, 110,000. Which number is wrong, and how would you prove it with only the numbers before it?
- **Stretch:** make `lookback` and `jump` arguments you tune: what's the smallest jump that never flags the demo data?

### Session 28: ex28 readable_colours
- **Skill:** parse hex with `int(x, 16)`, a formula from a spec (WCAG), `max`/`min` so order doesn't matter.
- **Unlocks:** why every heat-map number on the dashboard is readable, in light and dark mode.
- **Warm-up:** grey #777777 sits halfway between black and white. Is black or white text easier to read on it? Guess, then check.
- **Stretch:** find the grey (#xxxxxx with all three the same) where black and white text tie.

### Session 29: ex29 what_changed_this_week
- **Skill:** compare two dicts (`.get()` for missing keys), filter with comprehensions, sort with a tuple key.
- **Unlocks:** the "What changed this week" card on the Rankings tab.
- **Warm-up:** a stock goes from #9 to #4. Did it climb or drop? By how much? What about a ticker that wasn't ranked last week?
- **Stretch:** add a "biggest mover overall" field: the single ticker with the largest move either way.

### Session 30: ex30 stayers_vs_new
- **Skill:** pair each item with the one before it (`zip(xs, xs[1:])`), split into two lists, a t-stat by hand.
- **Unlocks:** "Does a top-5 streak mean anything?" on the Factor report card tab.
- **Warm-up:** 5 picks in one quarter all beat the market. Is that 5 pieces of evidence, or closer to 1? Why?
- **Stretch:** split stayers into "2 quarters" and "3+ quarters" in a row. Does a longer streak help?

### Session 31: ex31 beta_and_a_bad_day
- **Skill:** line two Series up by date (`pd.concat(..., axis=1).dropna()`), covariance vs correlation, a percentile as a risk number.
- **Unlocks:** "Beta to S&P 500" and "A bad day (1 in 20)" on the Risk card.
- **Warm-up:** a stock with correlation 0.5 to the market but twice as jumpy: is its beta 0.5, 1 or 2? Why?
- **Stretch:** compute the 99% VaR (1 day in 100). How much bigger is it than the 95% one, and why isn't it 5x?

### Session 32: ex32 sharpe_and_effective_bets
- **Skill:** annualizing (× 252 for returns, × √252 for volatility), a covariance matrix, the `@` operator.
- **Unlocks:** "Sharpe" on the Backtest tab and "Effective bets" on the Risk card.
- **Warm-up:** two strategies both return 20% a year; one has 15% volatility, the other 40%. Which Sharpe is higher, and would you care?
- **Stretch:** what happens to effective bets if you double one stock's weight? Try it on the 5 demo stocks.

### Session 33: ex33 paper_portfolio_return
- **Skill:** a loop over holding periods with state (value, weights), drift, trading costs, no look-ahead.
- **Unlocks:** "Paper return" on the Paper tab: the number that proves (or disproves) the model.
- **Warm-up:** you hold 50/50 and one stock doubles. What are the weights now? What does rebalancing back to 50/50 cost?
- **Stretch:** run it with cost_bps=0 and 50. How much of the return do trading costs eat?

---

Done all 33? You've written a small version of every important part of SemiScope. Next
step: pick one card on the dashboard and add a feature to it yourself, with a test.
