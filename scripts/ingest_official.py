from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.v07_official import run_real_file, sha256
from scripts.parse.csi_constituents_parser import parse_csi_file_detailed

OFFICIAL_SOURCE=('SRC-CSI-OFFICIAL','CSI300_CONSTITUENTS','CN','https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000300cons.xls')

def detect_source(path:Path):
    n=path.name.lower()
    if n in {'000300cons.xls','000300cons.xlsx'}: return OFFICIAL_SOURCE
    try:
        if path.resolve().is_relative_to((ROOT/'data/raw/inbox/official').resolve()):
            # Content-based recognition: code/name headers must be detectable before
            # the file is admitted as CSI300 official. Filename is not required.
            d=parse_csi_file_detailed(path, source_origin='OFFICIAL')
            if d['validation']['parsed_rows']>0:
                return OFFICIAL_SOURCE
    except Exception:
        pass
    return (None,None,None,None)

def ingest(path:Path):
    source=detect_source(path)
    if source[0] is None:
        return {'source_id':None,'dataset':None,'input_file':str(path),'sha256':sha256(path),'input_origin':'UNRESOLVED','status':'SOURCE_UNRESOLVED','publish_gate':'BLOCKED'}
    return run_real_file(path)

if __name__=='__main__':
    if len(sys.argv)!=2: print('usage: python scripts/ingest_official.py <file>',file=sys.stderr); raise SystemExit(2)
    p=Path(sys.argv[1]).resolve()
    r=ingest(p); print(__import__('json').dumps(r,ensure_ascii=False,indent=2)); raise SystemExit(0 if r.get('status') in {'PUBLISHED','VALIDATION_FAILED'} else 1)
