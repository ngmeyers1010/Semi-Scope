# SemiScope Code Tour

A beginner's walk through the codebase. Read it with the code open beside it.
You don't need to understand everything on day one. Each section stands alone, so
read one per practice session.

---

## 0. The big picture (read this first)

```
config.py ──► data_sources.py ──► fundamentals.py ──► factors.py ──► backtest.py
 (settings)    (download SEC +      (clean quarterly     (turn data     (test the
               Yahoo data)           numbers)             into scores)   strategy)
                                                              │
                         research.py, robustness.py, cycle.py, paper.py, alerts.py
                                                              │
                                    run.py  ──►  docs/data.json  ──►  docs/index.html
                                  (runs it all)   (results)           (the dashboard)
```

`run.py` is the "main" file. Everything else is a helper it calls. If you're
lost, open `run.py`, find `def main()`, and follow it top to bottom.

---

## 1. Five pandas ideas you'll see everywhere

**DataFrame**: a table. Rows have an *index* (dates, or tickers) and columns have names.
`px` (prices) is a DataFrame: one row per trading day, one column per ticker.

**Series**: one column of a DataFrame. `px["MU"]` is Micron's price history.

**Boolean filtering**: keep the rows where a condition is True.
```python
series[series["filed"] < asof]
```
`series["filed"] < asof` makes a column of True/False values, one per row. Putting
it inside `series[...]` keeps only the True rows. That one line is what stops the
backtest from cheating (see §4).

**groupby**: split a table into groups, do math on each group, then combine the results.
```python
hist.groupby("q")["g"].median()
```
In plain English: "for each quarter `q`, take the median of the growth column `g`."

**pct_change / cumprod**: turn prices into returns and back again.
```python
daily = px.pct_change()               # today's price / yesterday's - 1
growth = (1 + period).cumprod()       # multiply the (1 + return)s together = growth of $1
```

---

## 2. `config.py`: the settings

There is no logic here, only dictionaries and numbers. **This is the safest file to
experiment with.** `UNIVERSE` lists the stocks, `FACTORS` lists the stats and their
weights, and `TOP_N` sets how many stocks to hold.

```python
"momentum": {"weight": 1.0, "sign": +1, ...}
```
- `weight` sets how much the stat counts toward the score (0 = shown but not used).
- `sign` is `+1` if higher is better and `-1` if lower is better (like volatility).

---

## 3. `data_sources.py`: getting the data

Two sources:
- **SEC EDGAR** `companyfacts`: every number a company has ever reported in a filing, as JSON.
- **Yahoo Finance** via the `yfinance` library: daily prices and stock splits.

`_get_json` saves each download in `cache/`, so re-running doesn't hit the SEC again.
Being polite to free data sources keeps you from getting blocked.

---

## 4. `fundamentals.py` and `factors.py`: the heart of it

### Point-in-time (the most important idea in the project)
```python
def _known(series, asof):
    return series[series["filed"] < asof].sort_values("end")
```
Line by line:
1. `series` is a table with columns `end` (when the quarter ended), `val` (the number),
   and `filed` (the date the SEC received it).
2. `series["filed"] < asof` asks, for each row, "was this filed before the date we're
   pretending it is?"
3. Only those rows are kept, sorted by quarter.

Every factor calls `_known` first. That's how a backtest set in 2018 can't "see" a
report filed in 2019.

### Merging two tables
```python
m = rev.merge(gp, on="end", suffixes=("_r", "_g"))
cogs = pd.DataFrame({"end": m["end"], "val": m["val_r"] - m["val_g"], ...})
```
Some companies report gross profit but not cost of goods sold. `merge` lines up the
revenue and gross-profit rows that share the same quarter-end date, like a spreadsheet
VLOOKUP. Then cost = revenue − gross profit.

### z-scores (making different stats comparable)
```python
def _z(col):
    s = col.astype(float)
    lo, hi = s.quantile(0.05), s.quantile(0.95)
    s = s.clip(lo, hi)                       # 1. trim extreme outliers
    sd = s.std()
    return (s - s.mean()) / sd               # 2. distance from average, in std devs
```
Revenue growth is a percentage, while inventory change is measured in days. You
can't add those together. z-scores put every stat on the same scale, so they can be
averaged into one `score`.

---

## 5. `backtest.py`: did it work in the past?

Each quarter: score everything → buy the top 5 equally → hold → repeat.

```python
period = daily.loc[(daily.index > d) & (daily.index <= end), picks].fillna(0)
growth = (1 + period).cumprod()
path = value * (growth * w).sum(axis=1)
```
1. Take the daily returns of the 5 picks between this rebalance and the next.
2. `cumprod` turns them into "how much $1 grew" for each stock.
3. Multiply by the weights (0.2 each) and add them across stocks (`sum(axis=1)`) to get
   the portfolio value each day.

---

## 6. The research files

| File | Question it answers |
|---|---|
| `research.py` | Does each stat actually predict returns? (IC, t-stat) |
| `robustness.py` | Do the results survive small rule changes? |
| `cycle.py` | Where is the chip industry in its cycle? |
| `paper.py` | How are the live, logged picks doing? |
| `alerts.py` | What changed since the last run? |

`robustness.py` has a nice speed trick: it scores every month **once**, saves the
results in a dict (`cache`), and reuses them for all 16 variants.

---

## 6b. The newer analysis files

| File | Key idea | pandas move to look for |
|---|---|---|
| `cycle.py` | Classify the industry as Upswing / Late cycle / Downturn / Recovery from median sales growth and how many companies are accelerating | `groupby("q")["g"].median()` |
| `data_health.py` | Count quarters of data, check filing freshness, flag impossible values | `merge` of revenue and COGS on `end` |
| `digest.py` | Turn the big `data` dict into 5 plain-English bullet groups | plain Python dicts and f-strings — no pandas needed |
| `attribution.py` | Contribution = weight × return; sum by stock and by group | `groupby("ticker").agg(contrib=("contrib", "sum"), ...)` |

### The sell rule (`buffer_schedule` in `robustness.py`)
```python
allowed = set(order[:buffer])                  # stocks ranked inside the buffer
keep = [h for h in holdings if h in allowed]   # keep holdings still inside it
for t in order:                                # refill from the top
    if len(keep) >= n: break
    if t not in keep: keep.append(t)
```
A **list comprehension** (`[h for h in holdings if ...]`) builds a new list by filtering
an old one. It's the plain-Python version of boolean filtering in pandas.

---

## 7. `run.py` and the dashboard

`run.py` collects everything into one big dictionary and saves it as `docs/data.json`.
`docs/index.html` is plain HTML + JavaScript. It loads that JSON and draws the
tables and charts. There's no server, which is why it can be hosted free on GitHub Pages.

---

## 8. Tests (`tests/test_pipeline.py`)

Tests are small programs that check the main program. Run them with:
```bash
python -m pytest tests
```
The most important one is `test_no_lookahead`. It scores stocks with all the data,
then again with the future deleted, and checks the two scores match exactly. If you
ever change `factors.py` and this test fails, you introduced a cheat.

---

## 8b. Test fixtures and retries (round 17)

