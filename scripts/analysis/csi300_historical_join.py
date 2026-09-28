import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
"""Join historical prices with PIT membership using verified/qualified evidence windows."""
import json
from pathlib import Path
from datetime import datetime, timezone
from point_in_time import membership_at, status_for_price, snapshot_at

ROOT=Path(__file__).resolve().parents[2]
DATA_VERSION='DATA-2026-W39'; SOFTWARE_VERSION='1.3.0'
MEMBERSHIP_SOURCE='SRC-INDEX-CONSTITUTION-SECONDARY'
PRICE_SOURCE='SRC-GITHUB-TUSHARE-ARCHIVE'


def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def _snapshot_complete_for_date(records, td):
    # V1.0's secondary snapshot is explicitly bounded to the surrounding
    # rebalance interval. It is complete for its observation window, but not
    # an official historical event ledger.
    for r in records:
        if r.get('temporal_scope_type') == 'SNAPSHOT_BOUNDED_BY_KNOWN_REBALANCE_DATES':
            if r.get('effective_from') and r.get('effective_to') and r['effective_from'] <= td < r['effective_to']:
                return True
    return False


def build():
    members=load_json(ROOT/'data/standardized/index/index_constituent_history.json')
    snapshot_files=sorted((ROOT/'data/history/by_observation_date').glob('*/**/CSI300__membership__*.json'))
    snapshots=[load_json(p) for p in snapshot_files]
    prices=[]
    for p in sorted((ROOT/'data/history/by_observation_date/2021/01').glob('price_daily__*.json')):
        prices.extend(load_json(p)['records'])
    by_date={}
    for r in prices: by_date.setdefault(r['trade_date'], []).append(r)
    output=[]
    for td, rows in sorted(by_date.items()):
        snapshot_members=snapshot_at(snapshots, td)
        active=membership_at(members, td)
        if snapshot_members:
            active=snapshot_members
        complete=bool(snapshot_members)
        for p in rows:
            status, m=status_for_price(p['listing_id'],td,active,snapshot_complete=complete)
            quality='POINT_IN_TIME_PARTIAL' if status != 'UNKNOWN' else 'POINT_IN_TIME_UNKNOWN'
            rec={
                'index_id':'CN-CS300','trade_date':td,'observation_date':td,'ingestion_date':p.get('ingestion_date'),'retrieved_at':p.get('retrieved_at'),
                'security_id':p['security_id'],'listing_id':p['listing_id'],'ticker':p['ticker'],'exchange_mic':p['exchange_mic'],
                'close':p['close'],'volume':p['volume'],'turnover':p['turnover'],'price_type':p['price_type'],'currency':p['currency'],
                'membership_status':status,'membership_weight':m.get('weight') if m else None,'membership_rank':m.get('rank') if m else None,
                'membership_effective_from':m.get('effective_from') if m else None,'membership_effective_to':m.get('effective_to') if m else None,
                'membership_source_id':MEMBERSHIP_SOURCE,'membership_quality':'SOURCE_CONFIRMED_SECONDARY' if status != 'UNKNOWN' else 'UNKNOWN',
                'point_in_time_quality':quality,'price_source_id':p['source_id'],'price_lineage_ref':f"{p['listing_id']}|{td}|{p['source_id']}",
                'membership_lineage_ref':f"CN-CS300|{p['listing_id']}|{MEMBERSHIP_SOURCE}",
                'join_rule':'effective_from <= trade_date AND (effective_to IS NULL OR trade_date < effective_to); complete snapshot may classify absent member as OUT_OF_INDEX',
                'join_version':'point_in_time_join.v1.3','input_versions':{'price_data_version':DATA_VERSION,'membership_data_version':DATA_VERSION},
                'derived_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
            }
            output.append(rec)
    return output

if __name__=='__main__':
    out=build(); dest=ROOT/'data/current/stocks/csi300_price_point_in_time.json'
    dest.write_text(json.dumps({'dataset':'csi300_price_point_in_time','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,'records':out},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'rows':len(out),'in_index':sum(x['membership_status']=='IN_INDEX' for x in out),'out_of_index':sum(x['membership_status']=='OUT_OF_INDEX' for x in out),'unknown':sum(x['membership_status']=='UNKNOWN' for x in out)}))
