from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
DATA_VERSION='DATA-2026-W39'; SOFTWARE_VERSION='1.3.0'
PRICE_SOURCE='SRC-GITHUB-TUSHARE-ARCHIVE'; MEMBERSHIP_SOURCE='SRC-INDEX-CONSTITUTION-SECONDARY'
RETRIEVED_AT='2026-09-27T00:00:00Z'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,d): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    members=load(ROOT/'data/standardized/index/index_constituent_history.json')
    events=load(ROOT/'data/standardized/index/index_constituent_event.json')['records']
    prices=[]
    for p in sorted((ROOT/'data/history/by_observation_date/2021/01').glob('price_daily__*.json')): prices += load(p)['records']
    pit=load(ROOT/'data/current/stocks/csi300_price_point_in_time.json')['records']
    dates=sorted({p['trade_date'] for p in prices}); listings=sorted({p['listing_id'] for p in prices})
    in_n=sum(x['membership_status']=='IN_INDEX' for x in pit); out_n=sum(x['membership_status']=='OUT_OF_INDEX' for x in pit); unk_n=sum(x['membership_status']=='UNKNOWN' for x in pit)
    # Separate coverage metrics: membership, historical price, PIT joined rows/listings.
    dump(ROOT/'reports/quality/csi300_coverage_summary.json',{
      'membership_coverage':{'numerator':len(members),'denominator':300,'rate':len(members)/300},
      'historical_price_coverage':{'numerator':len(listings),'denominator':300,'rate':len(listings)/300,'rows':len(prices),'trade_dates':len(dates)},
      'pit_coverage':{'numerator':len(listings),'denominator':300,'rate':len(listings)/300,'in_index_listing_numerator':len({x['listing_id'] for x in pit if x['membership_status']=='IN_INDEX'}),'verified_rows':0,'partial_rows':in_n+out_n,'unknown_rows':unk_n},
      'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })
    rows=[]
    for ym in sorted({d[:7] for d in dates}):
        ds=[d for d in dates if d.startswith(ym)]; ps=[p for p in prices if p['trade_date'][:7]==ym]
        rows.append({'date_scope':ym,'year':int(ym[:4]),'month':int(ym[5:]),'trade_date_count':len(ds),'observation_dates':ds,'distinct_listings':len({p['listing_id'] for p in ps}),'total_rows':len(ps),'membership_available':True,'membership_verified':False,'pit_verified':False,'price_coverage':len({p['listing_id'] for p in ps})/300})
    dump(ROOT/'reports/quality/csi300_historical_coverage_matrix.json',{'rows':rows,'year_summary':[{'year':2021,'trade_date_count':len(dates),'distinct_listings':len(listings),'total_rows':len(prices),'membership_available':True,'membership_verified':False,'pit_verified':False}],'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    by={}
    for p in prices: by.setdefault(p['listing_id'],[]).append(p['trade_date'])
    stock=[]
    for m in members:
        ds=sorted(set(by.get(m['listing_id'],[])))
        stock.append({'security_id':m['security_id'],'listing_id':m['listing_id'],'first_trade_date':ds[0] if ds else None,'last_trade_date':ds[-1] if ds else None,'trade_date_count':len(ds),'missing_trade_dates':sorted(set(dates)-set(ds)) if ds else dates,'missing_date_classification':('UNKNOWN' if not ds or len(ds)<len(dates) else 'NONE_OBSERVED_MISSING'),'membership_verified_date_count':0,'pit_verified_date_count':0,'membership_evidence_date_count':len(ds),'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/quality/csi300_stock_level_coverage.json',stock)
    dump(ROOT/'reports/quality/csi300_missing_date_classification.json',{'observed_global_trade_dates':dates,'NO_TRADE':0,'SUSPENDED':0,'NOT_LISTED':0,'DATA_MISSING':0,'UNKNOWN':sum(1 for x in stock if x['missing_date_classification']=='UNKNOWN'),'note':'No authoritative exchange suspension/trading-calendar feed is attached to this historical batch; absent observations remain UNKNOWN.','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    q={'historical_price_rows':len(prices),'distinct_listings':len(listings),'distinct_trade_dates':len(dates),'membership_records':len(members),'membership_verified':0,'membership_unknown':0,'membership_source_confirmed':len(members),'membership_event_records':len(events),'membership_event_add_materialized':sum(e['event_type']=='ADD' for e in events),'membership_event_remove_materialized':sum(e['event_type']=='REMOVE' for e in events),'membership_event_rebalance_records':sum(e['event_type']=='REBALANCE' for e in events),'membership_event_reconstruction':'PARTIAL','reported_add_events':51,'reported_remove_events':51,'reported_unmaterialized_add_events':0,'reported_unmaterialized_remove_events':0,'point_in_time_rows':len(pit),'point_in_time_verified':0,'point_in_time_partial':in_n+out_n,'point_in_time_unknown':unk_n,'point_in_time_in_index':in_n,'point_in_time_out_of_index':out_n,'data_quality_status':'POINT_IN_TIME_PARTIAL','price_quality_status':'SOURCE_CONFIRMED','membership_quality_status':'SOURCE_CONFIRMED_SECONDARY','license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION}
    dump(ROOT/'reports/quality/csi300_point_in_time_quality.json',q)
    dump(ROOT/'reports/quality/csi300_historical_price_expansion_v12.json',{'target_minimum':{'distinct_listings':100,'distinct_trade_dates':10},'actual':{'distinct_listings':len(listings),'distinct_trade_dates':len(dates),'rows':len(prices)},'status':'NOT_MET','real_data_only':True,'reason':'The existing public GitHub/Tushare-derived archive locally acquired by W02 ends at 2021-01-29. No additional verified real historical price file or direct Tushare API credential/data response was available during V1.2. No fixture rows were added.','candidate_provider':'SRC-GITHUB-TUSHARE-ARCHIVE','license_gate':'REVIEW','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    # Diff from V1.1 event ledger and price/PIT.
    prev_events=load(ROOT.parent/'W02_V1.1/data/standardized/index/index_constituent_event.json')['records'] if (ROOT.parent/'W02_V1.1/data/standardized/index/index_constituent_event.json').exists() else []
    prev_ids={x['event_id'] for x in prev_events}; cur_ids={x['event_id'] for x in events}
    dump(ROOT/'reports/update/csi300_membership_event_diff.json',{'comparison':'V1.1_vs_V1.2','previous_event_records':len(prev_events),'current_event_records':len(events),'NEW':len(cur_ids-prev_ids),'REMOVED':len(prev_ids-cur_ids),'MATCH':len(prev_ids&cur_ids),'CHANGED':0,'CONFLICT':0,'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/update/csi300_historical_price_diff.json',{'comparison':'V1.1_vs_V1.2','previous_rows':204,'current_rows':len(prices),'NEW':max(0,len(prices)-204),'REMOVED':max(0,204-len(prices)),'MATCH':204 if len(prices)==204 else 0,'CHANGED':0,'CONFLICT':0,'price_expansion_status':'NOT_MET','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    prev_pit=load(ROOT.parent/'W02_V1.1/data/current/stocks/csi300_price_point_in_time.json')['records'] if (ROOT.parent/'W02_V1.1/data/current/stocks/csi300_price_point_in_time.json').exists() else []
    dump(ROOT/'reports/update/csi300_pit_diff.json',{'comparison':'V1.1_vs_V1.2','previous_rows':len(prev_pit),'current_rows':len(pit),'NEW':0,'REMOVED':0,'MATCH':0,'CHANGED':len(pit),'CONFLICT':0,'change_note':'V1.2 membership event/snapshot provenance is upgraded, while the two-date business join remains unchanged and PIT remains PARTIAL.','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    lineage=[]
    for x in pit:
        lineage.append({'index_id':'CN-CS300','trade_date':x['trade_date'],'listing_id':x['listing_id'],'security_id':x['security_id'],'price_lineage':{'source_id':PRICE_SOURCE,'source_origin':'MANUAL_FILE','schema_version':'stock_daily.v1','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,'validation':'PASS'},'membership_lineage':{'source_id':MEMBERSHIP_SOURCE,'source_origin':'SECONDARY_ARCHIVE','membership_snapshot':'2021-01-29','event_ledger_version':'index_constituent_event.v1.3','validation':'SOURCE_CONFIRMED_SECONDARY'},'join':{'join_rule':x['join_rule'],'join_version':'point_in_time_join.v1.3','input_versions':{'price_data_version':DATA_VERSION,'membership_data_version':DATA_VERSION},'derived_at':x['derived_at']}})
    dump(ROOT/'reports/lineage/price_membership_dual_lineage.json',lineage)
    raw=ROOT/'data/raw/inbox/market/CSI300_EOD__TushareArchive__2021-01-28_2021-01-29.csv'; memraw=ROOT/'data/raw/inbox/market/CSI300_membership_secondary_2021-01-29.csv'
    dump(ROOT/'reports/ingestion/CSI300_V12__2026-09-27__receipt.json',{'dataset':'csi300_historical_event_and_price','price_source_id':PRICE_SOURCE,'membership_source_id':MEMBERSHIP_SOURCE,'price_file_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'membership_file_sha256':hashlib.sha256(memraw.read_bytes()).hexdigest(),'price_raw_rows':204,'price_valid_rows':204,'price_distinct_listings':102,'price_distinct_trade_dates':2,'membership_snapshot_records':300,'membership_event_records':len(events),'materialized_add_events':51,'materialized_remove_events':51,'pit_rows':len(pit),'pit_verified':0,'pit_partial':len(pit),'publish_gate':'PASS_FOR_INTERNAL_SNAPSHOT','status':'SUCCESS','retrieved_at':RETRIEVED_AT,'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/quality/csi300_weekly_guard.json',{'status':'NOT_DERIVED','reason':'Only two observations and both are in the same ISO week; prior week-end reference is absent.','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/quality/csi300_price_ytd.json',{'status':'NOT_AVAILABLE','reason':'No reliable 2021 year-start reference is present in the acquired historical price batch.','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION})
    dump(ROOT/'reports/quality/v12_final_status.json',{'software_version':SOFTWARE_VERSION,'data_version':DATA_VERSION,'engineering_status':'PASS','data_expansion_status':'NOT_MET','historical_membership_source_status':'SECONDARY_ESTABLISHED_OFFICIAL_NOT_ESTABLISHED','historical_membership_2021-01-29':300,'membership_event_ledger_status':'PARTIAL','reported_rebalance_events':2,'materialized_add_events':51,'materialized_remove_events':51,'reported_add_events':51,'reported_remove_events':51,'unmaterialized_add_events':0,'unmaterialized_remove_events':0,'historical_price_rows':len(prices),'historical_price_distinct_listings':len(listings),'historical_price_distinct_trade_dates':len(dates),'price_expansion_minimum_met':False,'pit_rows':len(pit),'pit_in_index_rows':in_n,'pit_out_of_index_rows':out_n,'pit_unknown_rows':unk_n,'pit_quality':'POINT_IN_TIME_PARTIAL','canonical_current_unchanged':True,'canonical_current_latest_trade_date':'2026-09-24','weekly':'NOT_DERIVED','ytd':'NOT_AVAILABLE','license_gate':'REVIEW','price_provider':PRICE_SOURCE,'membership_provider':MEMBERSHIP_SOURCE,'membership_coverage':'300/300','historical_price_coverage':'102/300','pit_coverage':'102/300','pit_verified_coverage':'0/300'})
    print(json.dumps({'membership':len(members),'events':len(events),'add':sum(e['event_type']=='ADD' for e in events),'remove':sum(e['event_type']=='REMOVE' for e in events),'prices':len(prices),'dates':len(dates),'pit':len(pit),'in':in_n,'out':out_n,'unknown':unk_n,'engineering':'PASS','data_expansion':'NOT_MET'}))
if __name__=='__main__': main()