`tests/fixtures/*.json` are tiny fake SEC files, each copying one real-world mess
(Apple's 53-week year, Nvidia's January year-end and renamed revenue tag,
Alphabet's three share classes). `make_fixtures.py` builds them, so read that
file to see what each quirk looks like in raw SEC data.

`data_sources.py` now retries failed downloads:
```python
Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
```
That means "if the server says *too many requests* (429) or has an error (5xx),
wait 1s, 2s, 4s and try again." **Backoff** (waiting longer each time) is the polite
way to retry.

`test_price_retry_keeps_good_tickers` uses **monkeypatch**, which swaps the real
`yfinance` for a fake one during the test, so it can simulate a flaky
download without internet.

### `runlog.py` and try / except (round 18)
```python
try:
    _main(log)
except BaseException as e:
    runlog.append("failed", log, error=f"{type(e).__name__}: {e}")
    raise
```
`try` runs the code; if anything goes wrong, Python jumps to `except` instead of
crashing immediately. We write a "failed" line to the log, then `raise` re-throws
the same error so GitHub still marks the run red. **Catch, record, re-raise** is a
common pattern for "I want to know it broke, but I don't want to hide that it broke."

---

## 8c. `streamlit_app.py`: build your own app (round 19)

Streamlit turns a Python script into a web page. Three ideas cover most of it:

1. **The script re-runs on every click.** Pick a new stock and Streamlit runs the whole
   file again from the top with the new value. There are no event handlers to wire up.
2. **Each `st.something()` call draws one thing**, in order: `st.title`, `st.metric`,
   `st.line_chart`, `st.dataframe`.
3. **Layout uses `with`:**
   ```python
   left, right = st.columns(2)
   with left:
       st.bar_chart(...)     # lands in the left column
   ```

The file has two halves. **Pure helpers** at the top (`rankings_table`, `history_table`,
`factor_z`, ...) just reshape data with pandas, so `tests/test_streamlit_app.py` can test
them without a browser. **`main()`** at the bottom draws the page. Keeping logic separate
from display is the most useful habit in app building.

A bug the tests caught while this was being built: `factor_z` flipped the sign of
"lower is better" stats a second time, because `factors.py` already flips them, so
inventory and volatility bars pointed the wrong way. `test_factor_bars_match_score_direction`
now checks the bars add up to the actual score.

---

## 8d. `orders.py`: a greedy algorithm (round 20)

Buying whole shares with a fixed budget leaves cash over. `plan()` spends it with a
**greedy algorithm**: repeatedly make the best single choice right now.
```python
fits = [r for r in live if r["price"] <= left]       # picks we can still afford one share of
r = min(fits, key=lambda r: r["cost"] / target)       # the one furthest below its target
```
`min(..., key=...)` means "the item with the smallest value of this formula." A
`lambda` is a tiny one-line function. Greedy isn't always perfect, but it's simple
and good enough here.

The dashboard runs the same algorithm in JavaScript so it updates as you type.
`tests/test_orders.py` runs both on the same inputs and checks they match, which is
how you keep two copies of one idea from drifting apart.

---

## 8e. Out-of-sample and walk-forward (round 21)

**The problem:** the factor weights in `config.py` were chosen while looking at the
same history the backtest runs on. That's like grading a test you wrote after seeing
the answers.

**Fix 1: split the history** (`research.oos_check`). Compare each stat's IC before
2020 with its IC after. `split_quarters` drops the one quarter that crosses the split,
so no day's return counts in both periods.

**Fix 2: walk-forward** (`robustness.walk_forward_weights`). At every rebalance,
weight each stat by how well it worked over the *previous 3 years only*:
```python
known = [ics for k, ics in hist if lo < k <= d]   # quarters already FINISHED by date d
w = df.mean().clip(lower=0)                        # stats that stopped working get weight 0
```
The key is `k`, the date a quarter's result became **known** (its end), not the
date it started. Mixing those up is the most common way backtests accidentally
cheat. `test_walk_forward_weights_have_no_lookahead` deletes all data after `d` and
checks that the weights don't change.

---

## 8f. `mytrades.py`: money-weighted vs time-weighted (round 22)

Say you put in $100, it grows to $110, then you add $100 more. Your account shows $210.
- **Money-weighted** ("what did I make?"): $210 − $200 put in = **+$10**.
- **Time-weighted** ("how good were the picks?"): **+10%**, no matter when or how much you added.

The daily time-weighted step removes that day's deposit before measuring:
```python
r = (value - cf) / prev - 1      # cf = money added today
twr = (1 + r).cumprod()          # chain the daily returns together
```
`test_deposits_are_not_gains` checks that a deposit on a flat-price day gives exactly 0%.

`load()` also shows a habit worth copying: **validate input and explain problems instead of
crashing**. A typo in one line of your CSV becomes a warning on the dashboard, and the
other lines still work.

---

## 8g. `quarterly.py`: periods and pure functions (round 23)

pandas understands calendar periods, not just dates:
```python
pd.Timestamp("2026-03-31").to_period("Q")   # Period('2026Q1')
pd.Period("2026Q1", freq="Q").end_time      # 2026-03-31 23:59:59...
s.groupby(s.index.to_period("Q"))           # one group per calendar quarter
```
`build_report(data, q)` is a **pure function**: same input, same output, no files, no
internet. That makes it easy to test (`tests/test_quarterly.py` feeds it tiny fake
dicts). The *impure* part, writing files, lives separately in `write_new`, which
refuses to overwrite a report that already exists.

The dashboard renders the Markdown with a ~25-line converter (`mdToHtml` in
`index.html`). It **escapes HTML first** (`<` becomes `&lt;`), so text in a report can
never inject code into the page. A test checks that a `<script>` tag comes out harmless.

---

## 8h. Sharing code between pages (round 24)

`docs/setup_steps.js` holds `stepsDone()`, which both `index.html` (the banner) and
`setup.html` (the checklist) load with `<script src="setup_steps.js">`. One copy means the two
pages can never disagree. The last line,
```js
if (typeof module !== 'undefined') module.exports = {...}
```
lets the same file also run in Node, which is how `tests/test_setup.py` checks it against the
Python version in `check_setup.py`.

---

## 8i. `explain.py`: an exact decomposition (round 25)

The score is a weighted average: `score = Σ w·z / W`. So the change splits exactly into
pieces, one per factor:
```python
contrib = w * z_now / W_now - w * z_prev / W_prev
```
Add the pieces up and you get exactly `score_now - score_prev`. `test_contributions_sum_to_score_change`
checks this on 50 random examples. Writing the formula so it *must* add up (instead of
approximating) is a good habit: you never have to explain a leftover "other".

Note that z-scores are **relative**. If every other company's inventory improves and MU's
stays flat, MU's inventory z-score falls. That's why a stat can move the score even when the
company's own number didn't change.

---

## 8j. `risk.py`: matrix math in one line (round 26)

Portfolio volatility needs every pair of stocks, not just each one alone:
```python
port = np.sqrt(w @ cov @ w)        # @ = matrix multiply
```
`cov` is the covariance matrix (how each pair moves together). `w @ cov @ w` adds up
weight × weight × covariance over every pair. When stocks move together, the pair terms
are big and the portfolio is barely calmer than one stock.

**Effective bets** compares two numbers: the weighted average of each stock's own
volatility (`w @ sig`) and the portfolio's volatility. If diversification helps a lot,
the portfolio is much calmer than its parts. The ratio, squared, says how many unrelated
stocks you'd need for the same effect. The tests check the two extremes: identical
stocks give 1, unrelated stocks give N.

---

## 8k. Practice track (round 27)

Once you've read a section of this tour, do the matching exercise in `practice/`:

| Tour section | Exercise |
|---|---|
| §1 pandas ideas | 1–5 |
| §5 backtest (cumprod) | 6, 11 |
| §6b cycle (groupby) | 7, 8 |
| §4 fundamentals (merge) | 9 |
| §4 z-scores | 10 |
| §8 tests | 12 |

Progress: `python practice/check.py` prints e.g. `7/12 done.`

---

## 8l. Finding dividends hidden in two price columns (round 28)

Yahoo gives two prices: **Close** (what traded) and **Adj Close** (as if every dividend
were reinvested). On a dividend day the plain price drops by about the dividend, but the
adjusted price doesn't. The gap between the two daily returns *is* the dividend:
```python
d = close.shift(1) * (adj.pct_change() - close.pct_change())
```
Then `held.shift(1) * d`: you only get the dividend if you owned the shares at the
**previous** close, which is exactly how the real ex-dividend rule works.

---

## 8m. Making a website installable (round 29)

Three small files turn the dashboard into an app:
- `manifest.webmanifest`: the app's name, icon and colors (plain JSON).
- `sw.js`, a **service worker**: a script the browser runs *between* the page and the
  internet. Ours tries the network first and saves a copy of each file. When there's no
  signal, it hands back the saved copy. That's the whole trick behind "works offline".
- `make_icons.py`: draws the icon with Pillow (`ImageDraw.rectangle`, `.line`, `.ellipse`).
  Change the colors at the top and re-run it to make it yours.

---

## 8n. Making code fast: measure first (round 30)

```bash
python -m cProfile -s cumulative run.py --demo | head -40
```
The profile showed something surprising: the slow part wasn't the math. It was **tiny
pandas operations repeated 65,000 times** (`_known` filtering a 40-row table). Each one
takes ~1 ms of pandas overhead. The fix in `factors.py`:
1. Convert each company's series to plain numpy arrays **once** (`_arrays`).
2. Filter with a boolean mask on arrays (`_Known`), which is microseconds instead of milliseconds.
3. **Memoize** `score()`: the backtest and the robustness grid ask for the same dates, so
   compute each one once and reuse it.

Rule of thumb: never guess where code is slow. Profile it, fix the top line, measure again.
And keep the old version around as a yardstick: `tests/test_speed.py` checks that the fast
code gives exactly the same numbers as the slow pandas helpers.

---

## 8o. "Is this move unusual?" — z-moves (round 31)

`moves.py` answers one question: **was today's move big *for this stock*?**
```python
sigma = r.iloc[-253:-1].std()     # typical daily move over the past year, NOT counting today
z = today_return / sigma          # 3.0 = three times a normal day
z_5d = ret_5d / (sigma * 5**0.5)  # multi-day moves grow with sqrt(days), not days
```
Why leave today out of `sigma`? A huge day would inflate its own yardstick and look
less unusual than it is. Why `sqrt(5)`? If daily moves are random, their spread over
5 days grows like the square root of 5, so a 5-day move needs that much more room.

`biggest_since` is a nice pandas pattern: filter the past to moves at least as big in
the same direction, then take the **last** date: `hit.index[-1]`.

Try it: in `tests/test_moves.py`, change the spike from `-0.08` to `-0.02` and predict
whether `z_1d < -5` still holds before you run it.

---

## 8p. Event studies: what happens after earnings? (round 32)

`earnings_moves.py` is a tiny **event study**, a tool finance researchers use all the time:
pick an event (a filing), line up the days right after it, and compare them with normal days.
```python
pos = index.searchsorted(filed, side="right")   # first trading day STRICTLY after the filing
ret = r.iloc[pos]                                # that day's return
sigma = r.iloc[pos-252:pos].std()                # volatility from the year BEFORE, so no peeking
ratio = mean(|reaction returns|) / mean(|normal-day returns|)
```
`searchsorted(..., side="right")` is the key trick. It finds where a date *would* slot into a
sorted index. With `side="right"`, a filing on a trading day lands on the NEXT day, and a
Saturday filing lands on Monday.

Try it: change `side="right"` to `side="left"` and run `pytest tests/test_earnings_moves.py`.
Which test catches it, and why does it matter?

---

## 8q. Position sizing: equal vs calmer-weighted (round 33)

`sizing.py` decides **how much** of each pick to buy:
```python
vol = px.loc[:d].tail(64).pct_change().std() * 252**0.5   # only prices up to the rebalance day
w = (1 / vol) / (1 / vol).sum()                            # calmer -> bigger weight, sums to 1
```
`.loc[:d]` is the no-look-ahead guard: slicing a date index up to `d` throws away
everything after it. `tests/test_sizing.py` proves it by making a stock go wild *after* `d`
and checking the weights don't change.

The same idea runs in two languages: `orders.calmer_weights` (Python, used by Streamlit)
and `calmerWeights` (JavaScript, used by the dashboard). A test runs both on the same
inputs and checks they agree. That's a cheap way to keep two copies of the same logic honest.

Try it: in the robustness table, compare "Inverse-vol weights" with the baseline. Is the
drawdown smaller? Is the CAGR lower? That trade-off is the whole story of risk-based sizing.

---

## 8r. Statistics: is it skill or luck? (round 34)

`confidence.py` is your STAT 2120 class in code. Take each quarter's **excess return**
(strategy − SPY) and ask whether its average is really above zero:
```python
t = mean / (sd / sqrt(n))              # how many standard errors above zero
p = stats.t.sf(t, n - 1)               # one-sided p-value
n_needed = (2 * sd / mean) ** 2        # solve t = 2 for n
```
The last line is just algebra on the first. It shows why a small edge in noisy returns
needs *years* of quarters to prove: halve the edge and you need 4x the data.

**Block bootstrap**: resample the quarters with replacement to see how much the average
could wobble. Blocks of 4 consecutive quarters keep good and bad streaks together, so the
range isn't falsely narrow. A fixed `seed` makes the result identical every run, and the
test checks that.

Big caveat, printed on the card: the backtest was designed *knowing* the past, so its
t-stat is optimistic. The paper portfolio's t-stat is the honest one.

Try it: in `tests/test_confidence.py`, work out by hand how many quarters a 0.5%/quarter
edge with 8% noise needs, then check it with `confidence.quarters_needed(0.005, 0.08)`.

---

## 8s. The best of many tries is biased: the Deflated Sharpe Ratio (round 35)

The robustness table tests ~21 variants. Even if none had skill, the *best* one would
look good. `confidence.deflated_sharpe` corrects for that:
```python
SR0 = sd(trial Sharpes) * ((1-γ)·Φ⁻¹(1 - 1/N) + γ·Φ⁻¹(1 - 1/(N·e)))   # luck bar for N tries
PSR = Φ( (SR - SR0) * sqrt(T-1) / sqrt(1 - skew·SR + (kurt-1)/4 · SR²) )
```
* `γ` is the Euler–Mascheroni constant (0.577…). This formula is the expected maximum of N
  normal draws, an extreme-value result you may meet in a probability class.
* The denominator widens for negative skew and fat tails (kurtosis > 3). Crash-prone returns
  make a Sharpe ratio less trustworthy.
* With N = 1 the luck bar is 0 and the DSR equals the plain Probabilistic Sharpe Ratio. A test
  checks exactly that.

Honest limit: we only count the variants we *wrote down*. Every idea tried and thrown away
before that (other factors, other weights) is also a "try", so the real haircut is bigger.

Try it: call `confidence.expected_max_sharpe(n, 0.04)` for n = 2, 10, 100, 1000. How fast
does the luck bar grow? (Hint: roughly like sqrt(2·ln n).)

---

## 8t. Config as data: `state/my_stocks.csv` (round 36)

Before, changing your stocks meant editing a Python list in `config.py`, where one missing
comma breaks everything. Now it's a CSV that anyone can edit on GitHub's website:
```
ticker,kind,note
NVDA,holding,core AI bet
AVGO,watch,
```
`mystocks.parse` follows one rule: **never crash on user input, explain instead.**
* `row[0].strip().upper().lstrip("$")` cleans " nvda " and "$NVDA" into "NVDA".
* A regex (`^[A-Z][A-Z0-9.\-]{0,9}$`) rejects things that can't be tickers.
* Duplicates are merged. Unknown kinds become "holding". Every fix is recorded in
  `problems` so the dashboard can show it.

A typo like "NVDAA" passes the regex, so it can't be caught until the price download
finds nothing. That's why `mystocks.unknown` checks the run's `FAILURES`. Some errors can
only be caught by trying.

Try it: add `TSM,watch,foundry` to the CSV, run `python run.py --demo`, and find TSM
on the dashboard. Then add `NOT A TICKER,watch,` and look for the banner.

---

## 8u. Reusing math: compare = "explain the change" between two stocks (round 37)

Round 26's `explain_change(z_before, z_after)` splits a score *change over time* into
per-factor pieces that add up exactly. Comparing two stocks is the same question, with
stock B as "before" and stock A as "after":
```python
def compare(rec_a, rec_b, factors):
    e = explain_change(rec_b["z"], rec_a["z"], weights)   # B -> A
    # e["drivers"] = per-factor gaps; they sum to score_A - score_B
```
No new formula, and the "sums exactly" guarantee comes for free. When you notice two
problems with the same shape, reuse the solution.

The dashboard runs the same logic in JavaScript (`compareStocks`). The code lives between
`// ---- compare` markers so `tests/test_compare.py` can cut it out, run it with node, and
check that both languages give identical gaps.

`#compare=NVDA,AMD` in the URL is "state in the hash". It's shareable, needs no server,
and `parseCompareHash` throws away anything it doesn't recognize.

Try it: open the dashboard with `#compare=MU,AAPL` and read the sentence. Then check
in Python: `explain.compare(MU_row, AAPL_row, config.FACTORS)["diff"]` should equal the
score difference.

---

## 8v. Tax lots: same trades, different bookkeeping (round 38)

`positions()` uses **average cost**: all your MU shares share one blended price.
The tax view uses **lots**: each buy is its own pile, and a sell takes from the
*oldest* pile first (FIFO, most brokers' default):
```python
def fifo_sell(lots, shares, price, date):
    for lot in lots:                 # oldest first
        take = min(lot["shares"], left)
        ...                          # gain = take * (price - lot price); term from lot's date
```
Both views always agree on **total** profit (realized + open). They only split it
differently between "already realized" and "still open". `tests/test_taxlots.py` checks that.

Dates are where bugs hide:
* Long-term means held *more than* one year, so a lot bought 2023-03-15 is long-term
  from **2024-03-16**, not the 15th.
* `pd.DateOffset(years=1)` turns 2024-02-29 into 2025-02-28, so leap-day lots go
  long-term on 2025-03-01. The JS version has to copy that exactly, and a test checks it.
* Wash-sale window: 30 days either side. Day 31 is fine. Tests cover both edges.

Not tax advice; your broker's 1099 is the official record.

---

## 8w. Remembering state: "since your last visit" (round 39)

The dashboard is a static page with no server and no login. So how does it know what you
saw last time? **localStorage**: a small key-value store your browser keeps for each site.
```js
const last = JSON.parse(localStorage.getItem('semiscope.snapshot') || 'null');
SINCE = diffSnapshots(last, makeSnapshot(D));
localStorage.setItem('semiscope.snapshot', JSON.stringify(makeSnapshot(D)));
```
Three things that make it robust:
1. **Snapshot, don't copy.** We store ~10 numbers, not the 360 KB data.json.
2. **Distrust stored data.** Anything in localStorage could be old, edited or garbage.
   `snapshotValid()` checks its shape, and a bad snapshot is treated as a first visit.
   `try/catch` covers private browsing, where storage can throw.
3. **Two bookmarks.** If you reload the same data, comparing to "what I just saved" would always
   say "nothing new". So we keep a `.base` snapshot (what you saw *before* this data arrived)
   and compare to that.

`since.py` is the same function in Python. `run.py` uses it with `state/prev_snapshot.json`
to put a "Since last run" line in the digest.

---

## 8x. Missing data is information (round 41)

Real data feeds have gaps. When one stock's latest price is missing, the old code quietly
dropped it from the rankings. That's the worst kind of bug, because nothing tells you
anything happened. The fix is to **count** the gap and decide what to do with it:
```python
def stale_days(s):                      # trailing NaNs = days since the last real price
    v = s.notna().to_numpy()
    return int(len(v) - 1 - np.flatnonzero(v)[-1])
```
* 1–3 days stale: keep the stock, use its last price, and show a "stale" pill.
* More than 3 days: drop it (it may be halted or delisted).
* Never compute "today's move" from a stale price; that would repeat yesterday's news.

A typo'd ticker has **no** prices ever, while a stale one **had** prices and stopped.
Same symptom today, different cause, different message.

Note: we did NOT forward-fill the price table (`px.ffill()`). That would hide the gap
entirely, and the "stale" signal would be lost.

---

## 8y. Building an index from parts (round 43)

How do you make a "Memory stocks" index? Average the members' **daily returns**, then
compound:
```python
r = px[members].pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0)
index = (1 + r).cumprod()
```
Why not just average the *prices*? A $900 stock would drown out a $30 one. Averaging
returns gives each stock an equal vote every day (equal weight, rebalanced daily).
`skipna=True` means a stock with a missing day just sits that day out.

**Relative strength** is the group's return minus SOXX's over the same window. **Breadth**
asks how many members are above their own 50-day average, which tells you whether the
move is broad or carried by one big name.

Try it: in a scratch file, call `groups.build(px, bench, config.UNIVERSE)` on demo data
and print each group's `rel_3m`. Then change the horizon in `HORIZONS` to 252 (1 year).
Does the leader change?

---

## 8z. Measure, then cut: shrinking data.json (round 44)

First measure where the bytes are (`len(json.dumps(v))` for each top-level key). Two things
dominated: per-stock details shown only when you tap a stock, and time series that repeated
every date once per line.

1. **Load lazily.** Things you might never look at go in a second file (`detail.json`),
   fetched on first need. The page works without it.
2. **Don't repeat yourself.** Change `{"strategy": [[date, v], ...], "SPY": [[date, v], ...]}`
   into `{"_d": [dates], "strategy": [v...], "SPY": [v...]}`. `slim.unpack` / `unpackPairs`
   rebuild the original exactly. A round-trip test proves nothing was lost: compression
   you can't undo is data loss.

The result is 43% smaller with zero features removed, and the rankings table renders
character-for-character the same. Speed claims need numbers: the test asserts the size
budget, and the CHANGELOG records the before/after timing.

---

## 8aa. Rehearse the real thing (round 45)

The demo never calls `load_live()`, so 44 rounds of tests had never touched the code that will
run on launch day. `tests/fixtures/live_sim.py` fixes that **without the internet** by faking
only the outermost layer:

- `yfinance` is replaced by a module whose `download()` returns the same shape Yahoo does
  (a `(field, ticker)` column MultiIndex, time-zone-aware dates, an all-NaN column for an
  unknown ticker). So `data_sources.prices()` and its retry loop still run for real.
- `data_sources._get_json` returns SEC-format JSON, so the ticker→CIK lookup and every
  XBRL parser run for real too.

The rule: **fake as little as possible, as far out as possible.** The deeper you patch, the
more real code you skip, and that skipped code is where launch-day bugs live. This rehearsal
found one at once: foreign filers only have 2 stats, so `MIN_FACTORS = 3` silently left ASML
and TSM unranked forever. The demo hid it because its fake ASML had SEC data.

---

## 8ab. Compare a stock with itself (round 46)

`valuation.py` asks "is MU cheap?" the way a cyclical investor would: not against Nvidia,
but against MU's own past. Three ideas carry the whole file:

1. **Percentile rank** (`percentile`): the share of past weeks with a lower P/S, ties
   counted half. 0 = cheapest it's been, 100 = priciest. No assumption that P/S is
   normally distributed, which it usually isn't.
2. **Point-in-time, again.** Each weekly P/S calls the same `sales_yield()` the score uses,
   so it only sees filings made by that week. Shares are in today's split units and prices
   are split-adjusted, so the units match across a split. `test_split_in_window…` proves it.
3. **Context, not a signal.** It isn't a factor. Adding a weight-0 factor would re-run
   ~260 weekly look-ups at every backtest date for something the score ignores.

Small trap worth remembering: Python's `round(12.5)` is 12 (banker's rounding), JavaScript's
`Math.round(12.5)` is 13. The mirrored `ordinal()` uses `floor(x + 0.5)` so both say "13th".

---

## 8ac. Averages hide bad years (round 48)

`steady.py` turns one daily equity curve into "what does a bad year look like?":

- **Rolling window**: `curve / curve.shift(252)` is every 1-year return at once, no loop.
  Subtract SPY's and you get the 1-year excess for every possible start date.
- **Tracking error** is just `std` of the daily excess × √252; the **information ratio** is
  the mean daily excess × 252 divided by that. It's a Sharpe ratio measured against SPY.
- **Guard the division.** If the strategy *is* SPY, tracking error is 0 and the IR is 0/0.
  The code returns `None` below a tiny threshold instead of a meaningless huge number
  (`test_identical_to_spy…`).

The lesson for live trading: a strategy with IR 0.9 still trailed SPY by 28 points in its
worst year. If you'd quit in that year, you'd never have collected the average.

---

## 8ad. Two languages, one answer: rounding halves (round 50)

The page (JavaScript) and the pipeline (Python) print the same numbers, and twice they
disagreed on **exact halves**:

| value | Python `f"{x:.1f}"` / `round()` | JavaScript `toFixed(1)` / `Math.round` |
|---|---|---|
| 0.25 | "0.2" (halves go to the even digit) | "0.3" (halves go up) |
| 12.5 | 12 | 13 |

Neither is wrong; they're different rules. When two languages must agree, pick one rule and
write it down in both: here, "halves up" (`math.floor(x + 0.5)`, or `Decimal(...).quantize(...,
ROUND_HALF_UP)` when you need it exact). The mirror tests in `tests/` run the JS in node and
compare the text character by character, which is how these were caught.

Other lessons from the same hunt: escape **every** string that started in a file a person can
edit (`hEsc`), check "as of when?" for every date you label (a Friday label on a Thursday
price leaked a day), and when a value can be missing, decide on purpose where it sorts.

---

## 8ae. Reuse before you download (round 51)

`earnings_cal.py` adds a whole new card without a single new data source. It joins two
things the pipeline already computed: `filings.build()` (the expected next filing date) and
`earnings_moves.build()` (how far the stock moved after its last 8 filings). Look for what
you already have before reaching for a new API: no new failure modes, nothing new to cache.

Two small habits worth copying:
- **Week buckets from Monday**: `monday = asof - weekday days`; "this week" is anything before
  `monday + 7`. Testing the edges (Sunday, Monday, today) is where calendar bugs hide.
- **Say what a number does NOT mean.** The band is size only. A stock that went up 6 of its
  last 8 earnings days is not "likely up" on the next one.

---

## 8af. Questions beat summaries (round 52)

`weekly.py` doesn't summarize the week; it asks you about it. Each generator looks for one
kind of interesting fact (a big rank move, a valuation extreme, the worst year, earnings
soon, group rotation) and turns it into a question with a hint and a link. Three design
choices make it robust:

1. **Pure function, data in, list out.** No files or network, so a test can feed it
   hand-made dicts and check every branch.
2. **Each generator may fail alone.** `questions()` wraps each one; odd data skips that
   question instead of crashing the run (the test feeds it `groups: [None]` on purpose).
3. **Copies are tested, not trusted.** weekly.html carries its own copy of `hEsc` and
   `unpackPairs`; `test_weekly.py` fails the moment one drifts from index.html.

Study tip: answer the question in writing *before* tapping "Open". Checking a guess
against the data teaches more than reading the answer.

---

## 8ag. Reuse a rule, but check its assumptions (round 55)

`rebalance.next_date()` reuses `backtest.rebalance_dates()` instead of writing a second
"first trading day of Mar/Jun/Sep/Dec" rule that could drift from the first. But that function
quietly assumes its calendar starts at the beginning of a month: it takes the FIRST day it
sees in each rebalance month. Handed a calendar starting Dec 16, it said "Dec 16". The year-end
test (`2026-12-15 → 2027-03-01`) caught it. Reusing code is right; reusing it without knowing
what it assumes is how bugs move between files.

Drift in one line: a pick's weight now = (its price now ÷ entry price) ÷ (sum of that for all
picks). Winners grow past 1/N, losers shrink, and a rebalance sells some winners to buy the
losers back up to equal. That is the "buy low, sell high" built into equal weighting.

