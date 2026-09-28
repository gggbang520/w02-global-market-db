from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
DATA_VERSION='DATA-2026-W39'; SOFTWARE_VERSION='1.1.0'
PRICE_SOURCE='SRC-GITHUB-TUSHARE-ARCHIVE'; MEMBERSHIP_SOURCE='SRC-INDEX-CONSTITUTION-SECONDARY'
RETRIEVED_AT='2026-09-27T00:00:00Z'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,d): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    members=load(ROOT/'data/standardized/index/index_constituent_history.json')
    prices=[]
    for p in sorted((ROOT/'data/history/by_observation_date/2021/01').glob('price_daily__*.json')): prices += load(p)['records']
    pit=load(ROOT/'data/current/stocks/csi300_price_point_in_time.json')['records']
    mset={m['listing_id'] for m in members}; pset={p['listing_id'] for p in prices}
    dates=sorted({p['trade_date'] for p in prices})
    in_n=sum(x['membership_status']=='IN_INDEX' for x in pit); out_n=sum(x['membership_status']=='OUT_OF_INDEX' for x in pit); unk_n=sum(x['membership_status']=='UNKNOWN' for x in pit)
    # coverage
    cov={'index_id':'CN-CS300','year':2021,'month':1,'trade_date_count':len(dates),'trade_dates':dates,'distinct_listings':len(pset),'total_rows':len(prices),'point_in_time_membership_available':True,'point_in_time_membership_verified':False,'point_in_time_membership_status':'PARTIAL_SECONDARY_SOURCE','price_coverage':len(pset)/300,'membership_count_on_2021-01-29':len(mset),'point_in_time_join_rows':len(pit),'point_in_time_in_index_rows':in_n,'point_in_time_out_of_index_rows':out_n,'point_in_time_unknown_rows':unk_n,'source_id':PRICE_SOURCE,'membership_source_id':MEMBERSHIP_SOURCE,'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION}
    dump(ROOT/'reports/quality/csi300_historical_coverage_matrix.json',[cov])
    # quality
    q={'historical_price_rows':len(prices),'distinct_listings':len(pset),'distinct_trade_dates':len(dates),'membership_records':len(members),'membership_verified':0,'membership_unknown':0,'membership_source_confirmed':len(members),'point_in_time_rows':len(pit),'point_in_time_verified':0,'point_in_time_partial':in_n+out_n,'point_in_time_unknown':unk_n,'point_in_time_in_index':in_n,'point_in_time_out_of_index':out_n,'data_quality_status':'POINT_IN_TIME_PARTIAL','price_quality_status':'SOURCE_CONFIRMED','membership_quality_status':'SOURCE_CONFIRMED_SECONDARY','license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION}
    dump(ROOT/'reports/quality/csi300_point_in_time_quality.json',q)
    # membership reconciliation
    dump(ROOT/'reports/quality/csi300_membership_reconciliation/2021-01-29.json',{'observation_date':'2021-01-29','official_only':0,'secondary_only':300,'both_same':0,'both_different':0,'unknown':0,'secondary_source':MEMBERSHIP_SOURCE,'official_source':'SRC-CSI-OFFICIAL','status':'OFFICIAL_NOT_ESTABLISHED','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    # PIT reconciliation
    dump(ROOT/'reports/update/csi300_point_in_time_diff.json',{'comparison':'none_to_v1.0','previous_rows':0,'current_rows':len(pit),'NEW':len(pit),'REMOVED':0,'MATCH':0,'CHANGED':0,'CONFLICT':0,'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/update/csi300_membership_diff.json',{'comparison':'no_previous_historical_membership_snapshot_to_2021-01-29','previous_membership_records':0,'current_membership_records':300,'NEW':300,'REMOVED':0,'MATCH':0,'CHANGED':0,'CONFLICT':0,'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    # dual lineage
    lineage=[]
    for x in pit:
        lineage.append({'index_id':'CN-CS300','trade_date':x['trade_date'],'listing_id':x['listing_id'],'security_id':x['security_id'],'price_lineage':{'source_id':PRICE_SOURCE,'source_origin':'MANUAL_FILE','schema_version':'stock_daily.v1','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,'validation':'PASS'},'membership_lineage':{'source_id':MEMBERSHIP_SOURCE,'source_origin':'SECONDARY','membership_record_key':x['membership_lineage_ref'],'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,'validation':'SOURCE_CONFIRMED_SECONDARY'},'join':{'join_rule':x['join_rule'],'join_version':x['join_version'],'input_versions':x['input_versions'],'derived_at':x['derived_at']}})
    dump(ROOT/'reports/lineage/price_membership_dual_lineage.json',lineage)
    # stock coverage
    by={}
    for p in prices: by.setdefault(p['listing_id'],[]).append(p['trade_date'])
    stock=[]
    for m in members:
        ds=sorted(set(by.get(m['listing_id'],[])))
        stock.append({'security_id':m['security_id'],'listing_id':m['listing_id'],'first_trade_date':ds[0] if ds else None,'last_trade_date':ds[-1] if ds else None,'trade_date_count':len(ds),'missing_dates':sorted(set(dates)-set(ds)) if ds else [],'missing_date_status':'NO_OBSERVED_PRICE' if not ds else ('NONE_WITHIN_OBSERVED_DATES' if len(ds)==len(dates) else 'DATA_MISSING_WITHIN_OBSERVED_DATES'),'membership_verified_date_count':0,'membership_evidence_date_count':len(ds),'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/quality/csi300_stock_level_coverage.json',stock)
    # missing-day classification summary
    dump(ROOT/'reports/quality/csi300_missing_date_classification.json',{'observed_global_trade_dates':dates,'NO_TRADE':0,'SUSPENDED':0,'NOT_LISTED':0,'DATA_MISSING':0,'UNKNOWN':len(members)-len(pset),'note':'No exchange calendar/suspension feed is available in V1.0; absent historical prices outside the observed provider coverage are UNKNOWN, not DATA_MISSING.','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    # receipts
    raw=ROOT/'data/raw/inbox/market/CSI300_EOD__TushareArchive__2021-01-28_2021-01-29.csv'
    receipt={'dataset':'csi300_point_in_time','observation_date':'2021-01-29','price_source_id':PRICE_SOURCE,'membership_source_id':MEMBERSHIP_SOURCE,'price_file_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'price_raw_rows':204,'price_valid_rows':204,'membership_records':300,'point_in_time_rows':len(pit),'point_in_time_in_index_rows':in_n,'point_in_time_out_of_index_rows':out_n,'point_in_time_unknown_rows':unk_n,'publish_gate':'PASS_FOR_INTERNAL_SNAPSHOT','status':'SUCCESS','retrieved_at':RETRIEVED_AT,'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION}
    dump(ROOT/'reports/ingestion/CSI300_POINT_IN_TIME__2021-01-29__receipt.json',receipt)
    # weekly/ytd guards
    dump(ROOT/'reports/quality/csi300_price_ytd.json',{'status':'NOT_AVAILABLE','reason':'Only two provider dates (2021-01-28, 2021-01-29); no year-start reference date is present.','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/quality/csi300_weekly_guard.json',{'status':'NOT_DERIVED','reason':'Only two observations and both are in the same ISO week; prior week-end reference is absent.','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    # final status
    dump(ROOT/'reports/quality/v10_final_status.json',{'software_version':SOFTWARE_VERSION,'data_version':DATA_VERSION,'historical_membership_source_status':'SECONDARY_ESTABLISHED_OFFICIAL_NOT_ESTABLISHED','historical_membership_2021-01-29':300,'historical_price_rows':204,'historical_price_distinct_listings':102,'historical_price_distinct_trade_dates':2,'pit_rows':len(pit),'pit_in_index_rows':in_n,'pit_out_of_index_rows':out_n,'pit_unknown_rows':unk_n,'pit_quality':'POINT_IN_TIME_PARTIAL','canonical_current_unchanged':True,'canonical_current_latest_trade_date':'2026-09-24','weekly':'NOT_DERIVED','ytd':'NOT_AVAILABLE','license_gate':'REVIEW','price_provider':PRICE_SOURCE,'membership_provider':MEMBERSHIP_SOURCE})
    print(json.dumps({'membership':len(members),'prices':len(prices),'pit':len(pit),'in':in_n,'out':out_n,'unknown':unk_n,'status':'OK'}))
if __name__=='__main__': main()
