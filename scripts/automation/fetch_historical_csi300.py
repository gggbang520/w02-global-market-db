from __future__ import annotations
import argparse, io, json, re
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

from common import ROOT

SOURCE_ID = 'SRC-GITHUB-TUSHARE-ARCHIVE'
MEMBERSHIP_SOURCE = 'SRC-CSI300-SECONDARY'
REPO = 'shaocongWu/Multivariate_Stock_Time_Series_Dataset'
BRANCH = 'main'
MEMBERSHIP_URL = 'https://raw.githubusercontent.com/unliftedq/index-constitution/main/history/csi300.csv'

def stem_code(stem):
    s = re.sub(r'[^0-9]', '', str(stem).upper())
    return s.zfill(6) if s else None

def exchange_from_symbol(symbol):
    s = str(symbol).upper()
    if s.startswith('SZ'): return 'XSHE'
    if s.startswith('SH'): return 'XSHG'
    return None

def load_membership(start, end):
    r = requests.get(MEMBERSHIP_URL, timeout=45)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    df.columns = [str(c).strip().lower() for c in df.columns]
    df['opt-in'] = pd.to_datetime(df['opt-in'], errors='coerce')
    df['opt-out'] = pd.to_datetime(df['opt-out'], errors='coerce')
    start_ts = pd.Timestamp(start); end_ts = pd.Timestamp(end)
    active = df[(df['opt-in'] <= end_ts) & (df['opt-out'].isna() | (df['opt-out'] >= start_ts))].copy()
    active['ticker'] = active['symbol'].map(stem_code)
    active['exchange'] = active['symbol'].map(exchange_from_symbol)
    active = active.dropna(subset=['ticker','exchange']).drop_duplicates(['exchange','ticker'])
    return df, active

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', required=True)
    ap.add_argument('--end', required=True)
    args = ap.parse_args()
    membership, active = load_membership(args.start, args.end)
    wanted_by_code = {r.ticker: r for r in active.itertuples()}

    tree_url = f'https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1'
    tree = requests.get(tree_url, timeout=45, headers={'Accept':'application/vnd.github+json'})
    tree.raise_for_status()
    files = {}
    for item in tree.json().get('tree', []):
        p = item.get('path','')
        if p.lower().endswith('.csv'):
            code = stem_code(Path(p).stem)
            if code in wanted_by_code and code not in files:
                files[code] = p

    rows=[]; failures=[]
    for code, path in sorted(files.items()):
        meta = wanted_by_code[code]
        url = f'https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}'
        try:
            rr=requests.get(url,timeout=45); rr.raise_for_status()
            df=pd.read_csv(io.BytesIO(rr.content))
            cols={str(c).strip().lower():c for c in df.columns}
            def pick(*names):
                for n in names:
                    if n in cols: return cols[n]
                return None
            dcol=pick('date','trade_date','datetime'); ccol=pick('close')
            if not dcol or not ccol: raise ValueError('date/close columns not found')
            df[dcol]=pd.to_datetime(df[dcol],errors='coerce')
            df=df[df[dcol].notna()].copy()
            df['trade_date']=df[dcol].dt.date.astype(str)
            df=df[(df['trade_date']>=args.start)&(df['trade_date']<=args.end)]
            rows.append(pd.DataFrame({
                'ticker':code,'exchange':meta.exchange,'trade_date':df['trade_date'],
                'open':pd.to_numeric(df[pick('open')],errors='coerce') if pick('open') else None,
                'high':pd.to_numeric(df[pick('high')],errors='coerce') if pick('high') else None,
                'low':pd.to_numeric(df[pick('low')],errors='coerce') if pick('low') else None,
                'close':pd.to_numeric(df[ccol],errors='coerce'),
                'adjusted_close':None,'price_type':'RAW_CLOSE',
                'volume':pd.to_numeric(df[pick('volume','vol')],errors='coerce') if pick('volume','vol') else None,
                'turnover':pd.to_numeric(df[pick('turnover','amount','amt')],errors='coerce') if pick('turnover','amount','amt') else None,
                'currency':'CNY'}))
        except Exception as e:
            failures.append({'ticker':code,'exchange':meta.exchange,'path':path,'error':str(e)})

    out=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
    if not out.empty:
        out=out.drop_duplicates(['ticker','exchange','trade_date']).sort_values(['trade_date','exchange','ticker'])

    raw_dir=ROOT/'data/raw/inbox/market'; raw_dir.mkdir(parents=True,exist_ok=True)
    meta_dir=ROOT/'data/raw/_metadata'; meta_dir.mkdir(parents=True,exist_ok=True)
    membership_dir=ROOT/'data/raw/cn'; membership_dir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    membership_file=membership_dir/f'{MEMBERSHIP_SOURCE}__index_constituents__CN__{args.start}_{args.end}__{stamp}.csv'
    membership.to_csv(membership_file,index=False,encoding='utf-8-sig')
    out_file=raw_dir/f'{SOURCE_ID}__stock_daily__CN__HISTORICAL_CSI300__{args.start}_{args.end}__{stamp}.csv'
    out.to_csv(out_file,index=False,encoding='utf-8')
    report={
        'source_id':SOURCE_ID,'source_origin':'AUTO_PROVIDER','declared_upstream_source':'Tushare Pro',
        'verification_status':'SOURCE_DECLARED_NOT_DIRECTLY_RETRIEVED','historical_universe_source':MEMBERSHIP_SOURCE,
        'historical_universe_url':MEMBERSHIP_URL,'repository':f'https://github.com/{REPO}',
        'dataset':'STOCK_DAILY','market':'CN','start_date':args.start,'end_date':args.end,
        'historical_membership_overlap_codes':len(active),'matched_csv_files':len(files),
        'downloaded_rows':int(len(out)),'distinct_listings':int(out['ticker'].nunique()) if not out.empty else 0,
        'distinct_trade_dates':int(out['trade_date'].nunique()) if not out.empty else 0,'failures':failures,
        'membership_file':str(membership_file.relative_to(ROOT)),'output_file':str(out_file.relative_to(ROOT)),
        'license_gate':'REVIEW','publication_scope':'INTERNAL_SNAPSHOT_ONLY','retrieved_at':datetime.now(timezone.utc).isoformat()}
    (meta_dir/(out_file.stem+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': raise SystemExit(main())