---

## 8ah. One rule, one function (round 56)

Round 55 found that `rebalance_dates()` assumed its calendar started on the 1st. The fix
wasn't to patch the one caller that tripped over it, but to move the rule into one function,
`first_trading_days(index)`, that states its own assumption out loud: a day is a month's first
trading day if the trading day before it is in an earlier month. The very first day of the
data has no "day before", so it only counts if it's in the first week. Every caller now uses
it, so the backtest, the paper portfolio and the preview can't disagree.

**Start-date luck** is the same idea as the robustness grid, aimed at the calendar: change
nothing but *when* the backtest starts. If a headline only shows up from one start, it's the
calendar talking, not the strategy. Look at the spread, not the best dot.

---

## 8ai. Show your work (round 58)

A score you can't recompute is a score you have to trust. `walkthrough.py` takes today's #1
and redoes its score from scratch with only what's in `data.json`: raw stat → clip to the
universe's 5th-95th percentile → z-score → flip if lower is better → weighted average. The
universe numbers come from `factors.z_stats`, the **same** function the scorer calls, so there
is one definition of "z-score" in the codebase and the walkthrough can't quietly drift from it.
`tests/test_walkthrough.py` checks the rebuild against every ranked stock, not just #1. If a
future change to the scorer forgets to update `z_stats`, that test fails the same day.

