from __future__ import annotations
import argparse, json
from pathlib import Path
from .common import fetch_url, write_metadata

URL='https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000300cons.xls'

def main():
 p=argparse.ArgumentParser(); p.add_argument('--url',default=URL); p.add_argument('--raw-dir',default='data/raw/cn'); p.add_argument('--metadata-dir',default='data/raw/_metadata'); args=p.parse_args()
 root=Path(__file__).resolve().parents[3]
 result=fetch_url('SRC-CSI-OFFICIAL',args.url,root/args.raw_dir,'SRC-CSI-OFFICIAL__index_constituents__CN__latest.xls')
 write_metadata(result,root/args.metadata_dir/'SRC-CSI-OFFICIAL__fetch.json')
 print(json.dumps(result.__dict__,ensure_ascii=False,indent=2))
 return 0 if result.access_status=='AVAILABLE' else 2
if __name__=='__main__': raise SystemExit(main())
