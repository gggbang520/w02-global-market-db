from datetime import date

from scripts.automation.backfill_historical_yahoo import (
    membership_allows,
    quarter_ranges,
)


def test_quarter_ranges_from_mid_quarter_start():
    got = quarter_ranges(date(2021, 1, 30), date(2021, 6, 30))
    assert got == [
        ("2021Q1", date(2021, 1, 30), date(2021, 3, 31)),
        ("2021Q2", date(2021, 4, 1), date(2021, 6, 30)),
    ]


def test_quarter_ranges_capped_at_end_date():
    got = quarter_ranges(date(2026, 7, 1), date(2026, 9, 27))
    assert got == [("2026Q3", date(2026, 7, 1), date(2026, 9, 27))]


def test_membership_allows_inclusive_interval():
    intervals = {
        ("XSHG", "600000"): [(date(2021, 1, 1), date(2021, 3, 31))]
    }
    assert membership_allows(intervals, "XSHG", "600000", date(2021, 1, 1))
    assert membership_allows(intervals, "XSHG", "600000", date(2021, 3, 31))
    assert not membership_allows(intervals, "XSHG", "600000", date(2021, 4, 1))
