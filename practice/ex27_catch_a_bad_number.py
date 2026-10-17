"""
Exercise 27: catch a bad number (mirrors sanity.py)

SEC data sometimes has a quarter reported in thousands instead of dollars: 1,000× too big.
One such number can make a stock look like it grew 100,000% and push it to #1. Write two
functions that find the positions (0, 1, 2, ...) of the quarters to throw away.

1) flag_jumps(values, jump=8.0, lookback=4) -> list of positions, smallest first

   Walk the values in order. For position i:
   * skip it if it's None/NaN or <= 0 (nonpositive() handles those)
   * look at the up-to-`lookback` positions BEFORE i (i-4 .. i-1), leaving out any you
     already dropped and any that are <= 0 or missing. Never look at later quarters:
     on the day this quarter was filed, the later ones didn't exist yet.
   * if there are at least 2 of them, take their MEDIAN (one outlier can't move a median)
   * drop i if value / median >= jump  or  value / median <= 1 / jump

2) nonpositive(values) -> positions where the value is <= 0 (revenue can't be zero or negative)

Normal chip-cycle swings (−60% over a year) never come close to 8× in one quarter.

Run `python practice/check.py 27` to check your answer.
"""


def flag_jumps(values, jump: float = 8.0, lookback: int = 4) -> list:
    # HINT: import statistics; statistics.median([...])
    # HINT: dropped = []; for i, x in enumerate(values): ...
    # YOUR CODE HERE
    raise NotImplementedError


def nonpositive(values) -> list:
    # YOUR CODE HERE
    raise NotImplementedError