Then do it yourself: practice exercise 21 is the same arithmetic in 10 lines of Python.

---

## 8aj. Measure the thing you assumed (round 59)

The strategy holds picks for 3 months because that's when new quarterly filings arrive. That's
a reason, not evidence. `decay.py` checks it: take each rebalance's picks and measure them
against the average stock after 1, 2, 3, 6, 9 and 12 months. In the demo the lead grows for a
few months, then flips negative by month 12. Holding a quarter and re-picking fits that shape.

Two details worth copying. First, **overlap**: picks made every 3 months and held for 12 share
most of their days with the next three sets, so 55 "observations" are really closer to 14
independent ones. The t-stat is divided by √(months ÷ 3) so long horizons don't look more
certain than they are. Second, **no lookahead**: the picks come from the backtest (scored with
data known that day), and `test_no_lookahead` crashes a stock's price *after* a 1-month window to
prove that window's result doesn't move.

---

## 8ak. Write it down (round 60)

The weekly review asks questions; the journal is where the answers go. `docs/journal.md` is
deliberately dumb: dated headings and plain text, no markdown rendering, so it's impossible
to break the page (everything is escaped) and easy to edit from a phone on GitHub. The parser
(`parseJournal` in weekly.html, between `journal:start`/`journal:end` markers) is tested from
Python through node, the same trick as the other JS mirrors.

