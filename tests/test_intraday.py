"""Two runs a day (open and close): the open run must not record anything for good, and the
schedule must land on the right side of the open and the close in both daylight-saving seasons."""
from pathlib import Path

import pandas as pd
import pytest

import run

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "update.yml"
MON = pd.Timestamp("2026-11-02")          # a Monday


@pytest.mark.parametrize("now, expected", [
    ("2026-11-02 09:45", True),            # just after the open
    ("2026-11-02 16:09", True),            # not yet 4:10pm
    ("2026-11-02 16:10", False),           # prices have settled
    ("2026-11-02 17:17", False),           # the after-close run
    ("2026-11-03 09:45", False),           # last bar is yesterday's: nothing unfinished
])
def test_market_still_open_new_york_clock(now, expected):
    assert run.market_still_open(MON, pd.Timestamp(now, tz="America/New_York")) is expected


def test_market_still_open_converts_utc():
    # 14:45 UTC is 9:45 in New York in winter: still open. 21:17 UTC is 4:17: closed.
    assert run.market_still_open(MON, pd.Timestamp("2026-11-02 14:45", tz="UTC")) is True
    assert run.market_still_open(MON, pd.Timestamp("2026-11-02 21:17", tz="UTC")) is False


def test_schedule_lands_right_in_summer_and_winter():
    yaml = pytest.importorskip("yaml")
    wf = yaml.safe_load(WF.read_text())
    crons = [c["cron"] for c in (wf.get("on") or wf.get(True))["schedule"]]
    assert len(crons) == 2
    times = sorted((int(c.split()[1]), int(c.split()[0])) for c in crons)      # (UTC hour, minute)
    (open_h, open_m), (close_h, close_m) = times
    for utc_offset in (4, 5):                                                  # EDT, EST
        open_et = (open_h - utc_offset) * 60 + open_m
        close_et = (close_h - utc_offset) * 60 + close_m
        assert 9 * 60 + 30 <= open_et < 11 * 60, utc_offset                    # after the open, before late morning
        assert close_et >= 16 * 60 + 10, utc_offset                            # after prices settle at the close


def test_only_fridays_after_close_run_is_a_full_refresh_and_alert_issue_is_shared():
    text = WF.read_text()
    assert '[ "$(date -u +%H)" -lt 18 ]' in text and 'FAST="--fast"' in text
    assert "gh issue comment" in text and "SemiScope alert" in text


def test_unfinished_rebalance_day_is_never_recorded(tmp_path, monkeypatch):
    """The paper log is append-only, so a half-finished day must not become an entry price."""
    import json
    import numpy as np
    import paper

    idx = pd.bdate_range("2025-11-03", "2026-12-01")           # last bar = Tue 2026-12-01, first trading day of December
    rng = np.random.default_rng(3)
    px = pd.DataFrame({f"T{i}": 100 * np.cumprod(1 + rng.normal(0.0005 * i, 0.02, len(idx))) for i in range(8)}, index=idx)
    tickers = list(px.columns)
    monkeypatch.setattr(paper, "STATE", tmp_path / "paper.json")

    def fresh_state():
        (tmp_path / "paper.json").write_text(json.dumps({"entries": [{
            "date": "2026-09-01", "reason": "inception", "picks": tickers[:5],
            "entry_prices": {}, "scores": {}, "recorded_at": "2026-09-01T22:00:00Z"}]}))

    fresh_state()
    _, new = paper.update({}, px.iloc[:-1], tickers)           # what the morning run passes in
    assert new == []                                            # the unfinished December 1st is not recorded

    fresh_state()
    _, new = paper.update({}, px, tickers)                      # what the after-close run passes in
    assert [d.strftime("%Y-%m-%d") for d in new] == ["2026-12-01"]
