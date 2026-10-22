"""
SemiScope configuration — edit this file to change the universe, factor weights,
and portfolio rules. Everything else reads from here.
"""

# Identifies you to the SEC (required by their fair-access policy).
# GitHub Actions reads this from the SEC_USER_AGENT secret if set.
SEC_USER_AGENT_DEFAULT = "SemiScope research ngmeyers524@gmail.com"

# ---------------------------------------------------------------------------
# Universe: US-listed semiconductor + hardware companies.
# "sec": True  -> files 10-Q/10-K with US-GAAP XBRL, so full fundamental factors.
# "sec": False -> foreign filer (20-F, IFRS, annual only): scored on price factors only.
# ---------------------------------------------------------------------------
UNIVERSE = {
    # Chips: compute / logic
    "NVDA": {"name": "Nvidia", "group": "Compute", "sec": True},
    "AMD":  {"name": "AMD", "group": "Compute", "sec": True},
    "INTC": {"name": "Intel", "group": "Compute", "sec": True},
    "AVGO": {"name": "Broadcom", "group": "Compute", "sec": True},
    "QCOM": {"name": "Qualcomm", "group": "Compute", "sec": True},
    "MRVL": {"name": "Marvell", "group": "Compute", "sec": True},
    # Memory & storage
    "MU":   {"name": "Micron", "group": "Memory/Storage", "sec": True},
    "WDC":  {"name": "Western Digital", "group": "Memory/Storage", "sec": True},
    "STX":  {"name": "Seagate", "group": "Memory/Storage", "sec": True},
    # Analog / power / RF
    "TXN":  {"name": "Texas Instruments", "group": "Analog/Power", "sec": True},
    "ADI":  {"name": "Analog Devices", "group": "Analog/Power", "sec": True},
    "MCHP": {"name": "Microchip", "group": "Analog/Power", "sec": True},
    "NXPI": {"name": "NXP", "group": "Analog/Power", "sec": True},
    "ON":   {"name": "onsemi", "group": "Analog/Power", "sec": True},
    "MPWR": {"name": "Monolithic Power", "group": "Analog/Power", "sec": True},
    "SWKS": {"name": "Skyworks", "group": "Analog/Power", "sec": True},
    # Semi equipment & materials
    "AMAT": {"name": "Applied Materials", "group": "Equipment", "sec": True},
    "LRCX": {"name": "Lam Research", "group": "Equipment", "sec": True},
    "KLAC": {"name": "KLA", "group": "Equipment", "sec": True},
    "TER":  {"name": "Teradyne", "group": "Equipment", "sec": True},
    "ENTG": {"name": "Entegris", "group": "Equipment", "sec": True},
    "ASML": {"name": "ASML", "group": "Equipment", "sec": False},
    # Foundry
    "TSM":  {"name": "TSMC", "group": "Foundry", "sec": False},
    # Systems / hardware
    "AAPL": {"name": "Apple", "group": "Systems", "sec": True},
    "ANET": {"name": "Arista", "group": "Systems", "sec": True},
    "DELL": {"name": "Dell", "group": "Systems", "sec": True},
    "HPQ":  {"name": "HP Inc", "group": "Systems", "sec": True},
    "SMCI": {"name": "Super Micro", "group": "Systems", "sec": True},
    "COHR": {"name": "Coherent", "group": "Systems", "sec": True},
}

# Your actual holdings — highlighted on the dashboard. Tickers outside the
# semis universe (WATCHLIST) are scored on the same yardstick but never picked.
MY_HOLDINGS = ["MU", "AMD", "AAPL", "ASML", "NVDA", "AMZN", "GOOGL"]
WATCHLIST = {
    "AMZN":  {"name": "Amazon", "group": "Watchlist", "sec": True},
    "GOOGL": {"name": "Alphabet", "group": "Watchlist", "sec": True},
}

