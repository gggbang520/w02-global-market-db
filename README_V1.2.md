# W02 V1.2｜CSI300 Historical Event Expansion + Multi-Date Price Expansion

## Status

- ENGINEERING = PASS
- Historical Event Evidence = materially expanded, PARTIAL
- Historical Membership = SECONDARY_ESTABLISHED
- Official Membership = NOT_ESTABLISHED
- Historical Price Expansion = NOT_MET
- PIT = POINT_IN_TIME_PARTIAL
- Canonical Current = unchanged at 2026-09-24
- pytest = 184 passed / 2 skipped

## Historical Event Evidence

V1.2 expands the CSI300 event ledger from 8 to 104 records:

- ADD = 51
- REMOVE = 51
- REBALANCE = 2
- WEIGHT_CHANGE = 0
- RANK_CHANGE = 0
- UNKNOWN = 0

The 51 ADD + 51 REMOVE records cover the exact security lists represented by the retrieved secondary evidence for:

- 2020-12-14: 26 additions + 26 removals
- 2021-06-11 adjustment: 25 additions + 25 removals

The event ledger keeps REBALANCE as a separate index-level evidence event. It does not use REBALANCE to synthesize security events.

## Source and provenance

The security-level historical lists are secondary evidence. The GitHub historical archive declares China Securities Index Co. official announcements as its upstream, but W02 did not directly retrieve the underlying CSI historical files. The 2021 list is additionally cross-checked against a secondary reproduction of the CSI announcement.

Therefore:

- source_origin is not promoted to OFFICIAL_PRIMARY
- official historical membership/event evidence remains NOT_ESTABLISHED
- license_gate remains REVIEW
- publication_scope remains INTERNAL_SNAPSHOT_ONLY

## Effective dates

- 2020-12-14 events use the source-declared adjustment boundary.
- 2021-06-11 announcement says the adjustment takes effect after the June 11 close; the membership boundary is represented as 2021-06-15 because June 14 was a market holiday. This basis is recorded in the evidence notes.

## Historical snapshots

Separate snapshots are stored under:

- `data/history/by_observation_date/2020/12/`
- `data/history/by_observation_date/2021/01/`
- `data/history/by_observation_date/2021/06/`

The reconstructed 2020-12-14 and 2021-06-15 snapshots remain `PARTIAL_SECONDARY` and are never promoted to verified.

## Historical Price

No new real price rows were added in V1.2. The retained real batch remains:

- 204 rows
- 102 distinct listings
- 2 distinct trade dates: 2021-01-28 and 2021-01-29
- coverage = 102 / 300 = 34.00%

The acquired GitHub/Tushare-derived archive locally available to W02 ends at 2021-01-29. No additional verified real historical file or direct Tushare API response was available in this run. No fixture rows were used to increase coverage.

Therefore:

`DATA_EXPANSION = NOT_MET`

## Point-in-Time

- PIT rows = 204
- IN_INDEX = 202
- OUT_OF_INDEX = 2
- UNKNOWN = 0
- PIT VERIFIED = 0
- PIT PARTIAL = 204

PIT remains PARTIAL because membership evidence is secondary. Adding more secondary events does not automatically upgrade PIT to VERIFIED.

## Coverage separation

- Membership coverage = 300 / 300
- Historical price coverage = 102 / 300
- PIT joined-listing coverage = 102 / 300
- PIT verified coverage = 0 / 300

These metrics are deliberately kept separate.

## Deferred

- PE/PB
- Capital Flow
- UI
- Global markets
- Fox Spirit visual layer

## Version

- data_version = `DATA-2026-W39`
- software_version = `1.2.0`
- supersedes = `1.1.0`
