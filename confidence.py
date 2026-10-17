"""
"Is the edge real?" — could the strategy's lead over SPY just be luck?

We look at the strategy's EXCESS return over SPY each quarter and ask:
  * t-stat: average excess ÷ its standard error. Rule of thumb: |t| ≥ 2 is "probably not luck".
  * p-value: if the true edge were zero, how often would luck alone produce a result
    this good? (One-sided: we only care about beating SPY.)
  * bootstrap confidence interval: resample the quarters (in blocks of 4, so a good
    year stays together) thousands of times and see the range of average edges.
  * quarters needed: if the edge and its noise stay the same, how many quarters of
    data until t reaches 2?

Backtests are in-sample (the model was designed knowing the past), so even a strong
result here is weaker evidence than the same numbers from the live paper portfolio.
"""
from __future__ import annotations

import math

import numpy as np

T_TARGET = 2.0
BLOCK = 4          # quarters per bootstrap block (one year)
N_BOOT = 5000
SEED = 7


def _t_sf(t: float, df: int) -> float:
    """P(T > t) for a t distribution; normal approximation if scipy isn't installed."""
    try:
        from scipy import stats
        return float(stats.t.sf(t, df))
    except Exception:                                   # pragma: no cover - depends on env
        return 0.5 * math.erfc(t / math.sqrt(2))


def t_test(x) -> dict:
    """Mean, standard deviation, t-stat and one-sided p-value for 'mean > 0'."""
    x = np.asarray([v for v in x if v is not None and not np.isnan(v)], dtype=float)
    n = len(x)
    if n < 2:
        return {"n": n, "mean": float(x.mean()) if n else None, "sd": None, "t": None, "p": None}
    mean, sd = float(x.mean()), float(x.std(ddof=1))
    if sd <= 1e-12 * max(1.0, abs(mean)):         # identical every quarter (or float noise): t is undefined
        return {"n": n, "mean": mean, "sd": 0.0, "t": None, "p": None}
    else:
        t = mean / (sd / math.sqrt(n))
        p = _t_sf(t, n - 1)
    return {"n": n, "mean": mean, "sd": sd, "t": t, "p": p}


def block_bootstrap(x, n_boot: int = N_BOOT, block: int = BLOCK, seed: int = SEED) -> np.ndarray:
    """Means of `n_boot` resampled series built from random blocks of consecutive quarters."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return np.array([])
    block = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    k = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, size=(n_boot, k))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :n]
    return x[idx].mean(axis=1)


def quarters_needed(mean: float | None, sd: float | None, target: float = T_TARGET) -> int | None:
    """n such that mean / (sd / sqrt(n)) reaches `target`. None if the edge isn't positive."""
    if mean is None or sd is None or mean <= 0:
        return None
    if sd == 0:
        return 2
    return max(2, math.ceil((target * sd / mean) ** 2))


def verdict(t: float | None, n: int) -> str:
    if t is None or n < 8:
        return "Too early to tell"
    if t >= 3:
        return "Statistically strong"
    if t >= 2:
        return "Statistically strong (but check it out-of-sample)"
    if t > 0.5:
        return "Promising, not proven"
    if t > -0.5:
        return "No evidence of an edge"
    return "Evidence it's lagging"


def analyze(excess, label: str = "backtest") -> dict:
    """Full significance summary for a list of quarterly excess returns (strategy − SPY)."""
    x = [float(v) for v in excess if v is not None and not np.isnan(v)]
    tt = t_test(x)
    out = {"label": label, **tt, "verdict": verdict(tt["t"], tt["n"])}
    boots = block_bootstrap(x)
    if len(boots):
        lo, hi = np.percentile(boots, [5, 95])
        out["ci90_q"] = [float(lo), float(hi)]
        out["ci90_annual"] = [float((1 + lo) ** 4 - 1), float((1 + hi) ** 4 - 1)]
        out["prob_positive"] = float((boots > 0).mean())
    if tt["mean"] is not None:
        out["annual_mean"] = float((1 + tt["mean"]) ** 4 - 1)
    need = quarters_needed(tt["mean"], tt["sd"])
    out["quarters_needed"] = need
    out["more_quarters"] = None if need is None else max(0, need - tt["n"])
    out["explain"] = explain(out)
    return out


def explain(r: dict) -> str:
    """One plain-English paragraph."""
    if r["n"] < 2:
        return "Not enough quarters yet to judge."
    if r["t"] is None:
        return f"Every one of the {r['n']} quarters had the same excess return ({r['mean']:+.1%}), so there's no noise to test against."
    s = (f"Over {r['n']} quarters the strategy beat SPY by {r['mean']:+.1%} per quarter on average "
         f"(t = {r['t']:.1f}). ")
    if r.get("p") is not None:
        odds = "less than 1 time in 100" if r["p"] < 0.01 else f"about {r['p']:.0%} of the time"
        s += f"If there were no real edge, luck alone would produce a result this good {odds}. "
    if r.get("ci90_annual"):
        lo, hi = r["ci90_annual"]
        s += f"A 90% range for the yearly edge is {lo:+.0%} to {hi:+.0%}. "
    if r.get("more_quarters"):
        s += f"At this pace it would take about {r['more_quarters']} more quarters to reach t = 2."
    elif r.get("quarters_needed") is None:
        s += "With no positive average edge, more data won't make it significant."
    if r.get("label") == "backtest":
        s += (" Caution: this is a backtest of a model designed knowing the past, so it overstates the evidence."
              " The live paper portfolio is the real test.")
    return s.strip()


