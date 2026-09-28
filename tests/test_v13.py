import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def events(): return load(ROOT/'data/standardized/index/index_constituent_event.json')['records']

def test_event_evidence_schema():
    required={'event_id','index_id','security_id','listing_id','event_date','effective_from','effective_to','event_type','source_id','source_origin','evidence_id','evidence_event_status','data_quality_status','license_gate'}
    assert required.issubset(events()[0])

def test_event_types_strict(): assert {e['event_type'] for e in events()} <= {'ADD','REMOVE','WEIGHT_CHANGE','RANK_CHANGE','REBALANCE','UNKNOWN'}

def test_event_status_strict(): assert {e['evidence_event_status'] for e in events()} <= {'CONFIRMED','SOURCE_DECLARED','INFERRED','UNKNOWN'}

def test_source_origin_classification(): assert {e['source_origin'] for e in events()} <= {'OFFICIAL_PRIMARY','OFFICIAL_MIRROR','SECONDARY_REPRODUCTION','SECONDARY_ARCHIVE','SECONDARY','REFERENCE'}

def test_no_official_primary_event_claim(): assert not any(e['source_origin']=='OFFICIAL_PRIMARY' for e in events())

def test_2020_add_count(): assert sum(e['event_type']=='ADD' and e['event_date']=='2020-12-14' for e in events())==26

def test_2020_remove_count(): assert sum(e['event_type']=='REMOVE' and e['event_date']=='2020-12-14' for e in events())==26

def test_2021_add_count(): assert sum(e['event_type']=='ADD' and e['event_date']=='2021-06-11' for e in events())==25

def test_2021_remove_count(): assert sum(e['event_type']=='REMOVE' and e['event_date']=='2021-06-11' for e in events())==25

def test_rebalance_count(): assert sum(e['event_type']=='REBALANCE' for e in events())==2

def test_rebalance_not_security_event(): assert all(e['security_id'] is None and e['listing_id'] is None for e in events() if e['event_type']=='REBALANCE')

def test_2020_effective_from(): assert all(e['effective_from']=='2020-12-14' for e in events() if e['event_type']=='ADD' and e['event_date']=='2020-12-14')

def test_2020_effective_to(): assert all(e['effective_to']=='2020-12-14' for e in events() if e['event_type']=='REMOVE' and e['event_date']=='2020-12-14')

def test_2021_effective_from_boundary(): assert all(e['effective_from']=='2021-06-15' for e in events() if e['event_type']=='ADD' and e['event_date']=='2021-06-11')

def test_2021_effective_to_boundary(): assert all(e['effective_to']=='2021-06-15' for e in events() if e['event_type']=='REMOVE' and e['event_date']=='2021-06-11')

def test_2020_evidence_record():
    d=load(ROOT/'reports/quality/csi300_membership_evidence/2020-12-14.json'); assert d['reported_replacement_count']==26 and d['materialized_add_count']==26 and d['materialized_remove_count']==26

def test_2021_evidence_record():
    d=load(ROOT/'reports/quality/csi300_membership_evidence/2021-06-11.json'); assert d['reported_replacement_count']==25 and d['materialized_add_count']==25 and d['materialized_remove_count']==25

def test_official_status_not_established(): assert load(ROOT/'reports/quality/csi300_membership_evidence/official_status.json')['historical_event_file_status']=='NOT_ESTABLISHED'

def test_2020_snapshot_count(): assert load(ROOT/'data/history/by_observation_date/2020/12/CSI300__membership__2020-12-14.json')['constituent_count']==300

def test_2021_snapshot_count(): assert load(ROOT/'data/history/by_observation_date/2021/06/CSI300__membership__2021-06-15.json')['constituent_count']==300

def test_snapshot_reconstruction_status():
    for p in [ROOT/'data/history/by_observation_date/2020/12/CSI300__membership__2020-12-14.json',ROOT/'data/history/by_observation_date/2021/06/CSI300__membership__2021-06-15.json']:
        assert load(p)['reconstruction_status']=='PARTIAL_SECONDARY'

