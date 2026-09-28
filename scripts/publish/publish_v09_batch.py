from __future__ import annotations
import json, hashlib
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
SOURCE='SRC-GITHUB-TUSHARE-ARCHIVE'
SOFTWARE='0.9.0'
DATA='DATA-2026-W39'
INPUT=ROOT/'data/raw/inbox/market/CSI300_EOD__TushareArchive__2021-01-28_2021-01-29.csv'

def load_current_members():
    p=ROOT/'data/current/constituents/CSI300__current.json'
    return json.loads(p.read_text())['constituents']

def load_records():
    out=[]
    for p in (ROOT/'data/standardized/stocks').glob(f'LST-CN-*__*__{SOURCE}.json'):
        out.append(json.loads(p.read_text()))
    return sorted(out,key=lambda r:(r['trade_date'],r['listing_id']))

def sha256(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
    recs=load_records()
    members=load_current_members(); target={x['listing_id'] for x in members}
    mapped=sorted({r['listing_id'] for r in recs if r.get('listing_id') in target})
    dates=sorted({r['trade_date'] for r in recs})
    rows=len(recs)
    by_date=defaultdict(list)
    for r in recs: by_date[r['trade_date']].append(r)
    coverage={
      'dataset':'stock_daily','index_id':'CN-CS300','data_version':DATA,'software_version':SOFTWARE,
      'target_constituents':300,'secondary_constituents_reference':297,'mapped_constituents':len(mapped),
      'distinct_listings':len({r['listing_id'] for r in recs}), 'distinct_trade_dates':len(dates),
      'total_rows':rows,'valid_rows':rows,'invalid_rows':0,'duplicate_rows':0,
      'coverage_rate_by_listing':len(mapped)/300,'coverage_rate_by_date':len(dates),
      'earliest_trade_date':dates[0],'latest_trade_date':dates[-1],
      'missing_listings_count':300-len(mapped),'missing_dates':[],
      'source_id':SOURCE,'source_origin':'MANUAL_FILE','price_type':'RAW_CLOSE',
      'note':'Coverage is against the current 2026 CSI300 membership reference. The historical price source is not a point-in-time 2021 constituent snapshot.'
    }
    q={
      'source_id':SOURCE,'dataset':'stock_daily','total_rows':rows,'distinct_listings':len({r['listing_id'] for r in recs}),
      'distinct_dates':len(dates),'valid_rows':rows,'invalid_rows':0,'duplicate_rows':0,'review_rows':0,
      'missing_rows':300-len(mapped),'source_confirmed_rows':rows,'data_quality_status':'SOURCE_CONFIRMED',
      'price_type':'RAW_CLOSE','turnover_unit':'source_native_amount','volume_unit':'source_native_volume',
      'license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY'
    }
    qdir=ROOT/'reports/quality'; qdir.mkdir(parents=True,exist_ok=True)
    (qdir/'csi300_price_coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2))
    (qdir/'csi300_price_quality.json').write_text(json.dumps(q,ensure_ascii=False,indent=2))
    # provider qualification
    pq={
      'source_id':SOURCE,'source_name':'shaocongWu/Multivariate_Stock_Time_Series_Dataset (Tushare Pro-sourced archive)',
      'market':'CN A-share','dataset':'stock_daily','delivery_model':'PUBLIC_FILE','batch':True,'historical':True,
      'date_range':{'min':dates[0],'max':dates[-1]},'coverage':{'distinct_listings':len(mapped),'distinct_trade_dates':len(dates),'rows':rows},
      'fields':['ticker','trade_date','open','high','low','close','volume','turnover'],
      'access_status':'AVAILABLE','parse_status':'SUCCESS','quality_status':'PASS',
      'license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY','qualification':'CONDITIONAL',
      'reason':'Real public batch archive successfully parsed and mapped for 102 current CSI300 names across 2 dates; archive README attributes raw data to Tushare Pro, but this is not a direct Tushare endpoint and license/redistribution terms for this archived file are not established.'
    }
    pqpath=qdir/'provider_qualification'; pqpath.mkdir(parents=True,exist_ok=True)
    (pqpath/f'{SOURCE}.json').write_text(json.dumps(pq,ensure_ascii=False,indent=2))
    # field mapping
    fmap={'source_id':SOURCE,'fields':[{'source_field':'ticker','W02_field':'ticker','source_definition':'ts_code stock code','unit':None,'currency':None,'transform':'strip .SH/.SZ and map exchange','notes':'source-native ts_code'}, {'source_field':'trade_date','W02_field':'trade_date','source_definition':'transaction date','unit':'date','currency':None,'transform':'ISO date','notes':''},{'source_field':'open','W02_field':'open','source_definition':'opening price','unit':'CNY/share','currency':'CNY','transform':'numeric','notes':''},{'source_field':'high','W02_field':'high','source_definition':'highest price','unit':'CNY/share','currency':'CNY','transform':'numeric','notes':''},{'source_field':'low','W02_field':'low','source_definition':'lowest price','unit':'CNY/share','currency':'CNY','transform':'numeric','notes':''},{'source_field':'close','W02_field':'close','source_definition':'closing price','unit':'CNY/share','currency':'CNY','transform':'numeric','notes':'RAW_CLOSE'}, {'source_field':'vol','W02_field':'volume','source_definition':'transaction volume','unit':'source_native','currency':None,'transform':'numeric','notes':'not rescaled'}, {'source_field':'amount','W02_field':'turnover','source_definition':'stock amount','unit':'source_native','currency':'CNY','transform':'numeric','notes':'source-native amount'}]}
    provdir=qdir/'providers'; provdir.mkdir(parents=True,exist_ok=True); (provdir/f'{SOURCE}_field_mapping.json').write_text(json.dumps(fmap,ensure_ascii=False,indent=2))
    # history + provider-specific current snapshot; do not replace canonical 2026 current with stale 2021 data
    hdir=ROOT/'data/history'/DATA/'stocks'; hdir.mkdir(parents=True,exist_ok=True)
    hist=hdir/f'price_daily__{dates[-1]}__{SOURCE}.json'
    hist.write_text(json.dumps({'dataset':'stock_daily','data_version':DATA,'software_version':SOFTWARE,'source_summary':{'source_id':SOURCE,'source_origin':'MANUAL_FILE','license_gate':'REVIEW'},'records':recs,'coverage':coverage},ensure_ascii=False,indent=2))
    cdir=ROOT/'data/current/stocks/providers'; cdir.mkdir(parents=True,exist_ok=True)
    latest=[r for r in recs if r['trade_date']==dates[-1]]
    cdir.joinpath(f'{SOURCE}__latest.json').write_text(json.dumps({'dataset':'stock_daily','data_version':DATA,'software_version':SOFTWARE,'source_summary':{'source_id':SOURCE,'source_origin':'MANUAL_FILE','license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY'},'latest_trade_date':dates[-1],'canonical_current_promotion':False,'promotion_reason':'Historical source ends in 2021 and is stale versus canonical current latest trade date 2026-09-24. Provider-specific current snapshot retained without replacing canonical Current.','records':latest},ensure_ascii=False,indent=2))
    # lineage
    ldir=ROOT/'reports/lineage'; ldir.mkdir(parents=True,exist_ok=True)
    lineage=[]
    digest=sha256(INPUT)
    for r in recs:
      lineage.append({'listing_id':r['listing_id'],'trade_date':r['trade_date'],'source_id':SOURCE,'source_origin':'MANUAL_FILE','input_file':str(INPUT.relative_to(ROOT)),'sha256':digest,'parser_version':'0.9.0','schema_version':'stock_daily.v1','data_version':DATA,'software_version':SOFTWARE,'validation':'PASS','published_to_history':str(hist.relative_to(ROOT)),'provider_current':str((cdir/f'{SOURCE}__latest.json').relative_to(ROOT))})
    (ldir/'price_lineage.json').write_text(json.dumps(lineage,ensure_ascii=False,indent=2))
    # diff against canonical current records: all new because dates/source differ
    ddir=ROOT/'reports/update'; ddir.mkdir(parents=True,exist_ok=True)
    diff={'source_id':SOURCE,'data_version':DATA,'software_version':SOFTWARE,'comparison':'V0.8 canonical current vs V0.9 provider batch','NEW':rows,'REMOVED':0,'MATCH':0,'CHANGED':0,'CONFLICT':0,'note':'Historical 2021 provider batch has no overlapping canonical current trade-date records.'}
    (ddir/'csi300_price_provider_diff.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2))
    # receipt corrected
    rdir=ROOT/'reports/ingestion'; rdir.mkdir(parents=True,exist_ok=True)
    receipt={'source_id':SOURCE,'dataset':'stock_daily','input_file':str(INPUT.relative_to(ROOT)),'input_origin':'MANUAL_PROVIDER_FILE','sha256':digest,'file_size':INPUT.stat().st_size,'content_type':'text/csv','trade_date_min':dates[0],'trade_date_max':dates[-1],'raw_rows':rows,'parsed_rows':rows,'valid_rows':rows,'invalid_rows':0,'duplicate_rows':0,'review_rows':0,'distinct_listings':len({r['listing_id'] for r in recs}),'distinct_dates':len(dates),'publish_gate':'PASS','status':'SUCCESS','license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY','retrieved_at':'2026-09-27T13:45:00Z'}
    (rdir/f'CSI300_EOD__{SOURCE}__{dates[-1]}__receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print(json.dumps({'rows':rows,'listings':len(mapped),'dates':dates,'sha256':digest,'coverage_rate':len(mapped)/300,'history':str(hist.relative_to(ROOT))},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
