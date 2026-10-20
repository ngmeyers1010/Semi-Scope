# SemiScope

Semiconductor & hardware stock rankings built from SEC filings and prices, a
quarterly-rebalanced backtest, a factor report card, robustness tests, and a
**forward paper portfolio** that proves (or disproves) the model in real time.
Runs free on GitHub: an Action updates everything every weekday evening,
publishes a phone-friendly dashboard to GitHub Pages, and opens a GitHub issue
(→ phone notification) when something you care about changes.

> Research tool, not financial advice. The backtest is NOT proof — the paper record is.

**New to Python?** Start with [docs/START_HERE.md](docs/START_HERE.md): install, see the dashboard, and pass
your first exercise in about 30 minutes.

---

## Before you upload

On a computer, in this folder:
```bash
pip install -r requirements.txt
python check_setup.py        # ✓ list: files present (incl. hidden .github), email set, tests pass
```
Every line should show ✓. Once the site is live, open **`https://ngmeyers1010.github.io/Semi-Scope/setup.html`**:
it's a checklist that ticks off each setup step by itself and shows fixes for common errors.

## One-time setup (~15 min, easiest on a computer)

1. **GitHub account** — sign up at github.com if needed.
2. **New repository** → name `semiscope` → **Public** (Pages is free for public repos) → Create.
3. On the repo page click **"uploading an existing file"**, drag in *everything inside*
   this folder, and **Commit changes**.
   - The hidden `.github` folder matters (it holds the automation). On a Mac press
     `Cmd+Shift+.` in Finder to see it. If it won't upload: **Add file → Create new file**,
     name it `.github/workflows/update.yml`, paste the contents, commit.
4. **Settings → Pages →** Source: **GitHub Actions**.
5. **Settings → Secrets and variables → Actions → New repository secret**:
   name `SEC_USER_AGENT`, value `SemiScope your-email@example.com` (the SEC requires a contact).
6. **Settings → Actions → General → Workflow permissions →** "Read and write permissions" → Save.
7. **Actions tab** → enable workflows if asked → **Update SemiScope → Run workflow**.
   First run ≈ 5 min. When it's green, open `https://ngmeyers1010.github.io/Semi-Scope/`
   and add it to your phone's home screen.
8. **Phone alerts:** install the **GitHub mobile app**, sign in, and turn on notifications
   (Profile → Settings → Notifications → enable push for "Issues"). Make sure you're
   *watching* the repo (repo page → Watch → All Activity). Alerts arrive as new issues.

### Install on your phone (works like an app)

- **iPhone (Safari):** open your dashboard link → tap **Share** (□↑) → **Add to Home Screen** → Add.
- **Android (Chrome):** open the link → tap **⋮** → **Add to Home screen** (or **Install app**).

It gets the SemiScope icon, opens full-screen, and still works with no signal: you'll see the
last downloaded data with an "Offline" banner.

**First real run?** Follow [`docs/LAUNCH.md`](docs/LAUNCH.md): what to click, what a healthy run
looks like, and the 5 most likely problems with fixes.