Why bother? Writing one sentence about *why* you think a stat moved is what turns reading a
dashboard into learning from it. In three months, the journal is the record of what you
predicted and what happened.

---

## 8al. Count the bets, not the stocks (round 61)

Five picks sounds diversified. But semis stocks in the same group (Equipment, Memory, ...)
rise and fall together with the same part of the cycle, so five picks from two groups is
really about two bets. `concentration.py` asks two questions:

1. **Today:** how many picks share a group, and is that unusual? (vs every past rebalance)
2. **Always:** what if we *forbade* bunching? `capped_picks()` is the whole rule, 15 lines:
   walk down the ranking, skip a stock once its group is full, backfill if there aren't enough
   groups. The robustness grid backtests it. A small CAGR drop means the model's edge is
   picking good stocks *within* groups; a big drop would mean it mostly times which group to
   own, which is a different (and riskier) skill.

The new row goes at the END of the robustness list on purpose: tests and the dashboard refer
to rows by position (Baseline first), and appending can't shift anything that already exists.

---

## 8am. Reuse the math, write the headline (round 62)

`explain.py` (round 40-something) already splits any score change into exact per-stat pieces.
Round 62 needed "which stat moved MU?", and the tempting move was a fresh calculation. Instead
`score_moves.py` is 60 lines of *editing*: filter (|Δ| ≥ 0.15), sort, keep 5, and write one
honest sentence. The honesty rule: only say "mostly X" if X explains at least half the move
**in the same direction**. Otherwise say "spread out". A z-score is relative, so a stock can
move without anything about the company changing, just because the other 29 stocks did.

