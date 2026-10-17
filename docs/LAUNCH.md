# Launch day: your first real run

Everything so far has run on **made-up demo data**. This page is for the first run on
real SEC and Yahoo data. Plan on about 20 minutes, ideally on a computer.

## 1. Before you click anything

- [ ] All 8 steps on `setup.html` are ticked, or you've done README → *One-time setup*.
- [ ] The `SEC_USER_AGENT` secret looks like `SemiScope you@example.com` (a real email).
- [ ] `state/my_stocks.csv` lists your stocks, one per line: `NVDA,holding,` or `AVGO,watch,`.
- [ ] Optional: `state/my_trades.csv` has your real buys and sells. Blank is fine.

## 2. Start the run

GitHub → your repo → **Actions** → **Update SemiScope** → **Run workflow** → green button.
Refresh after about 10 seconds and a yellow dot appears. Tap it to watch.

## 3. What a healthy first run looks like

| Step | Normal time | Good sign |
|---|---|---|
| Run tests | 1–2 min (the quick tests) | `… passed, … deselected` (one or two "skipped" is fine) |
| Run pipeline | 5–12 min the first time (downloads every SEC file), 2–4 min after | ends with `Done → docs/data.json` and `Top 5 now: [...]` |
| Commit results | seconds | `Update data YYYY-MM-DD` |
| Run slow tests (after the data is saved) | 2–3 min | `… passed`. If this one fails, today's data is still saved; Run health shows a ⚠ note |
| Deploy | about 1 min | green check |

Then open your dashboard and check:

- [ ] The **"Demo data."** banner is gone and the date is the last trading day.
- [ ] One alert says *"Switched from demo to live data"*. That's expected: change alerts start
      with the next run.
- [ ] **Paper portfolio** says it opened today with 5 picks. Tracking starts on the next run.
- [ ] **How it works → Data health**: most stocks are "ok". ASML and TSM show
      *"No SEC quarterly data (foreign filer?)"*. That's normal: they're ranked on price only,
      shown as "≈#", and never picked.
- [ ] **How it works → Run health**: one green "ok" row.

The backtest numbers **will** differ from the demo (demo CAGR is 21.2%). The real number is the
one that counts, even if it's worse.

## 4. The 6 most likely problems

1. **"403 Forbidden" from sec.gov, or many "SEC download failed" under Data health.**
   The SEC rejects requests without a real contact. Fix the `SEC_USER_AGENT` secret, then re-run.
2. **"ABORT: no prices for N/30 stocks (Yahoo outage?)".** Yahoo is down or rate-limiting.
   Nothing gets overwritten. Wait an hour and re-run. If it keeps happening for a day,
   paste the error to Claude.
3. **A banner on My stocks saying "no prices at all. Probably a typo."**
   That's a typo in `my_stocks.csv` (e.g. `NVDAA`). Tap **Edit my stocks**, fix it, commit.
   The run itself still succeeded.
4. **"Permission denied" / 403 at the Commit step, or "Get Pages site failed" at Deploy.**
   Settings → Actions → General → *Read and write permissions*, and Settings → Pages →
   Source *GitHub Actions*. Then re-run.
5. **Data health shows "probably a units error, ignored" (or "impossible, ignored").** That's
   `sanity.py` catching a bad SEC number. That quarter is left out of the score and everything
   else still works. Nothing to fix unless it keeps happening for the same company after its
   next filing; then tell Claude the ticker.
6. **A stock shows a "stale 2d" pill, or Data health says "No new filing in N days".** The first means
   Yahoo skipped the latest day (usually fixed by the next run). The second means the company
   changed how it reports to the SEC. Its stats go stale, and it may drop to a price-only "≈#" rank.
   If it lasts more than a week, tell Claude the ticker.

Anything else: Actions → the red run → the red step → copy the last 30 lines → paste to Claude.

## 5. Reading the setup page after launch

`setup.html` ticks off each step as it detects it. After the first good run, every step should
be ticked and the bar full. If a step stays un-ticked, open it: the fix is written under it, and
*If it fails* at the bottom covers the common errors. After that, the dashboard's
**How it works → Run health** is the place to look: one row per run, green or red.

## Was this rehearsed?

Yes. `tests/fixtures/live_sim.py` runs the **live** code path twice on fake SEC and Yahoo data
with real-world problems built in: a typo ticker, a stale price, a stock split, foreign filers,
an SEC download error, a company missing from the SEC list, a 53-week fiscal year, a revenue
number filed 1,000× too big, and a Yahoo
timeout. It checks that everything above shows up the way it's described here. It runs
with the other tests on every update (`tests/test_live_sim.py`).
