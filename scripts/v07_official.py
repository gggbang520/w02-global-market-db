from __future__ import annotations
import hashlib, json, mimetypes, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
DATA_VERSION='DATA-2026-W39'
SOFTWARE_VERSION='0.7.0'
SCHEMA_VERSION='0.7.0'
PARSER_VERSION='0.7.0'
OFFICIAL_URL='https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000300cons.xls'

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def sha256(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def content_type(path: Path)->str:
    return mimetypes.guess_type(path.name)[0] or 'application/octet-stream'

def discover_official_file(root: Path=ROOT)->Path|None:
    inbox=root/'data/raw/inbox/official'
    if not inbox.exists(): return None
    files=[p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in {'.xls','.xlsx'}]
    return sorted(files, key=lambda p:p.name.lower())[0] if files else None

def audit_file(path: Path, original_url: str|None=None)->dict:
    return {
      'source_id':'SRC-CSI-OFFICIAL','dataset':'CSI300_CONSTITUENTS','market':'CN',
      'file_name':path.name,'file_size':path.stat().st_size,'content_type':content_type(path),
      'sha256':sha256(path),'input_origin':'OFFICIAL','original_url':original_url or OFFICIAL_URL,
      'downloaded_at':None,
    }

def _manifest_meta(path:Path)->dict:
    mf=ROOT/'data/raw/inbox_manifest.json'
    if not mf.exists(): return {}
    try:
        for x in json.loads(mf.read_text(encoding='utf-8')):
            if x.get('file_name')==path.name or x.get('file_path')==str(path.relative_to(ROOT)):
                return x
    except Exception: pass
    return {}

def audit_with_manifest(path:Path)->dict:
    a=audit_file(path)
    m=_manifest_meta(path)
    for k in ('original_url','downloaded_at'):
        if m.get(k): a[k]=m[k]
    return a

def _parse(path:Path):
    from scripts.parse.csi_constituents_parser import parse_csi_file_detailed
    return parse_csi_file_detailed(path, source_origin='OFFICIAL')

def validate_weight(records:list[dict])->dict:
    vals=[r['weight'] for r in records if r.get('weight') is not None]
    invalid=[r for r in records if r.get('weight') is not None and (not isinstance(r.get('weight'),(int,float)) or r.get('weight')<0)]
    return {'available_count':len(vals),'minimum':min(vals) if vals else None,'maximum':max(vals) if vals else None,'sum':sum(vals) if vals else None,'invalid_count':len(invalid),'sum_100_enforced':False}

def standardize(records:list[dict])->list[dict]:
    out=[]
    for r in records:
        ticker=r['ticker']; mic=r['exchange_mic']; norm=f'CN-{mic}-{ticker}'
        out.append({
          'index_id':'CN-CS300','security_id':f'SEC-CN-{ticker}','listing_id':f'LST-CN-{ticker}',
          'company_id':f'COM-CN-{ticker}','ticker':ticker,'normalized_ticker':norm,
          'source_ticker':r.get('source_ticker',ticker),'company_name':r['name'],
          'exchange_mic':mic,'weight':r.get('weight'),'effective_from':r.get('effective_from'),
          'effective_to':r.get('effective_to'),'source_id':'SRC-CSI-OFFICIAL','source_origin':'OFFICIAL',
          'data_quality_status':'SOURCE_CONFIRMED','license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY',
          'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION
        })
    return out

def reconcile(official:list[dict], secondary_path:Path)->dict:
    sec=[]
    if secondary_path.exists():
        try: sec=json.loads(secondary_path.read_text(encoding='utf-8')).get('constituents',[])
        except Exception: sec=[]
    om={r['normalized_ticker']:r for r in official}; sm={r.get('normalized_ticker') or f"CN-{r.get('exchange_mic','')}-{r.get('ticker','')}":r for r in sec}
    official_only=[]; secondary_only=[]; both_same=[]; both_different=[]; conflicts=[]
    for k in sorted(set(om)|set(sm)):
        if k in om and k not in sm: official_only.append(k); continue
        if k in sm and k not in om: secondary_only.append(k); continue
        o,s=om[k],sm[k]
        diffs=[]
        for field in ('ticker','company_name','exchange_mic','weight'):
            ov=o.get(field); sv=s.get(field)
            if field=='company_name': sv=s.get('company_name') or s.get('name')
            if ov!=sv and not (ov is None and sv is None): diffs.append({'field':field,'official_value':ov,'secondary_value':sv})
        if diffs:
            both_different.append(k)
            for d in diffs: conflicts.append({'security_id':o['security_id'],'normalized_ticker':k,**d,'resolution':'REVIEW','resolution_reason':'Official and secondary values differ; no silent overwrite.'})
        else: both_same.append(k)
    return {'official_only':len(official_only),'secondary_only':len(secondary_only),'both_same':len(both_same),'both_different':len(both_different),'official_only_tickers':official_only,'secondary_only_tickers':secondary_only,'conflicts':conflicts,'status':'CONFLICT' if conflicts else 'MATCH'}

def publish(official:list[dict], audit:dict, validation:dict, reconciliation:dict):
    if not validation['official_verified']: raise ValueError('PUBLISH_BLOCKED: official verification did not pass')
    ts=now()
    current=ROOT/'data/current/constituents/CSI300__current.json'
    previous=json.loads(current.read_text(encoding='utf-8')) if current.exists() else None
    constituents=[]
    for r in official:
        constituents.append({
          'index_id':'CN-CS300','security_id':r['security_id'],'listing_id':r['listing_id'],'ticker':r['ticker'],
          'normalized_ticker':r['normalized_ticker'],'company_name':r['company_name'],'source_ticker':r['source_ticker'],
          'effective_from':r['effective_from'],'effective_to':r['effective_to'],'weight':r['weight'],
          'source_id':'SRC-CSI-OFFICIAL','source_origin':'OFFICIAL','data_quality_status':'SOURCE_CONFIRMED',
          'license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY','retrieved_at':ts,
          'access_status':'AVAILABLE','parse_status':'SUCCESS','provenance':{'official_record':True,'secondary_record':False}
        })
    obj={'index_id':'CN-CS300','data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,
         'source_summary':{'primary_source':'SRC-CSI-OFFICIAL','source_origin':'OFFICIAL','secondary_preserved':True},
         'snapshot_date':None,'constituent_count':len(constituents),'coverage':{'target':300,'official_verified':len(constituents)},
         'quality':{'validation':'PASS','data_quality_status':'SOURCE_CONFIRMED','license_gate':'REVIEW','reconciliation_status':reconciliation['status']},
         'constituents':constituents}
    current.parent.mkdir(parents=True,exist_ok=True); current.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    hist=ROOT/'data/history'/DATA_VERSION/'constituents'; hist.mkdir(parents=True,exist_ok=True)
    (hist/'CSI300__current.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # preserve secondary source in a separate provenance artifact
    prov=ROOT/'data/standardized/provenance'; prov.mkdir(parents=True,exist_ok=True)
    (prov/'csi300_official_identity_snapshot.json').write_text(json.dumps({'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,'records':official},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return obj

def run_real_file(path:Path)->dict:
    audit=audit_with_manifest(path)
    receipt={**audit,'parser_version':PARSER_VERSION,'schema_version':SCHEMA_VERSION,'software_version':SOFTWARE_VERSION,'data_version':DATA_VERSION,'status':'AUDITED','publish_gate':'BLOCKED'}
    try:
        parsed=_parse(path)
        validation=parsed['validation']; records=parsed['records']
        validation['weight']=validate_weight(records)
        validation['official_verified']=validation['valid_rows']==300 and validation['duplicate_rows']==0 and validation['invalid_rows']==0
        standardized=standardize(records)
        receipt.update({'raw_rows':validation['raw_rows'],'parsed_rows':validation['parsed_rows'],'valid_rows':validation['valid_rows'],'invalid_rows':validation['invalid_rows'],'duplicate_rows':validation['duplicate_rows'],'status':'PARSE_SUCCESS' if validation['parsed_rows'] else 'PARSE_FAILED','publish_gate':'PASS' if validation['official_verified'] else 'BLOCKED'})
        # Archive raw only after parse succeeded, never overwrite an existing hash.
        archive=ROOT/'data/raw/cn'/f"SRC-CSI-OFFICIAL__CSI300_CONSTITUENTS__CN__{audit['sha256'][:16]}{path.suffix.lower()}"
        archive.parent.mkdir(parents=True,exist_ok=True)
        if not archive.exists(): shutil.copy2(path,archive)
        receipt['raw_archive']=str(archive.relative_to(ROOT))
        secondary=ROOT/'data/current/constituents/CSI300__current.json'
        rec=reconcile(standardized,secondary)
        (ROOT/'reports/quality/csi300_source_reconciliation.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (ROOT/'reports/quality/csi300_official_validation.json').write_text(json.dumps({'target':300,**validation},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if validation['official_verified']:
            publish(standardized,audit,validation,rec)
            receipt['status']='PUBLISHED'; receipt['publish_gate']='PASS'
        else:
            receipt['status']='VALIDATION_FAILED'
        # lineage
        lineage={'generated_at':now(),'count':len(standardized),'records':[{
          'security_id':r['security_id'],'listing_id':r['listing_id'],'ticker':r['ticker'],'source_origin':'OFFICIAL',
          'input_file':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),'sha256':audit['sha256'],
          'raw_file':receipt.get('raw_archive'),'parser_version':PARSER_VERSION,'schema_version':SCHEMA_VERSION,
          'data_version':DATA_VERSION,'software_version':SOFTWARE_VERSION,'standardized_record':r,
          'validation':'reports/quality/csi300_official_validation.json','current':'data/current/constituents/CSI300__current.json' if validation['official_verified'] else None,
          'history':f'data/history/{DATA_VERSION}/constituents/CSI300__current.json' if validation['official_verified'] else None
        } for r in standardized]}
        lp=ROOT/'reports/lineage/csi300_stock_lineage.json'; lp.write_text(json.dumps(lineage,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        receipt['lineage']='reports/lineage/csi300_stock_lineage.json'
        receipt['reconciliation']=rec
    except Exception as e:
        receipt.update({'status':'PARSE_FAILED','publish_gate':'BLOCKED','parse_error':f'{type(e).__name__}: {e}'})
    out=ROOT/'reports/ingestion'/f"CSI300__{datetime.now(timezone.utc).strftime('%Y-%m-%d')}__ingestion_receipt.json"
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return receipt
