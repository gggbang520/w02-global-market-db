from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
DATA_VERSION = 'DATA-2026-W39'
SOFTWARE_VERSION = '1.3.0'
ARCHIVE_SOURCE = 'SRC-INDEX-CONSTITUTION-SECONDARY'
SECONDARY_2020 = 'SRC-CSI-ADJUSTMENT-SECONDARY-2020-12-14'
SECONDARY_2021 = 'SRC-CSI-ADJUSTMENT-SECONDARY-2021-06-11'

OUT_2020 = ['SZ000709','SZ002466','SZ002468','SH600038','SH600089','SH600170','SH600188','SH600219','SH600221','SH600372','SH600398','SH600516','SH600583','SH600674','SH600867','SH600928','SH600968','SH600977','SH601018','SH601212','SH601298','SH601828','SH601898','SH601992','SH601997','SH603260']
IN_2020 = ['SZ002049','SZ002384','SZ002414','SZ002600','SZ002812','SZ002821','SZ300529','SZ300676','SH600150','SH600161','SH600584','SH600600','SH600763','SH600845','SH600872','SH600918','SH601696','SH601872','SH601990','SH603087','SH603195','SH603392','SH688008','SH688009','SH688012','SH688036']
OUT_2021 = ['SZ000627','SZ000671','SZ000723','SZ000961','SZ002146','SZ002422','SZ002958','SH600004','SH600027','SH600066','SH600068','SH600177','SH600208','SH600271','SH600297','SH600369','SH600390','SH600487','SH600498','SH600637','SH600998','SH601117','SH601198','SH601577','SH603156']
IN_2021 = ['SZ000800','SZ300274','SZ300450','SZ300558','SZ300595','SZ300677','SH600079','SH600132','SH600143','SH600426','SH600521','SH601799','SH601995','SH603233','SH603338','SH603517','SH603659','SH603806','SH603882','SH603939','SH688111','SH688126','SH688169','SH688363','SH688396']

SOURCE_CLASS = {
    'OFFICIAL_PRIMARY','OFFICIAL_MIRROR','SECONDARY_REPRODUCTION','SECONDARY_ARCHIVE','REFERENCE'
}
EVENT_STATUS = {'CONFIRMED','SOURCE_DECLARED','INFERRED','UNKNOWN'}


def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


def identity(ticker):
    code = ticker[2:]
    return f'SEC-CN-{code}', f'LST-CN-{code}', ('XSHG' if ticker.startswith('SH') else 'XSHE')


def event(event_id, ticker, event_type, event_date, effective_from=None, effective_to=None, source_id=ARCHIVE_SOURCE, source_origin='SECONDARY_ARCHIVE', evidence_id=None, status='CONFIRMED', notes=''):
    sec, listing, mic = identity(ticker)
    return {
        'event_id': event_id, 'index_id':'CN-CS300', 'security_id':sec, 'listing_id':listing,
        'ticker':ticker[2:], 'exchange_mic':mic, 'event_date':event_date,
        'effective_from':effective_from, 'effective_to':effective_to, 'event_type':event_type,
        'old_weight':None, 'new_weight':None, 'old_rank':None, 'new_rank':None,
        'source_id':source_id, 'source_origin':source_origin, 'evidence_id':evidence_id,
        'evidence_event_status':status, 'data_quality_status':'SOURCE_CONFIRMED_SECONDARY',
        'license_gate':'REVIEW', 'evidence_type':'SECONDARY_EVENT',
        'effective_date_status': 'SOURCE_DECLARED' if effective_from or effective_to else 'NOT_ESTABLISHED',
        'notes':notes,
    }


