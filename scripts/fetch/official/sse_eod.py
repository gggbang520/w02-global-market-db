from __future__ import annotations
import argparse,json
from pathlib import Path
from .common import fetch_url,write_metadata

# Official discovery endpoint: SSE stock data landing page. A bulk EOD file/API
# endpoint is intentionally not invented; set --url to a licensed/verified bulk endpoint.
DISCOVERY_URL='https://www.sse.com.cn/market/stockdata/'

def main():
 p=argparse.ArgumentParser(); p.add_argument('--url',default=DISCOVERY_URL); p.add_argument('--raw-dir',default='data/raw/cn'); p.add_argument('--metadata-dir',default='data/raw/_metadata'); args=p.parse_args(); root=Path(__file__).resolve().parents[3]
 result=fetch_url('SRC-SSE-OFFICIAL',args.url,root/args.raw_dir,'SRC-SSE-OFFICIAL__eod_discovery__CN__latest.html')
 write_metadata(result,root/args.metadata_dir/'SRC-SSE-OFFICIAL__fetch.json'); print(json.dumps(result.__dict__,ensure_ascii=False,indent=2)); return 0 if result.access_status=='AVAILABLE' else 2
if __name__=='__main__': raise SystemExit(main())
