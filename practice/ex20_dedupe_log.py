"""
Exercise 20: an alert log without duplicates (mirrors alerts.merge_log)

The pipeline can run twice on the same prices date (a manual re-run after the scheduled
one). Each run produces that day's alerts. Write merge_log(old, new, date) -> list of dicts:

  * `old` is the existing log, NEWEST FIRST: [{"date": "2026-10-12", "text": "..."}, ...]
  * `new` is today's alerts: [{"text": "..."}, ...] (no "date" yet: add date=`date` to each)
  * if `old` already has entries for `date`, today's run REPLACES them (drop the old ones)
  * drop exact duplicate (date, text) pairs anywhere (keep the first one you see)
  * result is newest first: today's alerts, then the rest of `old` in its order
  * keep at most 40 entries

Run `python practice/check.py 20` to check your answer.

Why "replace the day" instead of "skip anything already seen"? If the second run of the day
has FEWER alerts (say a stock dropped back out of the top 5), skipping would keep the stale
alert from the first run forever. Replacing makes the log match what's true now.
"""


def merge_log(old: list, new: list, date: str) -> list:
    # HINT: rest = [a for a in old if a["date"] != date]
    # HINT: today = [dict(a, date=date) for a in new]
    # HINT: seen = set(); a tuple (date, text) can go in a set, a dict can't
    # YOUR CODE HERE
    raise NotImplementedError
