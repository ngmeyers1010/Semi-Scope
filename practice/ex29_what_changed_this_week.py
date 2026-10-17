"""
Exercise 29: what changed this week (mirrors week_diff.py and the Rankings tab card)

You get two dicts of {ticker: rank}: `prev` (5 trading days ago) and `cur` (today).
Rank 1 is the best, so a SMALLER number is better: #9 -> #4 is a climb of 5.

week_diff(prev, cur, top_n, n=3) -> dict, or None if prev or cur is empty/None

    {"entered": [...],  # in the top `top_n` now (rank <= top_n) but not before. Sorted by NEW rank.
     "left":    [...],  # in the top before but not now. Sorted by OLD rank.
     "up":      [...],  # biggest climbs (in both dicts, rank number went down). At most n.
     "down":    [...],  # biggest drops (rank number went up). At most n.
     "new":     [...]}  # tickers in cur but not in prev, sorted A-Z (plain strings)

Every item in entered/left/up/down is {"ticker": t, "from": prev rank, "to": cur rank},
with None when the ticker is missing from that dict. A ticker that's new this week has
no "from", so it can enter the top but it is NOT a climber.

up/down order: biggest move first; on a tie, the better (smaller) NEW rank first; still
tied, ticker A-Z. (A sort key can be a tuple: key=lambda t: (a, b, c).)

Run `python practice/check.py 29` to check your answer.
"""


def week_diff(prev, cur, top_n: int, n: int = 3):
    # HINT: if not prev or not cur: return None
    # HINT: in_top = lambda r: r is not None and r <= top_n      (prev.get(t) gives None if missing)
    # HINT: both = [t for t in cur if t in prev and prev[t] != cur[t]]
    # YOUR CODE HERE
    raise NotImplementedError
