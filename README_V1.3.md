# W02 V1.3｜Official Historical Membership Evidence + Multi-Date Historical Price Expansion

## Final status

- Engineering: PASS
- Official primary historical membership: NOT_ESTABLISHED
- Secondary historical membership: 300/300
- Historical events: 104 records = 51 ADD + 51 REMOVE + 2 REBALANCE
- Historical price: 204 rows / 102 listings / 2 trade dates
- Minimum price expansion (100 listings × 10 dates): NOT_MET
- PIT: 204 rows = 202 IN_INDEX + 2 OUT_OF_INDEX + 0 UNKNOWN
- PIT VERIFIED: 0
- PIT PARTIAL: 204
- Canonical Current: unchanged, latest trade date 2026-09-24
- Weekly: NOT_DERIVED
- YTD: NOT_AVAILABLE
- License: REVIEW / INTERNAL_SNAPSHOT_ONLY
- pytest: 226 passed / 2 skipped

## Official evidence rule

Only a directly acquired CSI official document/attachment/dataset with acquisition metadata, SHA256, parsing and validation may be classified as OFFICIAL_PRIMARY historical membership evidence. V1.3 found official CSI methodology/rule documents, but did not establish a directly acquired 2020-12-14 or 2021-06-11 security-level historical attachment. Secondary reproductions remain separate.

## Price expansion rule

No fixture rows, copied dates, or duplicated prices were introduced. The existing real public GitHub/Tushare-derived archive remains the acquired price source. Because no additional verified real historical price file was acquired locally during V1.3, price expansion remains NOT_MET.

## Version

- data_version: DATA-2026-W39
- software_version: 1.3.0
- supersedes: 1.2.0