---

## 8an. The formula that survives missing data (round 63)

`w·Δz/W` is the formula everyone writes first, and it's right whenever the stock has the same
stats in both runs. The day a 10-Q adds a stat (or a data error removes one), W changes, and
the pieces stop adding up to the real change. Writing each run's share separately,
`w·z_now/W_now − w·z_prev/W_prev`, keeps the sum exact in every case. Exercise 23 has you hit
that wall on purpose: the second test case adds one stat and drops another.

---

## 8ao. One number hides two (round 64)

"Beat SOXX by 3% a year" could mean it rises more, or falls less, or both. Capture splits it.
The math is two `mean()`s and a division, but the *filter* is the lesson: look only at the
months the benchmark went up (`both[both["b"] > 0]`), then only the months it fell. Pandas
boolean masks make "the same calculation on a subset" one line. Compare SPY and SOXX: the
same strategy looks like a leveraged bet against SPY and a defensive one against SOXX. Which
benchmark you pick changes the story, so the card always shows both.

---

## 8ap. Ratio of averages ≠ average of ratios (round 65)

Two ways to "average the capture": divide each month (strategy ÷ benchmark) and average those
ratios, or average each side first and divide once. They sound the same and aren't. A month
when the benchmark moved +0.1% and the strategy +2% has a ratio of 20, and one such month
wrecks the per-month average. Dividing the averages weights each month by how much the
benchmark actually moved, which is what "share of the gains" means. Exercise 24's checker
detects the per-month version and tells you which one you wrote.

Also new: a **warning is a bug report from the future.** pandas warned that `concat` will stop
sorting date indexes. Passing `sort=True` says what we mean, so the result can't silently
change on an upgrade.

---

## 8aq. Treat warnings as bug reports (round 66)

A deprecation warning means: "this line works today and will mean something different
later." Tests still pass, so nobody reads it. Then a routine `pip install -U pandas` changes a
number on the dashboard, and the bug is months old by the time anyone notices.

Two lines in `pytest.ini` fix that for good. `filterwarnings = error::FutureWarning:(?!(pandas|numpy|...)\b)`
means "make it an error, unless the warning comes from inside a library." The `(?!...)` is a
*negative lookahead* regex: match any module name that does NOT start with those. We don't
control pandas' internals, but we do control how we call them.

---

## 8ar. Don't ship what the browser already has (round 67)

The underwater chart needs one line per curve: `value / running max − 1`. The weekly equity
curves are already in `data.json` for the backtest chart, so the browser computes it
(`underwaterPts`, 6 lines). Python keeps the part that needs daily precision (episode dates
and lengths). A node test feeds both versions the same numbers, gaps included, and checks
they agree.

The same round changed a test, honestly: the size budget measured a *ratio* that got worse
every time we added something small and efficient. The thing a phone cares about is bytes
over the wire, so that's now the limit (70 KB gzipped). When a test fails, first ask whether
it's measuring what you actually care about.

---

## 8as. A loop is fine when the state matters (round 68)

Most of this project avoids Python loops over prices: pandas does it faster in one line.
Drawdown episodes are the exception, because the answer depends on *state*: "am I currently
underwater, and since when?" Exercise 25 shows the standard pattern: one variable (`start`)
that is `None` while at a high and holds a position while underwater, plus one check after the
loop for an episode the data never closed. That last check is the line beginners forget, and
it's the episode you care about most, because it's the one happening now.

---

## 8at. Make the next step obvious (round 69)

25 exercises numbered in the order they were written isn't a course. `PLAN_ORDER` in
`practice/check.py` is the course: one Python list, and everything else (PLAN.md, `--next`,
`--plan`) follows it. The test that compares PLAN.md to that list is the same idea as the
Python/JS mirror tests elsewhere: two descriptions of one thing will drift apart unless
something checks that they agree.

---

## 8au. One backtest is one roll of the dice (round 70)

The 21.2% CAGR is what happened along ONE path: these quarters, in this order. `outcomes.py`
asks what the same quarters could have produced in a different order. Three choices matter:

- **Blocks, not single quarters.** Markets have streaks. Shuffling single quarters would break
  up 2022's run of bad quarters and make the worst cases look too mild. Blocks of 4 keep them.
- **Paired benchmark.** Each replay uses the same quarter numbers for the strategy and SPY, so
  "beat SPY" compares like with like instead of a lucky strategy draw against an unlucky SPY draw.
- **A fixed seed.** `np.random.default_rng(42)` gives the same "random" numbers every run, so the
  card doesn't flicker and the tests can check exact values.

The honest limit: a bootstrap can only reuse history. It can't produce a crash worse than the
worst stretch already in the data, so read the bad end of the range as "at least this bad".

---

## 8av. Build the menu from the page (round 71)

The jump chips aren't a hand-written list of card names: `buildJumpChips()` reads whatever
cards the tab has right now (skipping hidden ones) and makes a chip from each `<h2>`. Add a
card next month and it gets a chip with no extra code; hide one when its data is missing
and its chip disappears too. The rule that decides is a pure function, `chipItems()`, which
takes plain objects and returns plain objects. That's what makes it testable in node without
a browser. The DOM part around it just reads the page in and writes the buttons out.

---

## 8aw. When the tool lies to you (round 72)

While testing exercise 26, a "broken" version of a file kept passing. The file was right; the
*checker* ran a stale copy. Python caches compiled files in `__pycache__` and decides whether
a cache is fresh by the file's modification time (to the second) and size. Two saves in the
same second with the same size look identical. Students hit this when they fix one character
and re-run fast. `check.py` now compiles from the source text each time, which is a few
milliseconds slower and never stale.

The lesson that generalizes: when a test result makes no sense, check that you're running
the code you think you're running.

---

## 8ax. Distrust the input (round 73)

Every model downstream of the SEC data assumes the numbers are real. `sanity.py` sits between
"downloaded" and "scored" and asks one question per quarter: could this number possibly be
true? It only *drops* data that's impossible (negative revenue) or wildly out of line with the
company's own recent past (8×). Everything merely strange is flagged and kept, because a real
business can have a strange quarter, and silently deleting real data is its own kind of bug.

Two design details: (1) it compares each quarter only with quarters *before* it, the same
no-look-ahead rule as the backtest; (2) a clean company's data passes through as the exact
same Python objects, which is how we know the demo outputs can't change.

---

## 8ay. Test cases are designed, not collected (round 74)

Exercise 27 has only seven inputs, and each one exists to break one specific wrong answer.
`[10, 10, 10, 80, 10]` is exactly 8×, so it separates `>=` from `>`. `[100, 30, 100, 100, 700]`
is 7× the median but 8.5× the mean. `[100, 100, 100000, 100000, 100000, 100]` makes a version
that forgets what it dropped think the second 100,000 is normal. The test file proves the
design: it edits the correct solution into each mistake and checks the checker names it. A
test suite where no mutation fails is a suite that isn't testing anything.

---

## 8az. Onboarding is a feature (round 75)

