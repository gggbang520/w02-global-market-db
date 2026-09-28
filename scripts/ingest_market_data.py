from __future__ import annotations
import csv, hashlib, json, sys
from datetime import datetime, timezone, date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from scripts.providers.manual_file import ManualFileProvider, SUPPORTED

def sha256(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def resolve_listing(records):
 lm={}
 p=ROOT/'data/standardized/listing_master.json'
 if p.exists():
  for r in json.loads(p.read_text()): lm[(r['ticker'],r['exchange_mic'])]=r
 out=[]
 for r in records:
  x=lm.get((r['ticker'],r['exchange_mic']))
  if x:
   r['listing_id']=x['listing_id']; r['security_id']=x['security_id']; r['currency']=r.get('currency') or x.get('currency')
   r['identity_status']='MAPPED'
  else: r['identity_status']='REVIEW'
  out.append(r)
 return out

def validate(records, retrieved_date=None):
 retrieved_date=retrieved_date or date.today().isoformat(); seen=set(); valid=[]; invalid=[]; dup=[]; review=[]
 for r in records:
  errs=[]; key=(r.get('listing_id'),r.get('trade_date'),r.get('source_id'),r.get('price_type'))
  if key in seen: dup.append(r); continue
  seen.add(key)
  if not r.get('listing_id') or not r.get('security_id'): errs.append('IDENTITY_UNMAPPED')
  if not r.get('exchange_mic'): errs.append('EXCHANGE_MISSING')
  try: d=date.fromisoformat(str(r.get('trade_date')))
  except: errs.append('INVALID_TRADE_DATE'); d=None
  if d and str(d)>retrieved_date: errs.append('FUTURE_TRADE_DATE')
  vals=[r.get(k) for k in ('open','high','low','close')]
  if any(v is None for v in vals): errs.append('OHLC_MISSING')
  else:
   o,h,l,c=vals
   if not (h>=l and h>=o and h>=c and l<=o and l<=c and c>=0): errs.append('OHLC_INVALID')
  if r.get('volume') is not None and r['volume']<0: errs.append('VOLUME_INVALID')
  if r.get('turnover') is not None and r['turnover']<0: errs.append('TURNOVER_INVALID')
  if errs:
   (review if 'IDENTITY_UNMAPPED' in errs or 'FUTURE_TRADE_DATE' in errs else invalid).append({**r,'validation_errors':errs})
  else: valid.append({**r,'data_quality_status':'SOURCE_CONFIRMED','license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY'})
 return {'valid':valid,'invalid':invalid,'duplicate':dup,'review':review}

def main():
 if len(sys.argv)<2: print('usage: python scripts/ingest_market_data.py <file>'); return 2
 p=Path(sys.argv[1]);
 if not p.exists() or p.suffix.lower() not in SUPPORTED: print('MARKET INGEST = FAILED: unsupported/missing file'); return 2
 provider=ManualFileProvider(p); raw=provider.parse(p); norm=resolve_listing(provider.normalize(raw)); result=validate(norm)
 digest=sha256(p); now=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
 dates=[r['trade_date'] for r in result['valid'] if r.get('trade_date')]
 receipt={'source_id':provider.source_id,'input_file':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'sha256':digest,'input_size':p.stat().st_size,'input_origin':'MANUAL','dataset':'stock_daily','trade_date_min':min(dates) if dates else None,'trade_date_max':max(dates) if dates else None,'raw_rows':len(raw),'parsed_rows':len(norm),'valid_rows':len(result['valid']),'invalid_rows':len(result['invalid']),'duplicate_rows':len(result['duplicate']),'review_rows':len(result['review']),'publish_gate':'PASS' if result['valid'] and not result['invalid'] and not result['duplicate'] else 'BLOCKED','status':'SUCCESS' if result['valid'] and not result['invalid'] and not result['duplicate'] else 'FAILED','retrieved_at':now}
 outdir=ROOT/'reports/ingestion'; outdir.mkdir(parents=True,exist_ok=True)
 outdir.joinpath(f"STOCK_DAILY__{dates[0] if dates else 'UNKNOWN'}__receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 if result['valid']:
  rawdir=ROOT/'data/raw/inbox/market'; rawdir.mkdir(parents=True,exist_ok=True)
  archive=rawdir/(f"{provider.source_id}__stock_daily__{dates[-1] if dates else 'UNKNOWN'}__{digest[:12]}{p.suffix.lower()}")
  if not archive.exists(): archive.write_bytes(p.read_bytes())
  std=ROOT/'data/standardized/stocks'; std.mkdir(parents=True,exist_ok=True)
  for r in result['valid']:
   fn=std/f"{r['listing_id']}__{r['trade_date']}__{r['source_id']}.json"; fn.write_text(json.dumps(r,ensure_ascii=False,indent=2))
 print('MARKET INGEST =',receipt['status']); print(json.dumps(receipt,ensure_ascii=False,indent=2)); return 0 if receipt['status']=='SUCCESS' else 1
if __name__=='__main__': raise SystemExit(main())
