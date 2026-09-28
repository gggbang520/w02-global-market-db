import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'/'analysis'))
from membership_events import active_from_events

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def test_membership_event_schema():
    rows=load(ROOT/'data/standardized/index/index_constituent_event.json')['records']
    required={'event_id','index_id','security_id','listing_id','event_date','effective_from','effective_to','event_type','source_id','source_origin','data_quality_status','license_gate'}
    assert rows and required.issubset(rows[0])

def test_add_event(): assert any(x['event_type']=='ADD' and x['event_id']=='CSI300-ADD-2021-06-11-300274' for x in load(ROOT/'data/standardized/index/index_constituent_event.json')['records'])

def test_remove_event(): assert any(x['event_type']=='REMOVE' for x in load(ROOT/'data/standardized/index/index_constituent_event.json')['records'])

def test_effective_date_logic():
    e=[{'event_id':'1','listing_id':'A','event_type':'ADD','effective_from':'2021-01-01'},{'event_id':'2','listing_id':'A','event_type':'REMOVE','effective_from':'2021-02-01'}]
    assert 'A' in active_from_events(e,'2021-01-29') and 'A' not in active_from_events(e,'2021-02-02')

def test_snapshot_reconstruction_is_separate(): assert load(ROOT/'data/history/by_observation_date/2021/01/CSI300__membership__2021-01-29.json')['constituent_count']==300

def test_point_in_time_query():
    p=load(ROOT/'data/current/stocks/csi300_price_point_in_time.json')['records']; assert {x['membership_status'] for x in p}=={'IN_INDEX','OUT_OF_INDEX'}

def test_official_secondary_reconciliation(): assert load(ROOT/'reports/quality/csi300_membership_reconciliation/2021-01-29.json')['status']=='OFFICIAL_NOT_ESTABLISHED'

def test_event_reconciliation_partial(): assert load(ROOT/'reports/quality/csi300_membership_event_summary.json')['event_reconstruction_status']=='PARTIAL'

def test_historical_coverage_matrix():
    d=load(ROOT/'reports/quality/csi300_historical_coverage_matrix.json'); assert d['year_summary'][0]['trade_date_count']==2

def test_stock_level_coverage():
    d=load(ROOT/'reports/quality/csi300_stock_level_coverage.json'); assert len(d)==300 and all('trade_date_count' in x for x in d)

def test_missing_date_classification(): assert load(ROOT/'reports/quality/csi300_missing_date_classification.json')['DATA_MISSING']==0

def test_provider_provenance():
    d=load(ROOT/'data/source_provenance.json'); assert d['acquisition_source']['source_id']=='SRC-GITHUB-TUSHARE-ARCHIVE' and d['declared_upstream_source']['source_name']=='Tushare Pro'

def test_observation_ingestion_separation():
    x=load(ROOT/'data/history/by_observation_date/2021/01/price_daily__2021-01-29__SRC-GITHUB-TUSHARE-ARCHIVE.json')['records'][0]; assert x['trade_date']!=x['ingestion_date']

def test_pit_quality_guard():
    d=load(ROOT/'reports/quality/csi300_point_in_time_quality.json'); assert d['point_in_time_verified']==0 and d['point_in_time_partial']==204

def test_historical_price_expansion_guard(): assert load(ROOT/'reports/quality/v11_final_status.json')['price_expansion_minimum_met'] is False

def test_distinct_listings(): assert load(ROOT/'reports/quality/v12_final_status.json')['historical_price_distinct_listings']==102

def test_distinct_trade_dates(): assert load(ROOT/'reports/quality/v12_final_status.json')['historical_price_distinct_trade_dates']==2

def test_weekly_multidate_guard(): assert load(ROOT/'reports/quality/csi300_weekly_guard.json')['status']=='NOT_DERIVED'

def test_current_guard(): assert load(ROOT/'data/current/stocks/providers/SRC-GITHUB-TUSHARE-ARCHIVE__latest.json')['canonical_current_promotion'] is False

def test_pit_lineage():
    x=load(ROOT/'reports/lineage/price_membership_dual_lineage.json')[0]; assert x['membership_lineage']['event_ledger_version']=='index_constituent_event.v1.3'

def test_membership_lineage():
    x=load(ROOT/'reports/lineage/price_membership_dual_lineage.json')[0]; assert x['membership_lineage']['source_id']=='SRC-INDEX-CONSTITUTION-SECONDARY'

def test_event_diff(): assert load(ROOT/'reports/update/csi300_membership_event_diff.json')['NEW']==96

def test_price_diff(): assert load(ROOT/'reports/update/csi300_historical_price_diff.json')['NEW']==0

def test_pit_diff(): assert load(ROOT/'reports/update/csi300_pit_diff.json')['current_rows']==204

def test_import_receipt(): assert load(ROOT/'reports/ingestion/CSI300_V11__2026-09-27__receipt.json')['status']=='SUCCESS'

def test_license_review(): assert load(ROOT/'reports/quality/csi300_point_in_time_quality.json')['license_gate']=='REVIEW'

def test_data_version():
    d=load(ROOT/'data-version.json'); assert d['data_version']=='DATA-2026-W39' and d['software_version']=='1.3.0'

def test_engineering_pass(): assert load(ROOT/'reports/quality/v12_final_status.json')['engineering_status']=='PASS'

def test_data_expansion_not_met(): assert load(ROOT/'reports/quality/v12_final_status.json')['data_expansion_status']=='NOT_MET'