def build(backtest_quarters: list[dict], paper_excess: list[float] | None = None) -> dict:
    """{'backtest': {...}, 'paper': {...} or None}"""
    bt = [q["return"] - q["spy"] for q in backtest_quarters
          if q.get("return") is not None and q.get("spy") is not None and not np.isnan(q["spy"])]
    return {"backtest": analyze(bt, "backtest"),
            "paper": analyze(paper_excess, "paper") if paper_excess and len(paper_excess) >= 2 else None}


# ---------- Multiple testing: the Deflated Sharpe Ratio ----------
# Bailey & López de Prado (2014). If you try N versions of a strategy and keep the
# best, its Sharpe ratio is biased upward even if none of them has real skill.
# The DSR asks: "is our Sharpe higher than the best Sharpe we'd expect from N
# no-skill trials?", and adjusts for fat tails and skew in the returns.

EULER_GAMMA = 0.5772156649


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def norm_ppf(p: float) -> float:
    """Inverse normal CDF (scipy if present, else Acklam's rational approximation)."""
    if not 0 < p < 1:
        return -math.inf if p <= 0 else math.inf
    try:
        from scipy import stats
        return float(stats.norm.ppf(p))
    except Exception:                                   # pragma: no cover - depends on env
        a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
        b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
        d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
        q = min(p, 1 - p)
        if q < 0.02425:
            t = math.sqrt(-2 * math.log(q))
            x = (((((c[0]*t+c[1])*t+c[2])*t+c[3])*t+c[4])*t+c[5]) / ((((d[0]*t+d[1])*t+d[2])*t+d[3])*t+1)
        else:
            t = q - 0.5; r = t * t
            x = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*t / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
        return x if p == q else -x


def expected_max_sharpe(n_trials: int, var_sharpe: float) -> float:
    """SR0: the best Sharpe you'd expect from n_trials strategies with NO skill
    whose Sharpes vary with variance `var_sharpe`. Zero for a single trial."""
    if n_trials <= 1 or var_sharpe <= 0:
        return 0.0
    return math.sqrt(var_sharpe) * ((1 - EULER_GAMMA) * norm_ppf(1 - 1 / n_trials)
                                    + EULER_GAMMA * norm_ppf(1 - 1 / (n_trials * math.e)))


def psr(sr: float, sr_star: float, n_obs: int, skew: float, kurt: float) -> float | None:
    """Probabilistic Sharpe Ratio: P(true SR > sr_star). Per-period (not annualized) Sharpes;
    `kurt` is ordinary kurtosis (3 for a normal distribution)."""
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if n_obs < 2 or denom <= 0:
        return None
    return norm_cdf((sr - sr_star) * math.sqrt(n_obs - 1) / math.sqrt(denom))


def deflated_sharpe(returns, trial_sharpes_annual: list[float], periods: int = 252) -> dict | None:
    """DSR for the strategy's per-period `returns`, given the annualized Sharpes of all
    variants tried (including the strategy itself)."""
    r = np.asarray([v for v in returns if v is not None and not np.isnan(v)], dtype=float)
    if len(r) < 10 or r.std(ddof=1) == 0:
        return None
    sr = float(r.mean() / r.std(ddof=1))                      # per period
    z = (r - r.mean()) / r.std(ddof=0)
    skew, kurt = float((z ** 3).mean()), float((z ** 4).mean())
    trials = [s / math.sqrt(periods) for s in trial_sharpes_annual if s is not None and not np.isnan(s)]
    n = max(1, len(trials))
    var = float(np.var(trials, ddof=1)) if len(trials) > 1 else 0.0
    sr0 = expected_max_sharpe(n, var)
    dsr = psr(sr, sr0, len(r), skew, kurt)
    plain = psr(sr, 0.0, len(r), skew, kurt)
    out = {
        "n_trials": n, "sharpe": sr * math.sqrt(periods), "sr0": sr0 * math.sqrt(periods),
        "haircut_sharpe": (sr - sr0) * math.sqrt(periods),
        "dsr": dsr, "psr": plain, "skew": skew, "kurtosis": kurt, "n_obs": len(r),
    }
    out["explain"] = (
        f"We tried {n} versions of the strategy. Even with zero skill, the best of {n} would show a Sharpe of about "
        f"{out['sr0']:.2f} by luck, so the baseline's {out['sharpe']:.2f} gets haircut to {out['haircut_sharpe']:.2f}. "
        + (f"After adjusting for that, the chance its true Sharpe is above zero is "
           f"{'over 99%' if dsr > 0.99 else 'under 1%' if dsr < 0.01 else f'{dsr:.0%}'}. "
           if dsr is not None else "")
        + "Caveat: this only counts the variants in the robustness table, not the earlier choices "
          "of which stats to use, so the true haircut is bigger."
    )
    return out
