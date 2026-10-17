# Start here

From zero to your first green ✓ in about 30 minutes. You only need a computer with Python 3.10+
and a terminal (the "Terminal" app on a Mac, "PowerShell" on Windows).

A **terminal command** is a line you type and press Enter. In this guide they're in grey boxes.
Run them from the `semiscope` folder (the one with `run.py` in it).

## 1. What's in the folder (only the parts you'll touch)

| Folder / file | What it is |
|---|---|
| `practice/` | 33 small exercises. You write a few lines in each; `check.py` grades them. |
| `docs/` | The website: `index.html` is the dashboard, `weekly.html` the weekly review, `practice.html` your progress. |
| `run.py` | The program that downloads data, ranks the stocks and writes `docs/data.json` for the website. |
| `config.py` | The settings: which stocks, how many to hold, how much each stat counts. |
| `tests/` | Automatic checks that the code still does what it should. You can ignore them at first. |

Everything else is the machinery behind the dashboard. [CODE_TOUR.md](../CODE_TOUR.md) explains it
when you're curious.

## 2. Install, then see the dashboard (10 minutes)

Install the libraries the code uses (**pandas** for tables, **numpy** for maths, and a few more):

```bash
pip install -r requirements.txt
```

Make the demo data. `--demo` uses simulated prices, so it works offline and needs no accounts:

```bash
python run.py --demo
```

It prints a few screens of progress and ends with a line like `Backtest CAGR 21.2%`
(**CAGR** = average yearly growth). Now start a tiny web server so your browser can open the site:

```bash
python -m http.server -d docs
```

Open <http://localhost:8000> in your browser. That's the dashboard. Press Ctrl+C in the
terminal to stop the server when you're done.

## 3. Your first exercise (15 minutes)

Open `practice/ex01_last_price.py` in any editor (VS Code is free). The goal is in plain English
at the top: return the most recent price of one stock. Check it before writing anything:

```bash
python practice/check.py 1
```

You'll see:

```
✗  1. last_price           not done yet (still raises NotImplementedError)

0/1 done.
```

That's normal: the file starts with `raise NotImplementedError`, a placeholder that means "not
written yet". Replace that line with your answer. A common first try is to take the first row:

```python
    return float(px[ticker].iloc[0])
```

Check again:

```
✗  1. last_price           for MU: expected 2543.588058, got nan
    Hint: that's the FIRST row, and it's empty (the stock wasn't trading yet). Drop missing values with .dropna(), then take the LAST one with .iloc[-1].

0/1 done.
```

**nan** means "not a number": a missing value. The checker recognised the mistake and says how
to fix it: `.dropna()` throws away the missing values and `.iloc[-1]` takes the last one.

```python
    return float(px[ticker].dropna().iloc[-1])
```

```
✓  1. last_price           correct!

1/1 done.  Nice work!
```

That's your first ✓. Stuck on a later one? Run `python practice/check.py 5 --hint` (any
number): each time you ask, the hint gets a bit stronger, up to the first line of the answer.
`practice/solutions/` has the full answers, but try for 20 minutes before you peek.

## 4. Where to go next

* **The study plan:** [practice/PLAN.md](../practice/PLAN.md) puts the 33 exercises in an order where
  each one builds on the last, with a warm-up question for each. `python practice/check.py --next`
  tells you which one is next.
* **Your progress page:** run `python practice/check.py --html`, then open
  [practice.html](practice.html) (it's also linked from the dashboard's Learn tab).
* **The words on the dashboard:** the **Learn** tab explains every term with a tiny example.
* **How the code works:** [CODE_TOUR.md](../CODE_TOUR.md), one short section per idea.
* **Putting it online** (free, updates itself every weekday): the setup steps in
  [README.md](../README.md).

A good rhythm for a 2-hour session: 10 minutes on the warm-up question, an hour on one exercise,
then open the dashboard card it "unlocks" and see the same idea working on real numbers.
