from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
from datetime import datetime, timezone
from membership_events import event_dict

ROOT=Path(__file__).resolve().parents[2]
DATA_VERSION='DATA-2026-W39'; SOFTWARE_VERSION='1.1.0'
MEMBERSHIP_SOURCE='SRC-INDEX-CONSTITUTION-SECONDARY'
SECONDARY_URL='https://github.com/unliftedq/index-constitution/blob/main/history/csi300.csv'
EVIDENCE_URL='https://github.com/unliftedq/index-constitution/blob/main/README.md'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,d): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    members=load(ROOT/'data/standardized/index/index_constituent_history.json')
    by_ticker={m['ticker']:m for m in members}
    raw=ROOT/'data/raw/inbox/market/CSI300_membership_secondary_2021-01-29.csv'
    sha=hashlib.sha256(raw.read_bytes()).hexdigest()

    # These are index-level rebalance events explicitly documented by dated evidence.
    # We do NOT infer per-security effective dates from them.
    events=[
      event_dict(event_id='CSI300-REBAL-2020-12-14',index_id='CN-CS300',security_id=None,listing_id=None,event_date='2020-12-14',effective_from=None,effective_to=None,event_type='REBALANCE',source_id=MEMBERSHIP_SOURCE,source_origin='SECONDARY',evidence_type='SECONDARY_EVENT',notes='Secondary archive states the 2020-12-14 CSI300 rebalance changed 26 constituents; individual full add/remove list is not reproduced here.'),
      event_dict(event_id='CSI300-REBAL-2021-06-11',index_id='CN-CS300',security_id=None,listing_id=None,event_date='2021-06-11',effective_from=None,effective_to=None,event_type='REBALANCE',source_id='SRC-CSI-ADJUSTMENT-SECONDARY-2021-06-11',source_origin='SECONDARY',evidence_type='SECONDARY_EVENT',notes='Secondary report citing SSE/CSI says the CSI300 rebalance became effective after the June 11 close and replaced 25 constituents; per-security effective timestamps are not established.'),
    ]
    # Explicit named examples from the June 2021 evidence. They are stored as ADD/REMOVE
    # events but effective_from remains unresolved; this is intentionally not enough to
    # reconstruct a complete snapshot.
    named_add=[('300274','阳光电源'),('600143','金发科技'),('688126','沪硅产业-U')]
    named_remove=[('000627','天茂集团'),('000723','美锦能源'),('600390','五矿资本')]
    for ticker,name in named_add:
        m=by_ticker.get(ticker)
        events.append(event_dict(event_id=f'CSI300-ADD-2021-06-11-{ticker}',index_id='CN-CS300',security_id=m['security_id'] if m else None,listing_id=m['listing_id'] if m else None,event_date='2021-06-11',effective_from=None,effective_to=None,event_type='ADD',source_id='SRC-CSI-ADJUSTMENT-SECONDARY-2021-06-11',source_origin='SECONDARY',evidence_type='SECONDARY_EVENT',notes=f'Named by secondary report as a June 2021 CSI300 addition ({name}); exact effective_from not independently established in W02.'))
    for ticker,name in named_remove:
        m=by_ticker.get(ticker)
        events.append(event_dict(event_id=f'CSI300-REMOVE-2021-06-11-{ticker}',index_id='CN-CS300',security_id=m['security_id'] if m else None,listing_id=m['listing_id'] if m else None,event_date='2021-06-11',effective_from=None,effective_to=None,event_type='REMOVE',source_id='SRC-CSI-ADJUSTMENT-SECONDARY-2021-06-11',source_origin='SECONDARY',evidence_type='SECONDARY_EVENT',notes=f'Named by secondary report as a June 2021 CSI300 removal ({name}); exact effective_to not independently established in W02.'))

    # 300274 has a concrete opt-in date in the secondary history archive: 2021-06-15.
    # We retain it as source-declared membership history, not as a same-day event inferred
    # from price existence. It is useful for explaining V1.0's 2021-01-29 OUT_OF_INDEX row.
    m=by_ticker.get('300274')
    if m:
        events.append(event_dict(event_id='CSI300-ADD-SOURCE-DECLARED-2021-06-15-300274',index_id='CN-CS300',security_id=m['security_id'],listing_id=m['listing_id'],event_date=None,effective_from='2021-06-15',effective_to=None,event_type='ADD',source_id=MEMBERSHIP_SOURCE,source_origin='SECONDARY',evidence_type='SECONDARY_EVENT',effective_date_status='SOURCE_DECLARED',notes='The secondary history CSV declares opt-in=2021-06-15 for 300274.SZ; event_date is left null because the archive does not establish the announcement/implementation event date separately.'))

    dump(ROOT/'data/standardized/index/index_constituent_event.json',{
      'dataset':'index_constituent_event','schema_version':'index_constituent_event.v1','index_id':'CN-CS300','records':events,'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,
      'source_summary':{'secondary_source':MEMBERSHIP_SOURCE,'secondary_url':SECONDARY_URL,'evidence_url':EVIDENCE_URL,'license_gate':'REVIEW'},
      'limitations':['No official CSI historical event file was directly retrieved.','Only explicitly documented named events are materialized; unresolved per-security effective dates remain null.','The secondary archive is not treated as official provenance.']
    })

    dump(ROOT/'reports/quality/csi300_membership_evidence/2021-01-29.json',{
      'observation_date':'2021-01-29','source_id':MEMBERSHIP_SOURCE,'source_origin':'SECONDARY','source_url':SECONDARY_URL,
      'evidence_type':'SECONDARY_SNAPSHOT','retrieval_status':'RETRIEVED','license_gate':'REVIEW','raw_file_sha256':sha,
      'member_count':len(members),'official_evidence_status':'NOT_ESTABLISHED','data_quality_status':'SOURCE_CONFIRMED_SECONDARY','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,
      'notes':'The archive README attributes CSI300 history to official CSI announcements, but W02 did not retrieve the underlying CSI files directly; therefore source_origin remains SECONDARY.'
    })
    dump(ROOT/'reports/quality/csi300_membership_evidence/2021-06-11.json',{
      'observation_date':'2021-06-11','source_id':'SRC-CSI-ADJUSTMENT-SECONDARY-2021-06-11','source_origin':'SECONDARY',
      'source_url':'https://static.cdsb.com/micropub/Articles/202106/388496c86f773fd481b83675dc126455.html','evidence_type':'SECONDARY_EVENT','retrieval_status':'RETRIEVED','license_gate':'REVIEW',
      'reported_add_count':25,'reported_remove_count':25,'per_security_full_list_available_to_W02':False,'data_quality_status':'PARTIAL','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })

    # Snapshot remains separate from event ledger.
    snapshot={'index_id':'CN-CS300','observation_date':'2021-01-29','constituent_count':len(members),'members':members,
      'source_summary':{'primary_source_id':MEMBERSHIP_SOURCE,'source_origin':'SECONDARY','evidence_type':'SECONDARY_SNAPSHOT'},
      'quality_summary':{'membership_quality':'SOURCE_CONFIRMED_SECONDARY','official_verified':False,'event_reconstruction_complete':False},
      'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION}
    dump(ROOT/'data/history/by_observation_date/2021/01/CSI300__membership__2021-01-29.json',snapshot)

    # Event summary/reconciliation.
    dump(ROOT/'reports/quality/csi300_membership_reconciliation/2021-06-11.json',{
      'observation_date':'2021-06-11','official_only':0,'secondary_only':50,'both_same':0,'both_different':0,'unknown':0,
      'secondary_event_add_reported':25,'secondary_event_remove_reported':25,'security_level_reconciled':False,
      'official_source':'SRC-CSI-OFFICIAL','secondary_source':'SRC-CSI-ADJUSTMENT-SECONDARY-2021-06-11','status':'OFFICIAL_NOT_ESTABLISHED','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })
    dump(ROOT/'reports/quality/csi300_membership_event_summary.json',{
      'event_records':len(events),'ADD':sum(e['event_type']=='ADD' for e in events),'REMOVE':sum(e['event_type']=='REMOVE' for e in events),
      'WEIGHT_CHANGE':0,'RANK_CHANGE':0,'REBALANCE':sum(e['event_type']=='REBALANCE' for e in events),'UNKNOWN':0,
      'reported_unmaterialized_add_events':25-2,'reported_unmaterialized_remove_events':25-3,
      'event_reconstruction_status':'PARTIAL','official_event_source':'NOT_ESTABLISHED','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })
    print(json.dumps({'events':len(events),'add':sum(e['event_type']=='ADD' for e in events),'remove':sum(e['event_type']=='REMOVE' for e in events),'rebalance':sum(e['event_type']=='REBALANCE' for e in events),'status':'PARTIAL'}))
if __name__=='__main__': main()