def test_2020_snapshot_has_added_member():
    m={x['listing_id'] for x in load(ROOT/'data/history/by_observation_date/2020/12/CSI300__membership__2020-12-14.json')['members']}; assert 'LST-CN-002049' in m

def test_2020_snapshot_excludes_removed_member():
    m={x['listing_id'] for x in load(ROOT/'data/history/by_observation_date/2020/12/CSI300__membership__2020-12-14.json')['members']}; assert 'LST-CN-000709' not in m

def test_2021_snapshot_has_new_member():
    m={x['listing_id'] for x in load(ROOT/'data/history/by_observation_date/2021/06/CSI300__membership__2021-06-15.json')['members']}; assert 'LST-CN-300274' in m

def test_2021_snapshot_excludes_removed_member():
    m={x['listing_id'] for x in load(ROOT/'data/history/by_observation_date/2021/06/CSI300__membership__2021-06-15.json')['members']}; assert 'LST-CN-000627' not in m

def test_membership_coverage_separate():
    d=load(ROOT/'reports/quality/csi300_coverage_summary.json'); assert d['membership_coverage']['numerator']==300 and d['historical_price_coverage']['numerator']==102

def test_price_coverage_not_merged_with_membership():
    d=load(ROOT/'reports/quality/csi300_coverage_summary.json'); assert d['historical_price_coverage']['denominator']==300 and d['membership_coverage']['denominator']==300

def test_pit_coverage_separate(): assert load(ROOT/'reports/quality/csi300_coverage_summary.json')['pit_coverage']['numerator']==102

def test_price_expansion_real_only(): assert load(ROOT/'reports/quality/csi300_historical_price_expansion_v13.json')['real_data_only'] is True

def test_price_expansion_reason_recorded(): assert load(ROOT/'reports/quality/csi300_historical_price_expansion_v13.json')['status']=='NOT_MET'

def test_no_fixture_rows_in_expansion(): assert load(ROOT/'reports/quality/csi300_historical_price_expansion_v13.json')['actual']['rows']==204

def test_dual_lineage_v13(): assert load(ROOT/'reports/lineage/price_membership_dual_lineage.json')[0]['membership_lineage']['event_ledger_version']=='index_constituent_event.v1.3'

def test_join_version_v13(): assert load(ROOT/'data/current/stocks/csi300_price_point_in_time.json')['records'][0]['join_version']=='point_in_time_join.v1.3'

def test_provider_current_guard(): assert load(ROOT/'data/current/stocks/providers/SRC-GITHUB-TUSHARE-ARCHIVE__latest.json')['canonical_current_promotion'] is False

def test_canonical_current_unchanged(): assert load(ROOT/'reports/quality/v13_final_status.json')['canonical_current_latest_trade_date']=='2026-09-24'

def test_license_review(): assert load(ROOT/'reports/quality/v13_final_status.json')['license_gate']=='REVIEW'

def test_receipt_v13(): assert load(ROOT/'reports/ingestion/CSI300_V13__2026-09-27__receipt.json')['status']=='SUCCESS'

def test_event_diff_expansion(): assert load(ROOT/'reports/update/csi300_membership_event_diff.json')['NEW']==96

def test_price_diff_no_new_rows(): assert load(ROOT/'reports/update/csi300_historical_price_diff.json')['NEW']==0

def test_pit_diff_rows(): assert load(ROOT/'reports/update/csi300_pit_diff.json')['current_rows']==204

def test_weekly_guard(): assert load(ROOT/'reports/quality/csi300_weekly_guard.json')['status']=='NOT_DERIVED'

def test_ytd_guard(): assert load(ROOT/'reports/quality/csi300_price_ytd.json')['status']=='NOT_AVAILABLE'
