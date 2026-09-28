from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    inbox=ROOT/'data/raw/inbox/official'
    files=[p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in {'.xls','.xlsx'}] if inbox.exists() else []
    if files:
        p=subprocess.run([sys.executable,str(ROOT/'scripts/ingest_official.py'),str(sorted(files)[0])],capture_output=True,text=True)
        print('OFFICIAL INGEST =', 'SUCCESS' if p.returncode==0 and 'PUBLISHED' in p.stdout else 'FAILED')
        print(p.stdout)
    else:
        print('OFFICIAL INGEST = NOT_PRESENT')
    market_inbox=ROOT/'data/raw/inbox/market'
    market_files=[p for p in market_inbox.iterdir() if p.is_file() and p.suffix.lower() in {'.csv','.xls','.xlsx','.json'}] if market_inbox.exists() else []
    if market_files:
        mp=subprocess.run([sys.executable,str(ROOT/'scripts/ingest_market_data.py'),str(sorted(market_files)[0])],capture_output=True,text=True)
        print('MANUAL MARKET INGEST =', 'SUCCESS' if mp.returncode==0 else 'FAILED')
        print(mp.stdout)
    else:
        print('MANUAL MARKET INGEST = NOT_PRESENT')
    v=subprocess.run([sys.executable,str(ROOT/'scripts/validate/validate_csi300.py')],capture_output=True,text=True)
    print(v.stdout.strip())
    t=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True)
    print(t.stdout.strip())
    # Network access is allowed to fail without failing the entire pipeline.
    print('PIPELINE OK' if v.returncode==0 and t.returncode==0 else 'PIPELINE FAILED')
    return 0 if v.returncode==0 and t.returncode==0 else 1
if __name__=='__main__': raise SystemExit(main())