The dashboard has ~40 cards. A first-time visitor (you, a friend, an interviewer you show
it to) needs to know which 5 matter and in what order. The tour is deliberately small:
the steps are *data* (`TOUR_STEPS`: a tab, a list of selectors to try, a title, a sentence),
and one function decides which steps can run (`visibleSteps`). Everything else is plumbing:
open the tab, outline the card, move focus, clean up. Splitting "what" (data) from "how"
(DOM code) is why adding a sixth stop later is one line, and why the logic is testable
without a browser.

Accessibility detail worth copying: a popup that grabs focus must give it back, and Tab must
not wander behind it (`aria-modal`, a keydown trap, restore `document.activeElement`).

---

## 8ba. Contrast is arithmetic (round 76)

"Is this grey readable?" has an exact answer: WCAG contrast = (L1 + 0.05) / (L2 + 0.05), where
L is relative luminance. Body text needs 4.5:1. The old muted grey was 4.24:1: invisible to the
eye, obvious to the formula. `inkOn()` in index.html uses the same formula live: for each
heat-map cell it computes the background and picks the text colour (near-black or white) with
the higher ratio, instead of a fixed "white above 55%" rule that failed on mid-tone cells.

The audit tool (axe-core) runs in the real browser at phone size, both themes, so it checks what
a user sees, not just the source. 674 → 0 in one round, without changing any numbers.

## 8bb. The same maths, twice (round 77)

`practice/ex28_readable_colours.py` asks you to write `luminance()`, `contrast()` and `best_ink()`
in Python. The answer has to match the JavaScript `_lum()` / `inkOn()` in index.html exactly: a
test cuts the JS out between `// ---- ink ----` and `// ---- end ink ----`, runs it in node on 22
colours, and compares every luminance (to 12 decimals) and every ink choice. Two languages, one
formula, one test keeping them honest.

The tricky colour is grey #777777 (luminance 0.184). Compared with pure black #000000 it picks
black text; compared with the dashboard's real dark ink #0b0b0b it picks white. Tiny details in
a spec change answers, which is why the checker has a hint for exactly that slip.

## 8bc. Last week's ranks, recomputed (round 78)

To say "MPWR climbed from #6 to #4 this week" you need last week's ranks. Instead of storing a
history file, `run.py` simply calls `factors.score()` again with `asof` set 5 trading days back
(`week_diff.week_ago`). Because the scorer never peeks past `asof`, that IS what the ranking
looked like then. Only `{ticker: rank}` goes into data.json, so it costs ~0.3 KB.

The diff itself is pure: `weekDiff(prev, cur, topN)` in index.html and `week_diff.diff()` in
Python take two `{ticker: rank}` dicts and return entered / left / up / down. Ties sort by the
new rank, then by name, so the output never depends on dict order. Small pure functions are
easy to test in two languages; the DOM code that draws the card stays dumb.

## 8bd. Sorting ties on purpose (round 79)

`practice/ex29_what_changed_this_week.py` is the Python half of §8bc as an exercise. The bit
that trips people up is ties: if A and B both climbed 3 places, which comes first? Python's
`sorted(..., key=lambda t: (-move, cur[t], t))` answers it: compare the first item of the tuple,
and only on a tie look at the next. Without a full tie-break the order would depend on how the
dict happened to be built, and the Python and JS versions could disagree on the same data.

## 8be. Streaks: walk backwards, stop at the first miss (round 80)

A streak is "how many in a row, counting back from today". The code is a loop over the history
reversed, adding 1 per snapshot in the top N and `break`-ing at the first one that isn't.
Missing data is a miss (a stock we couldn't rank that week didn't prove it was in the top).

Cost was the worry: four extra full re-scores. It came to about one second because
`factors.score()` memoizes by date, and the backtest had already scored many nearby dates.
Measure before assuming something is slow (see the round 30 profile notes at the end of CHANGELOG.md).

## 8bf. One source of truth, three readers (round 81)

"Who joined the top 5 this week" now shows up in three places: the Rankings card (JS
`weekDiff`), the weekly review's summary line, and one of its questions (Python). The Python
side never re-implements the diff: `weekly._week()` calls `week_diff.diff()` and
`week_diff.streaks()` and only turns the result into sentences. If the rule ever changes (say,
"top 8"), it changes in one Python function plus its tested JS twin, and every reader follows.

## 8bg. Test the story you just told (round 82)

Round 80 added "5+ wk in top 5" tags, which quietly suggest a streak is good. Round 82 checks it
against the backtest and finds no evidence (t −0.4). That's a normal and useful result: a
dashboard should not hint at an edge it can't show. Two details make the test honest:

* **The unit is the quarter, not the pick.** 290 picks sounds like a lot, but five picks from the
  same quarter share the same market. The t-test runs on 55 quarterly gaps instead.
* **No look-ahead in the labels.** "Stayer" is decided from the previous and current pick lists,
  both known on the day. `classify(quarters[:k])` must equal the first rows of the full run.

## 8bh. `zip(xs, xs[1:])`: each item with the one before (round 83)

Lots of finance code compares "this period" with "last period": returns, rank changes,
stayers vs new picks. `zip(quarters, quarters[1:])` gives the pairs `(q0, q1), (q1, q2), ...`
with no index arithmetic and no off-by-one: the first quarter never appears as "this" quarter,
which is exactly right when there's nothing before it to compare with. Exercise 30 practises
it, then builds a t-stat by hand so `confidence.t_test` stops being a black box.

## 8bi. A page with no JavaScript (round 84)

`docs/practice.html` is generated by Python (`check.html_page`) as finished HTML: no fetch, no
framework, nothing to load. The only "logic" in the browser is a `<progress>` element, which
screen readers already understand. Two habits worth copying: build the page from the same
data the CLI prints (`PLAN`, `SKILLS`, `progress()`), so the page and `--plan` always agree;
and pass every string through `html.escape`, even ones you wrote yourself, because one day
somebody will put a `<` in a skill description.

## 8bj. Don't commit noise (round 85)

A generated file that embeds today's date changes every day even when nothing real changed,
and a bot that commits it daily buries the commits that matter. `write_html` compares the new
page with the old one *with the date removed* (`_without_date`) and only writes when something
else differs. Same idea as `git diff --cached --quiet || git commit` in the workflow: only
commit a difference. The CI step also ends in `|| echo ...` because an unfinished exercise
should never look like a broken pipeline.

## 8bk. Docs that are tested (round 86)

Instructions rot: a file gets renamed, a message changes, and the guide quietly lies. START_HERE
quotes real `check.py` output, so `test_start_here.py` writes those exact answers into a temp
copy of exercise 1, runs `check.report()`, and compares with the text in the guide. It also
checks every file and link the guide mentions still exists. If someone changes the checker's
wording, the test fails and points at the paragraph to update.

## 8bl. Hints by recognising the mistake (round 87)

A message like "expected 0.38, got 0.024" is correct but useless to a beginner. The checker now
keeps a list of *wrong answers written as code* (`EARLY_SLIPS`): "daily vol, not annualized",
"drawdown with the wrong sign", and so on. It runs them on the same inputs and compares. If your
result equals one of them, you get that mistake's explanation. It's the same trick the tests use
to prove a test catches bugs (mutation testing), turned around to help the person writing the code.

## 8bm. A hint must never fire on a right answer (round 88)

Each slip is only useful if the checker's cases can tell it apart from the correct code.
`test_every_slip_differs_from_the_right_answer_somewhere` runs every slip against the solution on
the real cases and fails if any of them agree everywhere. That's what dropped "forgot to skip
the last month" from exercise 11: on these dates it happens to pick the same three stocks, so a
hint for it could have shown up on someone's correct answer, which is worse than no hint.

## 8bn. Level 3 is read from the real answer (round 89)

The strongest hint, "the first line of the answer", isn't typed in by hand: `_body_lines` parses
the solution file with Python's `ast` module, skips imports and docstrings, and takes the first
statement. So it can't drift from the solution. When the whole answer is a single line it cuts
before the middle method call (`.dropna() ...`). A test checks, for all 16 exercises, that no
hint ever contains the complete answer.