def build():
    # Exact security-level lists are taken from the secondary history archive.
    # The archive README declares CSI official announcements as upstream; W02 did not
    # retrieve the underlying CSI documents directly, so these remain secondary evidence.
    events=[]
    for t in OUT_2020:
        events.append(event(f'CSI300-REMOVE-2020-12-14-{t[2:]}',t,'REMOVE','2020-12-14',effective_to='2020-12-14',source_id=ARCHIVE_SOURCE,evidence_id='EVID-CSI300-2020-12-14-SECONDARY',notes='Exact security appears with opt-out=2020-12-14 in the secondary CSI300 history archive.'))
    for t in IN_2020:
        events.append(event(f'CSI300-ADD-2020-12-14-{t[2:]}',t,'ADD','2020-12-14',effective_from='2020-12-14',source_id=ARCHIVE_SOURCE,evidence_id='EVID-CSI300-2020-12-14-SECONDARY',notes='Exact security appears with opt-in=2020-12-14 in the secondary CSI300 history archive.'))
    # Source says the 2021 adjustment took effect after the 2021-06-11 close. 2021-06-14
    # was a market holiday, so the first trading-day membership boundary is 2021-06-15.
    for t in OUT_2021:
        events.append(event(f'CSI300-REMOVE-2021-06-11-{t[2:]}',t,'REMOVE','2021-06-11',effective_to='2021-06-15',source_id=SECONDARY_2021,source_origin='SECONDARY_REPRODUCTION',evidence_id='EVID-CSI300-2021-06-11-SECONDARY',notes='Exact security appears in the reproduced June 2021 adjustment list; source states the change takes effect after the June 11 close. Effective membership boundary is 2021-06-15 because June 14 was a market holiday.'))
    for t in IN_2021:
        events.append(event(f'CSI300-ADD-2021-06-11-{t[2:]}',t,'ADD','2021-06-11',effective_from='2021-06-15',source_id=SECONDARY_2021,source_origin='SECONDARY_REPRODUCTION',evidence_id='EVID-CSI300-2021-06-11-SECONDARY',notes='Exact security appears in the reproduced June 2021 adjustment list; source states the change takes effect after the June 11 close. Effective membership boundary is 2021-06-15 because June 14 was a market holiday.'))
    # Keep index-level rebalance events as separate evidence events; do not collapse them into adds/removes.
    events += [
      {'event_id':'CSI300-REBAL-2020-12-14','index_id':'CN-CS300','security_id':None,'listing_id':None,'ticker':None,'exchange_mic':None,'event_date':'2020-12-14','effective_from':None,'effective_to':None,'event_type':'REBALANCE','old_weight':None,'new_weight':None,'old_rank':None,'new_rank':None,'source_id':ARCHIVE_SOURCE,'source_origin':'SECONDARY_ARCHIVE','evidence_id':'EVID-CSI300-2020-12-14-SECONDARY','evidence_event_status':'CONFIRMED','data_quality_status':'SOURCE_CONFIRMED_SECONDARY','license_gate':'REVIEW','evidence_type':'SECONDARY_EVENT','effective_date_status':'NOT_ESTABLISHED','notes':'Index-level rebalance evidence: 26 replacements reported. Full security-level list is materialized separately from the same secondary archive.'},
      {'event_id':'CSI300-REBAL-2021-06-11','index_id':'CN-CS300','security_id':None,'listing_id':None,'ticker':None,'exchange_mic':None,'event_date':'2021-06-11','effective_from':None,'effective_to':None,'event_type':'REBALANCE','old_weight':None,'new_weight':None,'old_rank':None,'new_rank':None,'source_id':SECONDARY_2021,'source_origin':'SECONDARY_REPRODUCTION','evidence_id':'EVID-CSI300-2021-06-11-SECONDARY','evidence_event_status':'CONFIRMED','data_quality_status':'SOURCE_CONFIRMED_SECONDARY','license_gate':'REVIEW','evidence_type':'SECONDARY_EVENT','effective_date_status':'NOT_ESTABLISHED','notes':'Index-level rebalance evidence: 25 replacements reported; full security-level list is materialized separately from the reproduced list.'}
    ]

    dump(ROOT/'data/standardized/index/index_constituent_event.json', {
      'dataset':'index_constituent_event','schema_version':'index_constituent_event.v1.3','index_id':'CN-CS300','records':events,
      'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,
      'event_status_definition':{'CONFIRMED':'Exact security-level event is present in retrieved evidence; source is still subject to provenance class.','SOURCE_DECLARED':'Date or upstream attribution is explicitly declared by source.','INFERRED':'Derived by W02 logic and never used for unresolved membership.','UNKNOWN':'Insufficient evidence.'},
      'source_origin_classes':sorted(SOURCE_CLASS),
      'source_summary':{'secondary_archive':ARCHIVE_SOURCE,'secondary_reproduction_2020':'Sina reproduction of CSI announcement','secondary_reproduction_2021':'Longcheng reproduction of CSI announcement','official_primary_status':'NOT_ESTABLISHED','license_gate':'REVIEW'},
      'limitations':['No official CSI historical event file was directly retrieved.','The 2020 and 2021 security lists are confirmed as secondary evidence, not official primary evidence.','2021-06-15 effective boundary uses the source rule (after 2021-06-11 close) plus the exchange holiday calendar; this is explicitly recorded in notes.']
    })

    evidence_dir=ROOT/'reports/quality/csi300_membership_evidence'
    raw=ROOT/'data/raw/inbox/market/CSI300_membership_secondary_2021-01-29.csv'
    raw_sha=hashlib.sha256(raw.read_bytes()).hexdigest()
    dump(evidence_dir/'2020-12-14.json',{
      'evidence_id':'EVID-CSI300-2020-12-14-SECONDARY','event_date':'2020-12-14','effective_date':'2020-12-14','index_id':'CN-CS300','source_id':ARCHIVE_SOURCE,
      'source_origin':'SECONDARY_ARCHIVE','evidence_type':'SECONDARY_EVENT_LIST','source_url':'https://github.com/unliftedq/index-constitution/blob/main/history/csi300.csv',
      'document_title':'CSI300 historical composition archive','attachment':None,'hash':None,'retrieval_date':'2026-09-27','quality_status':'SOURCE_CONFIRMED_SECONDARY','license_gate':'REVIEW',
      'reported_replacement_count':26,'materialized_add_count':26,'materialized_remove_count':26,'event_materialization':'COMPLETE_SECONDARY','declared_upstream_source':'China Securities Index Co. official announcements','verification_status':'SOURCE_DECLARED_NOT_DIRECTLY_RETRIEVED',
      'secondary_reproduction_url':'https://finance.sina.com.cn/money/fund/fundzmt/2020-11-28/doc-iiznezxs4108904.shtml'
    })
    dump(evidence_dir/'2021-06-11.json',{
      'evidence_id':'EVID-CSI300-2021-06-11-SECONDARY','event_date':'2021-06-11','effective_date':'2021-06-15','index_id':'CN-CS300','source_id':SECONDARY_2021,
      'source_origin':'SECONDARY_REPRODUCTION','evidence_type':'SECONDARY_EVENT_LIST','source_url':'https://www.lcaj.net/jingji/080530688.html',
      'document_title':'沪深300和中证香港100等指数样本调整（名单）','attachment':None,'hash':None,'retrieval_date':'2026-09-27','quality_status':'SOURCE_CONFIRMED_SECONDARY','license_gate':'REVIEW',
      'reported_replacement_count':25,'materialized_add_count':25,'materialized_remove_count':25,'event_materialization':'COMPLETE_SECONDARY','declared_upstream_source':'China Securities Index Co. official announcement','verification_status':'SOURCE_DECLARED_NOT_DIRECTLY_RETRIEVED',
      'effective_rule':'Effective after 2021-06-11 close; 2021-06-14 was a market holiday, so membership boundary is 2021-06-15.'
    })
    dump(evidence_dir/'official_status.json',{
      'source_id':'SRC-CSI-OFFICIAL','source_origin':'OFFICIAL_PRIMARY','evidence_type':'OFFICIAL_RULE_REFERENCE','source_url':'https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/1475_931142_Index_Methodology_cn.pdf',
      'retrieval_status':'FOUND','historical_membership_snapshot_status':'NOT_ESTABLISHED','historical_event_file_status':'NOT_ESTABLISHED','license_gate':'REVIEW',
      'note':'Official CSI methodology confirms index adjustment rules but does not establish the 2020-12-14 or 2021-06-11 security-level event files used here.'
    })

    # Reconstruct secondary snapshots from the existing 2021-01-29 anchor.  These are
    # explicitly PARTIAL_SECONDARY and are never promoted to VERIFIED.
    anchor=load(ROOT/'data/history/by_observation_date/2021/01/CSI300__membership__2021-01-29.json')
    anchor_members={m['listing_id']:m for m in anchor['members']}
    def apply(anchor_state, outs, ins, effective_date):
        s=dict(anchor_state)
        for t in ins:
            _, lid, mic=identity(t); s[lid]={'index_id':'CN-CS300','security_id':identity(t)[0],'listing_id':lid,'ticker':t[2:],'exchange_mic':mic,'effective_from':effective_date,'effective_to':None,'source_id':ARCHIVE_SOURCE,'source_origin':'SECONDARY_ARCHIVE','data_quality_status':'SOURCE_CONFIRMED_SECONDARY','license_gate':'REVIEW'}
        for t in outs:
            _, lid, _=identity(t); s.pop(lid,None)
        return s
    snap2020=dict(anchor_members)
    # The secondary archive's 2020-12-14 opt-in/opt-out boundary is represented by the existing 300-member secondary anchor; no intra-day boundary is guessed.
    dump(ROOT/'data/history/by_observation_date/2020/12/CSI300__membership__2020-12-14.json',{
      'index_id':'CN-CS300','observation_date':'2020-12-14','constituent_count':len(snap2020),'members':sorted(snap2020.values(),key=lambda x:x['listing_id']),
      'source_summary':{'source_id':ARCHIVE_SOURCE,'source_origin':'SECONDARY_ARCHIVE','source_quality':'SOURCE_CONFIRMED_SECONDARY'},
      'reconstruction_version':'membership_snapshot_reconstruction.v1.2','reconstruction_status':'PARTIAL_SECONDARY','official_verified':False,'event_evidence_id':'EVID-CSI300-2020-12-14-SECONDARY','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })
    snap2021=apply(anchor_members, OUT_2021, IN_2021, '2021-06-15')
    dump(ROOT/'data/history/by_observation_date/2021/06/CSI300__membership__2021-06-15.json',{
      'index_id':'CN-CS300','observation_date':'2021-06-15','constituent_count':len(snap2021),'members':sorted(snap2021.values(),key=lambda x:x['listing_id']),
      'source_summary':{'source_id':SECONDARY_2021,'source_origin':'SECONDARY_REPRODUCTION','source_quality':'SOURCE_CONFIRMED_SECONDARY'},
      'reconstruction_version':'membership_snapshot_reconstruction.v1.2','reconstruction_status':'PARTIAL_SECONDARY','official_verified':False,'event_evidence_id':'EVID-CSI300-2021-06-11-SECONDARY','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })

    dump(ROOT/'reports/quality/csi300_membership_event_summary.json',{
      'event_records':len(events),'ADD':sum(x['event_type']=='ADD' for x in events),'REMOVE':sum(x['event_type']=='REMOVE' for x in events),'WEIGHT_CHANGE':0,'RANK_CHANGE':0,'REBALANCE':2,'UNKNOWN':0,
      'reported_add_events':51,'reported_remove_events':51,'materialized_add_events':51,'materialized_remove_events':51,'event_reconstruction_status':'PARTIAL','official_event_source':'NOT_ESTABLISHED',
      'source_security_level_status':{'2020-12-14':'COMPLETE_SECONDARY','2021-06-11':'COMPLETE_SECONDARY'},'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })
    dump(ROOT/'reports/quality/csi300_membership_reconciliation/2020-12-14.json',{
      'observation_date':'2020-12-14','official_security_level_records':0,'secondary_security_level_records':52,'official_only':0,'secondary_only':52,'both_same':0,'both_different':0,
      'official_source':'SRC-CSI-OFFICIAL','secondary_source':ARCHIVE_SOURCE,'status':'OFFICIAL_NOT_ESTABLISHED','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })
    dump(ROOT/'reports/quality/csi300_membership_reconciliation/2021-06-11.json',{
      'observation_date':'2021-06-11','official_security_level_records':0,'secondary_security_level_records':50,'official_only':0,'secondary_only':50,'both_same':0,'both_different':0,
      'official_source':'SRC-CSI-OFFICIAL','secondary_source':SECONDARY_2021,'status':'OFFICIAL_NOT_ESTABLISHED','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
    })
    print(json.dumps({'events':len(events),'add':sum(x['event_type']=='ADD' for x in events),'remove':sum(x['event_type']=='REMOVE' for x in events),'rebalance':2,'status':'PARTIAL','snapshot_2020':len(snap2020),'snapshot_2021_06_15':len(snap2021)}))

if __name__=='__main__': build()
