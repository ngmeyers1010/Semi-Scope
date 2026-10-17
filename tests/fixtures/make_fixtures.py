"""
Builds the small fake SEC "companyfacts" files in this folder. Each one copies a
real-world quirk seen in EDGAR data, so tests/test_fixtures.py can check the
parser handles it. Re-run with:  python tests/fixtures/make_fixtures.py

Format matches https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json:
facts -> taxonomy -> tag -> units -> USD/shares -> list of facts. Each fact has
start (flows only), end, val, accn (filing id), fy, fp, form, filed, and
sometimes "frame" (the SEC adds it to ONE copy of a repeated fact).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent


def f(start, end, val, form, filed, accn, frame=None):
    d = {"end": end, "val": val, "accn": accn, "form": form, "filed": filed}
    if start:
        d["start"] = start
    if frame:
        d["frame"] = frame
    return d


def doc(name, us_gaap, dei=None):
    facts = {"us-gaap": {t: {"units": {"USD": v}} for t, v in us_gaap.items()}}
    if dei is not None:
        facts["dei"] = {"EntityCommonStockSharesOutstanding": {"units": {"shares": dei}}}
    return {"cik": 0, "entityName": name, "facts": facts}


# 1) Apple-style: 52/53-week year ending late September. FY2023 is a 53-week
#    year with a 14-week Q1 (97 days). Q4 must be DERIVED (annual - Q1..Q3).
#    Quirks: frame duplicates, a 6-month YTD figure in the Q2 10-Q (must be
#    ignored), a later restated comparative, and a 10-K/A with a different annual.
aapl = doc("Fruit Co", {
    "RevenueFromContractWithCustomerExcludingAssessedTax": [
        f("2022-09-25", "2022-12-31", 117_000, "10-Q", "2023-02-03", "A1", "CY2022Q4"),
        f("2022-09-25", "2022-12-31", 117_000, "10-Q", "2023-02-03", "A1"),          # exact duplicate
        f("2023-01-01", "2023-04-01", 95_000, "10-Q", "2023-05-05", "A2", "CY2023Q1"),
        f("2022-09-25", "2023-04-01", 212_000, "10-Q", "2023-05-05", "A2"),          # 6-month YTD
        f("2023-04-02", "2023-07-01", 82_000, "10-Q", "2023-08-04", "A3", "CY2023Q2"),
        f("2022-09-25", "2023-09-30", 383_000, "10-K", "2023-11-03", "A4", "CY2023"),
        f("2022-09-25", "2023-09-30", 390_000, "10-K/A", "2024-01-15", "A5"),        # amendment: ignore
        f("2022-09-25", "2022-12-31", 116_000, "10-Q", "2024-02-02", "A6"),          # restated comparative
    ],
    "CostOfGoodsAndServicesSold": [
        f("2022-09-25", "2022-12-31", 66_000, "10-Q", "2023-02-03", "A1"),
        f("2023-01-01", "2023-04-01", 53_000, "10-Q", "2023-05-05", "A2"),
        f("2023-04-02", "2023-07-01", 46_000, "10-Q", "2023-08-04", "A3"),
        f("2022-09-25", "2023-09-30", 214_000, "10-K", "2023-11-03", "A4"),
    ],
    "InventoryNet": [
        f(None, "2022-12-31", 6_800, "10-Q", "2023-02-03", "A1"),
        f(None, "2023-04-01", 7_500, "10-Q", "2023-05-05", "A2"),
        f(None, "2023-07-01", 7_400, "10-Q", "2023-08-04", "A3"),
        f(None, "2023-09-30", 6_300, "10-K", "2023-11-03", "A4"),
    ],
    # cash flow is YEAR-TO-DATE: 3, 6, 9, 12 months sharing the FY start date
    "NetCashProvidedByUsedInOperatingActivities": [
        f("2022-09-25", "2022-12-31", 34_000, "10-Q", "2023-02-03", "A1"),
        f("2022-09-25", "2023-04-01", 62_000, "10-Q", "2023-05-05", "A2"),
        f("2022-09-25", "2023-07-01", 88_000, "10-Q", "2023-08-04", "A3"),
        f("2022-09-25", "2023-09-30", 110_000, "10-K", "2023-11-03", "A4"),
    ],
})

# 2) Nvidia-style: year ends late January, and revenue switches tag names
#    (SalesRevenueNet -> RevenueFromContract... after the 2018 accounting change).
#    The FY2019 10-K re-reports FY2018 under the new tag with a different value;
#    the ORIGINAL must win. Q4 must be derived for both years.
nvda_old = [
    f("2017-01-30", "2017-04-30", 1_937, "10-Q", "2017-05-23", "N1"),
    f("2017-05-01", "2017-07-30", 2_230, "10-Q", "2017-08-23", "N2"),
    f("2017-07-31", "2017-10-29", 2_636, "10-Q", "2017-11-21", "N3"),
    f("2017-01-30", "2018-01-28", 9_714, "10-K", "2018-02-28", "N4"),
]
nvda_new = [
    f("2018-01-29", "2018-04-29", 3_207, "10-Q", "2018-05-24", "N5"),
    f("2018-04-30", "2018-07-29", 3_123, "10-Q", "2018-08-23", "N6"),
    f("2018-07-30", "2018-10-28", 3_181, "10-Q", "2018-11-20", "N7"),
    f("2018-01-29", "2019-01-27", 11_716, "10-K", "2019-02-21", "N8"),
    f("2017-01-30", "2018-01-28", 9_700, "10-K", "2019-02-21", "N8"),           # restated comparative
]
nvda = doc("Graphics Co", {
    "SalesRevenueNet": nvda_old,
    "RevenueFromContractWithCustomerExcludingAssessedTax": nvda_new,
    "GrossProfit": [dict(x, val=round(x["val"] * 0.6)) for x in nvda_old + nvda_new[:4]],
})

# 3) Alphabet-style: three share classes on the cover page (same filing, same
#    date) that must be SUMMED; a 20-for-1 split later; no inventory at all;
#    a 10-Q/A that supplies revenue the original 10-Q left out.
googl = doc("Search Co", {
    "Revenues": [
        f("2021-01-01", "2021-03-31", 55_000, "10-Q", "2021-04-28", "G1"),
        f("2021-04-01", "2021-06-30", 62_000, "10-Q/A", "2021-09-15", "G2A"),  # only in the amendment
        f("2021-07-01", "2021-09-30", 65_000, "10-Q", "2021-10-27", "G3"),
    ],
}, dei=[
    f(None, "2021-04-20", 300, "10-Q", "2021-04-28", "G1"),
    f(None, "2021-04-20", 45, "10-Q", "2021-04-28", "G1"),
    f(None, "2021-04-20", 320, "10-Q", "2021-04-28", "G1"),
])

if __name__ == "__main__":
    for name, d in [("aapl_like", aapl), ("nvda_like", nvda), ("googl_like", googl)]:
        (HERE / f"{name}.json").write_text(json.dumps(d, indent=1))
        print("wrote", name)
