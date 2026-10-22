# SemiScope: brief for any Claude working here

**Owner:** Nick, a beginner Python learner (UVA econ/math). Explain new ideas in plain words and keep
code readable for a learner.

## What this is
Repo: github.com/ngmeyers1010/Semi-Scope · live site: https://ngmeyers1010.github.io/Semi-Scope/

A semis/hardware stock site. The code ranks stocks, backtests the ranking, keeps a paper portfolio
and tracks Nick's real trades. A GitHub Action runs every weekday and publishes the dashboard in
`docs/` to GitHub Pages.

**Goal:** prove whether the code's picks beat SOXX/QQQ, quarter by quarter, after costs.
The plan doc is "Investing Tracker Website — Plan" in the Claude project "Code Practice".

## Layout
- `run.py`: the whole pipeline (`python run.py --demo` works offline)
- `config.py`: the universe, weights and settings
- `docs/`: the website (`index.html`, `helpers.js`, `weekly.html`, `practice.html`)
- `practice/`: 33 exercises; `python practice/check.py` grades them
- `tests/`: `python -m pytest tests -q`; browser smokes run via `python tests/run_smokes.py`
- `.github/workflows/update.yml`: the daily automation
- `~/Code/hardware-analysis`: Nick's earlier project, with the fundamentals score to merge in

## Rules
- Run `python -m pytest tests -q` before saying a change is done.
- `python run.py --demo` must still end with `Backtest CAGR 20.7%`, unless a change is meant to
  move it (say so).
- Add a CHANGELOG.md row for each change and a CODE_TOUR.md section for each new idea.
- Never publish dollar amounts or share counts from Nick's real trades; percentages only.
- Not financial advice. Keep the cost and hindsight-bias guards in place.
