# W02 V1.1｜CSI300 Historical Event + Multi-Date Price Expansion

## Status

- Engineering: PASS
- Historical membership: SECONDARY established, OFFICIAL not established
- Membership event ledger: PARTIAL
- Historical price expansion: NOT_MET
- Point-in-Time: PARTIAL
- Canonical Current: unchanged
- pytest: 142 passed, 2 skipped

## Real data

Existing real batch retained unchanged:

- source_id: `SRC-GITHUB-TUSHARE-ARCHIVE`
- rows: 204
- listings: 102
- trade dates: 2
- dates: 2021-01-28, 2021-01-29

No fixture rows were added to coverage.

## Membership evidence

Secondary history archive:
`https://github.com/unliftedq/index-constitution`

The archive describes CSI300 history as based on official CSI announcements. W02 keeps this as `SECONDARY` because the underlying official files were not directly retrieved.

V1.1 materializes only explicitly evidenced events. It does not infer individual effective dates from a rebalance date.

## Event status

- materialized ADD: 3
- materialized REMOVE: 3
- REBALANCE summaries: 2
- event reconstruction: PARTIAL
- reported but not individually materialized June-2021 additions: 23
- reported but not individually materialized June-2021 removals: 22

## Point-in-Time

For 2021-01-29:

- membership evidence: 300
- IN_INDEX price rows: 202
- OUT_OF_INDEX price rows: 2
- UNKNOWN: 0
- PIT verified: 0
- PIT partial: 204

The two OUT_OF_INDEX rows correspond to the same excluded security on two trading dates; membership is not inferred from price existence.

## Price expansion

The public Tushare-derived archive states that it contains daily data for 800 Chinese stocks in separate CSV files. W02 did not acquire an additional local real batch during V1.1, so the 100×10 minimum price target remains unmet.