# Your list lives in state/my_stocks.csv (edit it on GitHub, no Python needed).
# The two lists above are only the fallback if that file is missing.
KNOWN_NAMES = {
    "MSFT": {"name": "Microsoft", "group": "Watchlist", "sec": True},
    "META": {"name": "Meta", "group": "Watchlist", "sec": True},
    "TSLA": {"name": "Tesla", "group": "Watchlist", "sec": True},
    "ORCL": {"name": "Oracle", "group": "Watchlist", "sec": True},
}
import mystocks as _mystocks  # noqa: E402  (needs UNIVERSE above)
MY_STOCKS = _mystocks.parse()
MY_HOLDINGS, WATCHLIST = _mystocks.resolve(MY_STOCKS, UNIVERSE, MY_HOLDINGS, WATCHLIST, KNOWN_NAMES)

BENCHMARKS = {"SPY": "S&P 500", "SOXX": "Semis ETF"}

# ---------------------------------------------------------------------------
# Factors. weight = importance in the composite score; sign = +1 if higher is
# better, -1 if lower is better. Set a weight to 0 to switch a factor off.
# ---------------------------------------------------------------------------
FACTORS = {
    "rev_growth":    {"weight": 1.0, "sign": +1, "label": "Revenue growth YoY",
                      "why": "Demand strength this quarter vs. a year ago."},
    "rev_accel":     {"weight": 1.0, "sign": +1, "label": "Revenue acceleration",
                      "why": "Change in YoY growth vs. last quarter — semis stocks tend to turn when growth inflects."},
    "gm_change":     {"weight": 1.0, "sign": +1, "label": "Gross-margin change YoY",
                      "why": "Rising margins = pricing power / better utilization (cycle upswing)."},
    "inv_days_change": {"weight": 1.0, "sign": -1, "label": "Inventory-days change YoY",
                      "why": "Falling days of inventory = channel is lean; a rising pile is the classic downturn warning."},
    "op_margin_change": {"weight": 0.5, "sign": +1, "label": "Operating-margin change YoY",
                      "why": "Operating leverage: in an upswing, fixed costs get spread over more sales and margins jump."},
    "fcf_margin":    {"weight": 0.5, "sign": +1, "label": "FCF margin (TTM)",
                      "why": "Free cash flow (operating cash flow minus capex) per dollar of sales — real cash, not accounting profit."},
    "rd_intensity":  {"weight": 0.0, "sign": +1, "label": "R&D intensity (TTM)",
                      "why": "R&D spend / sales. Informational only (weight 0) — shown in the report card so you can see if it predicts anything before trusting it."},
    "capex_intensity": {"weight": 0.0, "sign": -1, "label": "Capex intensity (TTM)",
                      "why": "Capex / sales. Informational only (weight 0). Heavy capex late in a cycle often precedes oversupply."},
    "sales_yield":   {"weight": 1.0, "sign": +1, "label": "Sales yield (TTM sales / mkt cap)",
                      "why": "Inverse of price-to-sales: how much revenue you buy per dollar. Higher = cheaper. Split-safe (uses SEC share counts in split-adjusted units)."},
    "momentum":      {"weight": 1.0, "sign": +1, "label": "Price momentum (6-1 mo)",
                      "why": "6-month return skipping the latest month; trend persistence."},
    "low_vol":       {"weight": 0.5, "sign": -1, "label": "Volatility (6 mo)",
                      "why": "Annualized daily volatility; lower is preferred as a mild tie-breaker."},
}

# ---------------------------------------------------------------------------
# Portfolio rules
# ---------------------------------------------------------------------------
TOP_N = 5                        # stocks held each quarter, equal weight
REBALANCE_MONTHS = [3, 6, 9, 12] # rebalance on first trading day of these months
                                 # (gives filings ~30-60 days after quarter end)
BUFFER_RANK = 10                 # robustness "sell rule": keep a holding while it ranks in the top 10
COST_BPS = 10                    # trading cost per side, basis points
BACKTEST_START = "2012-03-01"    # XBRL data is reliable from ~2011
MIN_FACTORS = 3                  # a stock needs at least this many factors to be ranked
MOVE_ALERT_Z = 2.5              # alert when a holding's daily move is this many of ITS OWN typical moves
OOS_START = "2020-01-01"         # out-of-sample check: weights judged on data before vs after this date
WALK_FORWARD_YEARS = 3           # walk-forward variant: weight factors by their trailing N-year IC

# Paper portfolio: forward, out-of-sample tracking starts at the first
# rebalance date on/after this date. Backtest results are NOT proof;
# the paper record is.
PAPER_START = "2026-10-15"
