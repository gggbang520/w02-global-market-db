import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    print(p.stdout,end=''); print(p.stderr,end='')
    if p.returncode: raise SystemExit(p.returncode)
run([sys.executable,'scripts/run_pipeline.py'])
run([sys.executable,'scripts/analysis/csi300_historical_join.py'])
run([sys.executable,'scripts/publish_v10.py'])
print('V1.0 PIPELINE OK')
