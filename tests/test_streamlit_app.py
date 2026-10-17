"""Smoke tests for the Streamlit app's data helpers (no browser needed)."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit_app as app  # noqa: E402

DATA_FILE = Path(__file__).resolve().parents[1] / "docs" / "data.json"
pytestmark = pytest.mark.skipif(not DATA_FILE.exists(), reason="run `python run.py --demo` first")


def test_helpers_shape_the_data():
    data = app.load_data()
    t = app.rankings_table(data)
    assert t["score"].dropna().is_monotonic_decreasing   # unscored stocks (NaN) go last
    rec = app.stock(data, t["ticker"].iloc[0])
    h = app.history_table(rec)
    assert list(h.columns) == ["Revenue ($bn)", "Gross margin (%)"]
    z = app.factor_z(rec, data["factors"])
    assert len(z) >= 3 and "rd_intensity" not in z   # weight-0 factors left out
    curves, label = app.performance_curves(data)
    assert set(curves.columns) == {"Top-5 strategy", "S&P 500 (SPY)"}
    assert curves.dropna().iloc[0].round(6).tolist() == [1.0, 1.0]   # both start at 1.0


def test_watchlist_and_foreign_filer():
    data = app.load_data()
    assert app.stock(data, "GOOGL")["ticker"] == "GOOGL"     # watchlist stocks are pickable
    no_sec = {"rank": 1, "history": [], "z": {}}
    assert app.history_table(no_sec).empty


def test_factor_bars_match_score_direction():
    """Weighted average of the bars must equal the stock's score (same sign convention)."""
    data = app.load_data()
    rec = app.rankings_table(data).iloc[0]
    rec = app.stock(data, rec["ticker"])
    z = app.factor_z(rec, data["factors"])
    w = {f: data["factors"][f]["weight"] for f in z.index}
    approx = sum(z[f] * w[f] for f in z.index) / sum(w.values())
    assert abs(approx - rec["score"]) < 1e-3


def test_order_table():
    data = app.load_data()
    t = app.order_table(data, 1000, fractional=False)
    assert len(t) == data["top_n"] and t["cost"].sum() <= 1000


def test_compare_helpers():
    import json
    from pathlib import Path
    import streamlit_app as app
    p = Path(__file__).parents[1] / "docs" / "data.json"
    if not p.exists():
        import pytest; pytest.skip("run python run.py --demo first")
    data = app.load_data(p)
    if "px_1y" not in data["rankings"][0]:
        import pytest; pytest.skip("data.json predates round 37")
    t = [r["ticker"] for r in data["rankings"][:3]]
    tab = app.compare_table(data, t)
    assert list(tab.columns) == t and len(tab) == sum(c["weight"] > 0 for c in data["factors"].values())
    px = app.compare_prices(data, t)
    assert (px.iloc[0] == 100).all()


# ---------- rounds 43-48 in the Streamlit app ----------
def test_new_helpers_on_full_data():
    data = app.load_data()
    t = app.rankings_table(data)
    assert "ps_pct" in t.columns and t["rank"].iloc[0].startswith("#")
    g = app.groups_table(data)
    assert list(g.columns)[:2] == ["Group", "1m vs SOXX"] and len(g) >= 3
    assert app.diverging_color(0.2).startswith("background-color: rgba(42") and app.diverging_color(None) == ""
    rec = app.stock(data, t["ticker"].iloc[0])
    v = app.valuation_view(rec)
    assert v is None or "percentile" in v["text"] or "needs 2 years" in v["text"]
    sv = app.steady_view(data)
    assert sv is not None and len(sv["metrics"]) == 4 and len(sv["series"]) > 50
    assert "LAUNCH" in app.launch_text().upper() or "first real run" in app.launch_text()


def test_rank_label_price_only_and_watchlist():
    assert app.rank_label({"rank": 3}) == "#3"
    assert app.rank_label({"rank": None, "would_rank": 7}) == "≈#7 (price only)"
    assert app.rank_label({"rank": None, "would_rank": 9}, in_universe=False) == "≈#9"
    assert app.rank_label({"rank": None}) == "—"


def test_helpers_handle_old_or_sparse_data():
    data = {"rankings": [{"ticker": "A", "rank": 1, "name": "A", "group": "G", "score": 1.0,
                          "ret_3m": None, "gross_margin": None}], "watchlist": []}
    assert app.groups_table(data).empty and app.steady_view(data) is None
    assert app.steady_view({"steady": {"backtest": {"available": False, "reason": "x"}, "paper": None}}) is None
    assert app.valuation_view({"ticker": "A"}) is None
    assert app.valuation_view({"valuation": {"ps": 2.0, "pct": None}})["frac"] is None
    assert app.rankings_table(data)["ps_pct"].isna().all()


@pytest.mark.parametrize("which", ["full", "sparse"])
def test_app_runs_end_to_end(which, tmp_path, monkeypatch):
    """Run the real page with Streamlit's test runner, on the demo data and on a sparse
    'first live run' file, and check the new sections appear without any exception."""
    testing = pytest.importorskip("streamlit.testing.v1")
    import shutil
    import subprocess
    root = Path(__file__).resolve().parents[1]
    if which == "sparse":
        subprocess.run([sys.executable, str(root / "tests" / "fixtures" / "make_sparse.py")], check=True,
                       capture_output=True)
        src = root / "tests" / "fixtures" / "sparse_data.json"
        shutil.copy(src, tmp_path / "data.json")          # no detail.json next to it: also tested
        src.unlink()
        monkeypatch.setenv("SEMISCOPE_DATA", str(tmp_path / "data.json"))
    else:
        monkeypatch.delenv("SEMISCOPE_DATA", raising=False)
    at = testing.AppTest.from_file(str(root / "streamlit_app.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    heads = [h.value for h in at.subheader]
    assert "Is the edge steady?" in heads and "Does it work?" in heads
    if which == "full":
        assert "Group leadership" in heads
        assert any("Launch day" in e.label for e in at.expander)


def test_earnings_table_helper():
    data = app.load_data()
    t = app.earnings_table(data)
    assert t.empty or list(t.columns)[:3] == ["week", "date", "ticker"]
    assert app.earnings_table({}).empty and app.earnings_table({"earnings_cal": {"rows": []}}).empty
    one = app.earnings_table({"earnings_cal": {"rows": [{"week": "Later", "date": "2026-11-04", "ticker": "MU",
            "days": 22, "move": None, "band": None, "ups": None, "n": None}]}})
    assert one.iloc[0]["band"] == "" and one.iloc[0]["up / last"] == "—"