## 8bo. Test the words, not just the code (round 90)

The "look up" hints are prose, so they can quietly go wrong ("use .resample" when the answer
uses .groupby). `test_hint_ladder_texts_are_short_and_name_real_methods` pulls the method and
function names out of each hint with a regex and checks at least one really appears in that
exercise's solution. It's a cheap guard, not proof, but it catches the most likely mistake: a
hint copied from a neighbouring exercise.

## 8bp. One definition, many places (round 91)

The "?" explanations don't keep their own copy of what CAGR means. `learnDefs()` reads the
Learn tab's `<dl>` once and builds a `{term: definition}` map, so editing a Learn entry updates
the tile explanation too. The sentence with your numbers comes from `explainTile(term, def,
values)`: plain text in, plain text out, no page access, so a test can run it in node with made-up
numbers. Only the click handler touches the page, and it uses `textContent`, never `innerHTML`.

## 8bq. When the explanation exposes the definition (round 92)

Putting the Learn definition next to a real number is a good test of the definition. The t-stat
entry said "how confident we are the average IC isn't luck", which was wrong next to the
"Is the edge real?" tile, where the t-stat is about the edge over SPY. It now says what a t-stat
is in general. The test `test_tiles_use_learn_terms_that_exist` keeps the three pieces in sync: every
`explainTile` branch has a tile using it and a Learn entry with exactly that name.

## 8br. An honest link or none (round 93)

Linking every dashboard number to "the exercise that builds it" is tempting, but Beta, VaR and
Sharpe have no exercise yet, and pointing them at something nearby would teach the wrong idea.
So `TERM_EXERCISE` leaves them out, and the test checks the reverse too: each mapped exercise's
name or skill must actually mention the idea. Those gaps are a to-do list for future exercises.

## 8bs. Correlation is not beta (round 94)

Exercise 31's first hint is the most common confusion in market stats. Correlation (-1..1) says
how *closely* a stock follows the market; beta says how *far* it moves when it does:
beta = correlation × (stock volatility ÷ market volatility). A jumpy stock with correlation 0.5
can still have beta 1.3. The checker's cases also make sure you line returns up by date:
dropping missing days from each Series separately quietly pairs Monday's stock move with
Tuesday's market move, and the answer looks plausible but is wrong.

## 8bt. Why √252 and not 252 (round 95)

Returns add up over time, so a year of average daily return is about 252 × the daily average.
Bounces partly cancel out, so spread grows more slowly: the yearly standard deviation is
√252 ≈ 15.9 × the daily one (variances add, not standard deviations). Mixing those up is the
most common Sharpe bug, and it makes a strategy look 16× better or worse. Exercise 32 also
shows a nice property of effective bets: scaling all weights by 2 changes nothing, because the
weights appear on both the top and the bottom of the ratio.

## 8bu. The honest test, rebuilt by hand (round 96)

The paper portfolio is the one number on the dashboard that can't be overfitted: picks are
logged before the returns happen. Exercise 33 rebuilds it line by line, and the rules that make
it honest are the ones the hints check. Returns start the day *after* the pick (that day's close
was used to choose), weights drift between rebalances and the next trade pays for moving them
back, and a stock with no price that day counts as flat rather than quietly disappearing.

## 8bv. Refactoring with a safety net (round 97)

Splitting a 1,900-line file by hand invites typos, so it was done by a script that reads
`check.py` with Python's `ast` module and moves each definition, with its comments, into
`_cases.py` or `_hints.py`. It also writes the imports each new file needs from the names it
uses. The safety net was a "golden output" capture: everything the checker can print was
saved before the split and compared after. Same text, byte for byte, means same behaviour.
Re-exporting the moved names from `check` meant none of the 490 tests had to change.

## 8bw. One place to look things up (round 98)

Moving the dashboard's helpers into `docs/helpers.js` broke 19 test files at once, because each
one opened `index.html` itself. Instead of fixing 19 paths, they now all call
`tests/_jsblocks.page_source()` or `js_block(name)`, which know where the code lives. Next time
something moves, one function changes. The same idea as `check.py` re-exporting its names in
round 97: give callers a stable address and hide where things actually are.

---

## 8bx. Two runs a day (round 100)

The Action now runs twice on weekdays: shortly after the market opens and shortly after it closes. That sounds like
one line of config, but two things in the code treat a run as "a finished day":

1. **The paper portfolio is append-only.** If a morning run landed on the first trading day of a quarter, the price
   at 9:45am would become that day's entry price forever. So `run.market_still_open()` checks the clock in New York
   time, and while the day is unfinished we hand `paper.update` the prices *without* the last row (`px.iloc[:-1]`).
   The rebalance then happens in the after-close run, with the real close.
2. **"What changed since last run"** compares against `state/prev_snapshot.json`. If the morning run replaced it,
   the after-close run would compare today with today. So only after-close runs overwrite it.

Why are the cron times odd? GitHub schedules in UTC and ignores daylight saving. 14:45 UTC is 9:45am in winter and
10:45am in summer; 21:17 UTC is 4:17pm in winter and 5:17pm in summer. Both are after the open and after the close
all year. `tests/test_intraday.py` checks that for both seasons.

## 9. Try this (one per practice session)

**Graded versions** of the newest ideas live in `practice/` (`python practice/check.py 13`):
z-moves (§8o) → ex13, FIFO tax lots (§8v) → ex14, the t-test (§8r) → ex15, inverse-vol sizing
(§8q) → ex16, P/S vs its own history (§8ab) → ex17, faking the network for a test (§8aa) → ex18,
rolling 1-year excess (§8ac) → ex19, the alert-log dedupe (round 53) → ex20.
Do the exercise first, then read the matching module to compare.

1. **Add a stock.** Add `"LSCC": {"name": "Lattice", "group": "Analog/Power", "sec": True}`
   to `UNIVERSE` in `config.py`. Run `python run.py --demo` and find it in the output.
2. **Change how many you hold.** First note the "Hold top 8" robustness row printed by
   `python run.py --demo`. Then set `TOP_N = 8`, re-run, and check that the new *baseline*
   CAGR matches the number you noted. Why must they be equal?
3. **Turn a stat off.** Set the momentum `weight` to `0`. Which robustness row should now
   match the baseline? Predict first, then run it.
4. **Write your own mini-factor.** In a scratch file, load prices with
   `demo_data.generate(...)` and compute each stock's 12-month return with
   `px.iloc[-1] / px.iloc[-252] - 1`. Sort it with `.sort_values(ascending=False)`.
   Which stock is #1?
5. **Read a test, then break it on purpose.** In `factors.py`, change `<` to `<=` in
   `_known`. Run `python -m pytest tests -k lookahead`. Does it still pass? Think about why,
   then change it back. (Hint: it's about what happens on the filing day itself.)

6. **Group the cycle yourself.** In a scratch file, run `cycle.growth_history(...)` on demo data
   and print `df.groupby("q")["g"].median()`. Then try `.mean()`. Which one is less affected
   by one crazy company, and why does `cycle.py` use it?
7. **Change the sell rule.** Set `BUFFER_RANK = 7` in `config.py`, re-run the demo, and compare
   the "Sell rule" row's CAGR and turnover with the baseline. Write down what you expected *before*
   running it.

8. **Make your own fixture.** In `make_fixtures.py`, copy the `googl` block, give it a fourth
   share class, re-run the script, and update `test_share_classes_summed_and_split_adjusted`.

9. **Move the split.** Set `OOS_START = "2018-01-01"` in `config.py` and re-run the demo.
   Do the same stats still "hold up"? A result that depends on exactly where you cut is fragile.

Bonus: open `docs/data.json` in a browser or text editor. Everything the dashboard shows
comes from there.
