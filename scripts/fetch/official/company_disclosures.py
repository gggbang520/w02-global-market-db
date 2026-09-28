from __future__ import annotations
import argparse,json
from pathlib import Path
from .common import fetch_url,write_metadata

URL='https://www.sse.com.cn/disclosure/listedinfo/announcement/'

def main():
 p=argparse.ArgumentParser(); p.add_argument('--url',default=URL); args=p.parse_args(); root=Path(__file__).resolve().parents[3]
 result=fetch_url('SRC-SSE-OFFICIAL',args.url,root/'data/raw/cn','SRC-SSE-OFFICIAL__company_disclosures__CN__latest.html')
 write_metadata(result,root/'data/raw/_metadata/SRC-SSE-OFFICIAL__company_disclosures_fetch.json'); print(json.dumps(result.__dict__,ensure_ascii=False,indent=2)); return 0 if result.access_status=='AVAILABLE' else 2
if __name__=='__main__': raise SystemExit(main())
