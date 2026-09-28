import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'/'analysis'))
from point_in_time import membership_at
from csi300_historical_join import build

MEM=ROOT/'data/standardized/index/index_constituent_history.json'
PRICE=ROOT/'data/history/by_observation_date/2021/01/price_daily__2021-01-29__SRC-GITHUB-TUSHARE-ARCHIVE.json'
PIT=ROOT/'data/current/stocks/csi300_price_point_in_time.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def test_point_in_time_membership_real_snapshot():
    m=load(MEM); assert len(m)==300; assert len({x['listing_id'] for x in m})==300

def test_effective_from_present():
    assert all(x['effective_from'] for x in load(MEM))

def test_effective_to_present_for_bounded_snapshot():
    assert all(x['effective_to']=='2021-06-15' for x in load(MEM))

def test_historical_join_real_prices():
    out=build(); assert len(out)==204

def test_unknown_membership_not_coerced_to_out():
    m=load(MEM); active=membership_at(m,'2022-01-01'); assert 'LST-CN-000001' not in active

def test_current_not_used_for_history():
    pit=load(PIT)['records']; assert all(x['membership_source_id']=='SRC-INDEX-CONSTITUTION-SECONDARY' for x in pit)

def test_observation_vs_ingestion_date():
    d=load(PRICE); assert d['records'][0]['trade_date']=='2021-01-29'; assert d['records'][0]['retrieved_at'].startswith('2026-09-27')

def test_historical_coverage_matrix():
    d=load(ROOT/'reports/quality/csi300_historical_coverage_matrix.json'); d=d['year_summary'][0]; assert d['trade_date_count']==2 and d['distinct_listings']==102

def test_membership_lineage():
    d=load(ROOT/'reports/lineage/price_membership_dual_lineage.json'); assert len(d)==204; assert all(x['membership_lineage']['source_id']=='SRC-INDEX-CONSTITUTION-SECONDARY' for x in d)

def test_dual_lineage_has_price_and_membership():
    x=load(ROOT/'reports/lineage/price_membership_dual_lineage.json')[0]; assert 'price_lineage' in x and 'membership_lineage' in x and 'join' in x

def test_historical_provider_provenance():
    d=load(ROOT/'data/source_provenance.json'); assert d['acquisition_source']['source_id']=='SRC-GITHUB-TUSHARE-ARCHIVE'; assert d['declared_upstream_source']['source_name']=='Tushare Pro'

def test_provider_current_guard():
    d=load(ROOT/'data/current/stocks/providers/SRC-GITHUB-TUSHARE-ARCHIVE__latest.json'); assert d['canonical_current_promotion'] is False

def test_canonical_current_guard():
    d=load(ROOT/'data/current/stocks/price_daily.json'); assert d['records']; assert max(x['trade_date'] for x in d['records'])=='2026-09-24'

def test_missing_trade_day_classification():
    d=load(ROOT/'reports/quality/csi300_missing_date_classification.json'); assert d['DATA_MISSING']==0 and d['UNKNOWN']>=1

def test_weekly_multiday_guard():
    d=load(ROOT/'reports/quality/csi300_weekly_guard.json'); assert d['status']=='NOT_DERIVED'

def test_ytd_reference_guard():
    d=load(ROOT/'reports/quality/csi300_price_ytd.json'); assert d['status']=='NOT_AVAILABLE'

def test_20210129_membership_count():
    d=load(ROOT/'data/history/by_observation_date/2021/01/CSI300__2021-01-29__membership.json'); assert d['membership_count']==300

def test_20210129_price_membership_join_counts():
    d=load(PIT)['records']; assert sum(x['membership_status']=='IN_INDEX' for x in d)==202

def test_20210129_out_of_index_is_explicit():
    d=load(PIT)['records']; out={x['ticker'] for x in d if x['membership_status']=='OUT_OF_INDEX'}; assert out=={'300274'}

def test_unknown_not_used_for_observed_complete_snapshot():
    d=load(PIT)['records']; assert sum(x['membership_status']=='UNKNOWN' for x in d)==0

def test_point_in_time_quality_is_not_verified():
    d=load(ROOT/'reports/quality/csi300_point_in_time_quality.json'); assert d['point_in_time_verified']==0 and d['point_in_time_partial']==204

def test_membership_reconciliation_status():
    d=load(ROOT/'reports/quality/csi300_membership_reconciliation/2021-01-29.json'); assert d['secondary_only']==300 and d['status']=='OFFICIAL_NOT_ESTABLISHED'

def test_membership_source_is_secondary():
    d=load(ROOT/'data/source_registry.json'); x=[z for z in d if z['source_id']=='SRC-INDEX-CONSTITUTION-SECONDARY'][0]; assert x['source_type']=='SECONDARY' and x['license_gate']=='REVIEW'

def test_point_in_time_diff():
    d=load(ROOT/'reports/update/csi300_point_in_time_diff.json'); assert d['NEW']==204 and d['REMOVED']==0

def test_membership_diff():
    d=load(ROOT/'reports/update/csi300_membership_diff.json'); assert d['NEW']==300

def test_time_model_fields_on_price():
    d=load(PRICE)['records'][0]; assert d['trade_date']=='2021-01-29' and d['observation_date']=='2021-01-29' and d['ingestion_date']=='2026-09-27'

def test_time_model_fields_on_membership():
    d=load(MEM)[0]; assert d['observation_date']=='2021-01-29' and d['ingestion_date']=='2026-09-27'

def test_history_storage_by_observation_date():
    assert (ROOT/'data/history/by_observation_date/2021/01').exists()

def test_history_storage_by_ingestion_snapshot():
    assert (ROOT/'data/history/by_ingestion_snapshot/DATA-2026-W39').exists()
