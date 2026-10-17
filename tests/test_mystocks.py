"""state/my_stocks.csv: parsing, fallback, bad rows, duplicates."""
import mystocks as ms

UNIVERSE = {"NVDA": {}, "MU": {}, "AMD": {}}
DEF_H = ["MU", "AMZN"]
DEF_W = {"AMZN": {"name": "Amazon", "group": "Watchlist", "sec": True}}


def write(tmp_path, text):
    p = tmp_path / "my_stocks.csv"
    p.write_text(text)
    return p


def test_parses_and_cleans(tmp_path):
    p = write(tmp_path, "ticker,kind,note\n nvda ,holding,core AI bet\nMSFT,watch,cloud, AI\n$amd,,\n\n# comment line\n")
    r = ms.parse(p)
    assert r["holdings"] == ["NVDA", "AMD"]           # blank kind = holding, '$' and spaces stripped
    assert r["watch"] == ["MSFT"]
    assert r["notes"] == {"NVDA": "core AI bet", "MSFT": "cloud, AI"}
    assert r["problems"] == []


def test_missing_file_falls_back_to_defaults(tmp_path):
    parsed = ms.parse(tmp_path / "nope.csv")
    assert parsed is None
    h, w = ms.resolve(parsed, UNIVERSE, DEF_H, DEF_W)
    assert h == DEF_H and w == DEF_W


def test_bad_rows_reported_not_fatal(tmp_path):
    p = write(tmp_path, "ticker,kind,note\nNVDA,holding,\n12345,holding,\nTHIS IS BAD,watch,\nMU,maybe,\n")
    r = ms.parse(p)
    assert r["holdings"] == ["NVDA", "MU"]
    assert len(r["problems"]) == 3
    assert any("12345" in x for x in r["problems"]) and any("maybe" in x for x in r["problems"])


def test_duplicates_merged_holding_wins(tmp_path):
    p = write(tmp_path, "ticker,kind,note\nAVGO,watch,\nnvda,holding,\nAVGO,holding,\nNVDA,watch,\n")
    r = ms.parse(p)
    assert r["holdings"] == ["NVDA", "AVGO"] and r["watch"] == []
    assert sum("twice" in x for x in r["problems"]) == 2


def test_resolve_builds_watchlist_for_non_universe(tmp_path):
    p = write(tmp_path, "ticker,kind,note\nNVDA,holding,\nAMZN,holding,\nZZZZ,watch,\n")
    h, w = ms.resolve(ms.parse(p), UNIVERSE, DEF_H, DEF_W)
    assert h == ["NVDA", "AMZN"]
    assert list(w) == ["AMZN", "ZZZZ"]
    assert w["AMZN"]["name"] == "Amazon" and w["ZZZZ"]["group"] == "Watchlist"


def test_no_header_still_works(tmp_path):
    r = ms.parse(write(tmp_path, "NVDA,holding\nMU\n"))
    assert r["holdings"] == ["NVDA", "MU"] and r["problems"]


def test_unknown_from_failures():
    assert ms.unknown(["NVDA", "ZZZZ", "QQQQ"], {"ZZZZ": "price download failed",
                                                "QQQQ": "SEC download failed (X)"}) == ["ZZZZ"]


def test_shipped_file_matches_defaults():
    import config
    assert config.MY_STOCKS is not None and config.MY_STOCKS["problems"] == []
    assert config.MY_HOLDINGS == ["MU", "AMD", "AAPL", "ASML", "NVDA", "AMZN", "GOOGL"]
    assert list(config.WATCHLIST) == ["AMZN", "GOOGL"]      # so the demo is unchanged