If a run fails: Actions tab → click the red run → copy the error → paste it to Claude.
A failed download for one or two stocks does **not** fail the run — they're skipped and shown
under *How it works → Data health*. The run only stops (leaving yesterday's dashboard in place)
if more than half the stocks have no prices.

**What the daily run does, in order:** quick tests (~1 min; if any fail, nothing is published) →
pipeline → save the data → **slow tests** (~2 min of full rehearsals, run *after* the data is saved so
they can't hold it up; if one fails you still get the issue, and Run health shows a ⚠ note on that
day's otherwise-OK run) → alerts → deploy. Locally, `pytest tests` runs everything;
`pytest -m "not slow" tests` runs just the quick ones. Deprecation warnings from this project's own code fail the tests (`pytest.ini`), so a pandas upgrade can't quietly change a number.

**You'll hear about failures.** A failed run opens a GitHub issue titled *"SemiScope update
failed"* (one issue, not one per day; it closes itself after the next good run), the dashboard
shows a red *"Data is N trading days old"* banner if prices fall more than 4 trading days behind,
and *How it works → Run health* lists the last 10 runs.

---

## What's on the dashboard

| Tab | What it shows |
|---|---|
| **Live paper portfolio** | **Next rebalance** preview (date, weight drift, what would change today and what it would cost); **Group concentration** (how many picks share an industry group, vs past picks, and what a max-2-per-group backtest shows); "This week" digest (incl. the **biggest score moves** since the last run and the stat behind each), then the real test: top-5 picks logged to git *before* returns happen, vs SPY / SOXX, with per-pick attribution. CSV download of the pick log. |
| *(Live paper portfolio, cont.)* | **Invest $X**: type an amount and see the shares the model's rules would buy today (fractional or whole), plus how your holdings line up with the picks. |
| **My stocks** | **Earnings coming up** (estimated report dates with each stock's typical earnings-day move and price band), where your holdings rank (MU, AMD, AAPL, ASML, NVDA + AMZN, GOOGL), signal, 8-quarter rank trend, and the alert log. |
| **Rankings** | Semis cycle gauge + group view, then all ~30 stocks with a factor heatmap. Tap a row for raw values, z-scores and revenue / margin / inventory / operating-margin history. **P/S vs own 5y** column (sortable): where today's price-to-sales sits in the stock's own 5-year range, with a gauge in the detail view (context only, not scored). **How did #1 get its score?**: the full arithmetic with real numbers, plus a pandas snippet that reproduces it. CSV download. |
| **Backtest** | Top-5 quarterly strategy since 2012 vs SPY, SOXX and an equal-weight basket; "Is the edge real?" (t-test, bootstrap, deflated Sharpe); **What could $1,000 become?** (the backtest replayed 5,000 times in random 1-year blocks: a range, not a forecast); **How long was it underwater?** (every drawdown: depth, months to recover, vs SOXX); **Up/down capture** (share of SPY's and SOXX's up and down months it catches); **"Is the edge steady?"** (rolling 1-year excess vs SPY, information ratio, tracking error, worst year); attribution (who made the money); every quarter's picks. |
| **Factor report card** | Which stats predict returns (IC, t-stat, hit rate, spread), model health over time, and robustness: 22 rule variants incl. sell-discipline, cost stress and a max-2-per-group cap, with turnover & cost drag; **start-date luck** (the baseline from 12 different starts); **signal decay** (how the picks do vs the average stock 1–12 months later, i.e. whether a 3-month hold fits). |
| **Learn** | Searchable plain-English meanings of every number on the site. |
| **Getting around on a phone** | A 5-stop tour on your first visit (again any time: How it works → Take the tour, or `#tour`). Long tabs start with a row of jump chips (one per card) plus Collapse all. Links like `index.html#tab=bt&card=dd-card` open a tab at a specific card; the weekly review uses them. |
| **Weekly review** (`weekly.html`) | The week on one screen for a study session: 3 data-driven questions to think about, top picks, your stocks, what changed, earnings soon, edge and steadiness, group leadership, and your last 3 **journal** entries (`docs/journal.md`: a `## YYYY-MM-DD` heading, then a few sentences on what you learned). Printable. |
| **How it works** | Factor list, data health (coverage, stale filings, odd values), honest caveats. |

## The stats

Scored (count toward the ranking) — weights in `config.py`:

| Stat | Weight | Idea |
|---|---|---|
| Revenue growth YoY | 1.0 | Demand strength |
| Revenue acceleration | 1.0 | Chip stocks turn when growth inflects |
| Gross-margin change YoY | 1.0 | Pricing power / utilization |
| Inventory-days change YoY | 1.0 (lower better) | Lean channel = healthy; inventory piling up = downturn warning |
| Operating-margin change YoY | 0.5 | Operating leverage in upswings |
| FCF margin (TTM) | 0.5 | Real cash per dollar of sales |
| Sales yield (TTM sales / mkt cap) | 1.0 | Valuation (inverse of P/S), split-safe |
| Price momentum (6-1 mo) | 1.0 | Trend persistence |
| Volatility (6 mo) | 0.5 (lower better) | Tie-breaker |

Informational (weight 0 — shown on the report card so you can test them before trusting them):
R&D intensity, capex intensity.

## How the data stays honest

- **Point-in-time:** every SEC number counts only from the date it was filed. Restatements are ignored; the originally reported value is used.
- **Q4 & cash flow:** Q4 = full year − Q1..Q3; cash-flow items are reported year-to-date, so they're de-cumulated into quarters.
- **Split-safe valuation:** SEC share counts are converted to split-adjusted units so a 10-for-1 split (e.g. NVDA 2024) doesn't make a stock look 10× cheaper.
- **Append-only paper log:** `state/paper_portfolio.json` is never edited; git history timestamps each pick.
- **Real-world SEC quirks** are covered by small fixture files in `tests/fixtures/` (53-week years, January fiscal years, revenue tag switches, amendments, multiple share classes).
- **Bad SEC numbers** (`sanity.py`) are caught before scoring: impossible values (negative revenue, a quarter 8× off its recent past, the classic thousands-vs-dollars mix-up) are dropped and listed in Data health; merely odd ones are flagged and kept.
- **What changed this week** (`week_diff.py`, Rankings tab): the universe is re-scored as of 5 trading days ago and only the ranks are kept, so the dashboard can list who entered/left the top 5 and the biggest climbs and drops; 10/15/20 days back are kept too, for the "N wk in top 5" streak pills.
- **Tests** (`tests/`) check no look-ahead, Q4/YTD math, split safety, watchlist isolation, robustness consistency, and alert logic. The Action runs them before every update.

## Files

| File | Job |
|---|---|
| `config.py` | Universe, watchlist, your holdings, factor weights, portfolio & buffer rules |
| `data_sources.py` | SEC EDGAR company facts + Yahoo prices/splits (cached) |
| `fundamentals.py` | Point-in-time quarterly series (revenue, COGS, inventory, op income, R&D, cash flow, capex, shares) |
| `factors.py` | Factor math, z-scores, composite score, watchlist scoring |
| `backtest.py` | Quarterly top-N backtest |
| `research.py` | Factor report card (IC, t-stat, spreads) |
| `robustness.py` | Rule-variant backtests, sell-discipline buffer, turnover & cost drag |
| `cycle.py` | Semis cycle phase, overall and per group |
| `attribution.py` | Contribution by stock / group (backtest and paper) |
| `data_health.py` | Coverage, staleness and odd-value checks |
| `paper.py` | Forward paper portfolio |
| `alerts.py` | Change detection (signal changes, big moves, model health) → `state/alerts.md` → GitHub issue |
| `digest.py` | "This week" summary → `state/digest.md` |
| `run.py` | Runs everything, writes `docs/data.json` |
| `moves.py` | Big price moves: z-moves (σ), 52-week highs/lows, "biggest since", move alerts |
| `earnings_moves.py` | How hard each stock moves after its filings vs a normal day; feeds the Invest $X heads-up |
| `sizing.py` | Equal vs inverse-volatility (calmer-weighted) position sizing, used by the backtest grid and Invest $X |
| `confidence.py` | "Is the edge real?": t-stat, p-value, bootstrap range, quarters needed, Deflated Sharpe (multiple-testing haircut) |
| `mystocks.py` | Reads `state/my_stocks.csv` (your holdings + watch list), validates it, reports problems |
| `since.py` | "Since your last visit / last run": compares two small snapshots (same logic as the dashboard JS) |
| `groups.py` | Sector rotation: group indices, relative strength vs SOXX, breadth, model's view by group |
| `slim.py` | Shrinks data.json for phones: moves per-stock details to detail.json, packs time series (lossless) |
| `risk.py` | Volatility, beta, VaR, correlation, effective bets, stress tests |
| `explain.py` | Why a score moved: exact per-factor contributions to the change; `compare`: why stock A scores above B |
| `quarterly.py` | Quarterly report cards (`reports/`), written once per finished quarter |
| `mytrades.py` | Your real trades: positions, P&L, vs SPY / model, quarterly returns, FIFO tax lots (short/long-term, wash-sale flags) |
| `docs/sw.js`, `docs/manifest.webmanifest`, `make_icons.py` | Installable phone app: offline cache, app info, icon drawing |
| `check_setup.py` / `docs/setup.html` | Pre-upload checker / self-updating setup checklist |
| `orders.py` | "Invest $X" math: shares per pick for a dollar amount; holdings vs picks |
| `runlog.py` | Logs every run (ok / failed / stocks skipped) to `docs/run_log.json` |
| `docs/index.html` | The dashboard |
| `.github/workflows/update.yml` | The daily automation |
| `CODE_TOUR.md` / `CHANGELOG.md` | Beginner code walkthrough / what changed each round |

## Customize

- **Your holdings:** edit `MY_HOLDINGS` in `config.py`. Non-chip stocks go in `WATCHLIST`.
- **Universe:** add/remove tickers in `UNIVERSE`.
- **Weights:** change a factor's `weight` (0 = informational only). Do it *before* a quarter
  starts, write down why, and judge it by the paper record — not by re-running the backtest
  until it looks good.

## Run locally (optional)

```bash
pip install -r requirements.txt
python -m pytest tests     # ~1 min
python run.py --demo       # fake data, no internet (~1 min)
python run.py --demo --fast  # reuse last run's robustness grid (much quicker)
python run.py --check      # real data: download + plain-English health report, writes nothing
python run.py              # real data
python -m http.server -d docs 8000   # open http://localhost:8000
```

## Quarterly report cards

When a quarter ends, the next daily update writes `reports/<year>Q<n>.md`, e.g. `reports/2027Q1.md`.
Each report covers:

- the model vs the S&P 500 and the semis ETF
- your real trades
- the picks held that quarter
- which stats worked
- how the chip cycle moved
- any alerts

It opens with a one-line verdict, like *"Model beat SPY by 3.1%; you trailed the model by 0.8%."*
Reports are written once and never changed, so they're an honest record. Read them on the
dashboard (**Live paper portfolio → Quarterly reports**), download them as `.md`, or open them
in the `reports/` folder on GitHub. Until the paper portfolio has a full quarter, reports show
backtest picks, clearly labeled.

## Track your real trades

The paper portfolio tests the *model*. To track *your* money, log each real trade:

1. On GitHub, open **`state/my_trades.csv`** and click the pencil icon (Edit).
2. Add one line per buy or sell:
   ```
   date,ticker,action,shares,price,note
   2026-10-16,MU,buy,3,112.40,first buy
   2026-11-20,MU,sell,1,125.00,trim
   ```
   Use the price you actually paid per share. Fractional shares are fine. Don't put commas
   inside numbers (`1000.50`, not `1,000.50`). Lines starting with `#` are ignored.
3. **Commit changes.** The next daily update shows it under **My stocks → My real money**:
   your value and P&L, the same dollars in SPY and in the model's picks on the same days, and
   each quarter's return.

How it's counted: average cost per share. Quarterly returns are *time-weighted*, so adding
money never shows up as a "gain". Stock splits after your trade are adjusted automatically.
Dividends are estimated automatically from price data and kept as cash (so the comparison
with SPY, which includes dividends, is fair). To use your broker's exact numbers, add lines like
`2026-11-14,TXN,dividend,1,4.08,Q4 dividend` (total cash in the price column) or
`2026-11-01,,fee,1,1.00,transfer fee`. Typos (a sell with no matching buy, an unknown ticker) show as
warnings on the card; they never break the update.

## Practice track

`practice/` has 33 self-checking exercises built on this project's data, from beginner
pandas up to a mini backtest, writing your own test, FIFO tax lots, a t-test, valuation
percentiles, testing with a fake download, rolling 1-year excess returns and a dedupe log:
```bash
python practice/check.py 1     # check exercise 1
python practice/check.py       # check all 33 (✓ / ✗ with what was expected vs what you got)
python practice/check.py --next  # progress bar + the next session in practice/PLAN.md (6 weeks)
python practice/check.py --html  # the same as a page: docs/practice.html (linked from Learn)
```
Everything runs offline on simulated data. See `practice/README.md` for the list. Solutions
are in `practice/solutions/`. Try first!

## Your own app (Streamlit)

`streamlit_app.py` is a second, much simpler front end written in **pure Python**. It
reads the same `docs/data.json`, and it's meant for learning: every line is commented,
with 7 practice exercises at the bottom. It has the rankings (with P/S vs its own 5 years
and "≈#" price-only ranks), a stock view, Group leadership, Invest $X, Compare, tax lots,
"Does it work?", "Is the edge steady?" and the launch checklist. To try another data file:
`SEMISCOPE_DATA=path/to/data.json streamlit run streamlit_app.py`.

**Run it on your computer**
```bash
pip install -r requirements-app.txt
python run.py --demo              # makes docs/data.json if you don't have one yet
streamlit run streamlit_app.py    # opens http://localhost:8501
```
Edit the file, save, and click **Rerun** in the browser to see your change.

**Put it online free:** go to share.streamlit.io → sign in with GitHub → **Create app** →
pick your `semiscope` repo, branch `main`, file `streamlit_app.py`. It redeploys every time
the daily Action commits new data. (The GitHub Pages dashboard keeps working either way.)

## Honest caveats

- **Survivorship bias:** the universe is today's companies; the backtest never held a chip stock that later collapsed. Real results will be worse.
- **Overfitting:** tuning until the backtest looks great makes it meaningless. Use the robustness table, the **out-of-sample check** (Factor report card tab: does each stat still work after 2020, on years it wasn't tuned on?), the **walk-forward** row (weights re-learned each quarter from past data only), and above all the paper record.
- **Foreign filers** (ASML, TSMC) file annually under IFRS, so they're scored on price factors only.
- 10 bps trading cost per side is included; taxes aren't.

### Checking the dashboard against messy data
`python tests/fixtures/make_sparse.py` turns the demo `data.json` into a "first live run" version (no paper
portfolio yet, a holding with no prices, a foreign stock with no SEC history, …).
`node tests/fixtures/sparse_smoke.mjs` then opens every tab in a headless browser and fails on any JS error; `tour_smoke.mjs` walks the first-visit tour. `a11y_smoke.mjs` runs the axe-core accessibility audit (WCAG 2.1 AA) on every tab in light and dark: `AXE=path/to/axe.min.js node tests/fixtures/a11y_smoke.mjs`.
