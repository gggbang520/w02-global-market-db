from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd, allow_fail=False):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    print(p.stdout,end=''); print(p.stderr,end='')
    if p.returncode and not allow_fail: raise SystemExit(p.returncode)
    return p
# Official/manual acquisition stage: network/file absence is a data-state, not a fake-data trigger.
inbox=ROOT/'data/raw/inbox/official'; files=[p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in {'.xls','.xlsx'}] if inbox.exists() else []
if files:
    p=run([sys.executable,'scripts/ingest_official.py',str(sorted(files)[0])],allow_fail=True); print('OFFICIAL INGEST =', 'SUCCESS' if p.returncode==0 else 'FAILED')
else: print('OFFICIAL INGEST = NOT_PRESENT')
market=ROOT/'data/raw/inbox/market'; mfiles=[p for p in market.iterdir() if p.is_file() and p.name.startswith('CSI300_EOD__') and p.suffix.lower()=='.csv'] if market.exists() else []
if mfiles:
    p=run([sys.executable,'scripts/ingest_market_data.py',str(sorted(mfiles)[0])]); print('MANUAL MARKET INGEST = SUCCESS')
else: print('MANUAL MARKET INGEST = NOT_PRESENT')
run([sys.executable,'scripts/validate/validate_csi300.py'])
run([sys.executable,'scripts/analysis/csi300_v12_events.py'])
run([sys.executable,'scripts/analysis/csi300_historical_join.py'])
run([sys.executable,'scripts/publish_v12.py'])
pytest=run([sys.executable,'-m','pytest','-q'],allow_fail=True)
print('PIPELINE OK' if pytest.returncode==0 else 'PIPELINE FAILED')
if pytest.returncode: raise SystemExit(pytest.returncode)
print('V1.2 PIPELINE OK')
