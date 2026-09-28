from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, mimetypes, socket, urllib.error, urllib.request

FAILURE_STATES={'NETWORK_ERROR','HTTP_ERROR','ACCESS_BLOCKED','CONTENT_TYPE_UNEXPECTED','PARSE_FAILED','SCHEMA_CHANGED','EMPTY_RESPONSE','LICENSE_REVIEW'}

@dataclass
class FetchResult:
    source_id: str
    url: str
    request_time: str
    response_time: str
    content_type: str|None
    http_status: int|None
    file_path: str|None
    file_hash: str|None
    file_size: int|None
    access_status: str
    error: str|None=None


def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def fetch_url(source_id: str, url: str, raw_dir: Path, filename: str, timeout=30) -> FetchResult:
    req_time=now(); path=None
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'W02-Global-Market-Database/0.5 (+official-data-access-layer)'})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            status=r.status; ctype=r.headers.get_content_type(); body=r.read()
            response_time=now()
            if status >= 400: return FetchResult(source_id,url,req_time,response_time,ctype,status,None,None,None,'HTTP_ERROR',f'HTTP {status}')
            if not body: return FetchResult(source_id,url,req_time,response_time,ctype,status,None,None,0,'EMPTY_RESPONSE','empty response')
            path=raw_dir/filename; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(body)
            sha=hashlib.sha256(body).hexdigest()
            return FetchResult(source_id,url,req_time,response_time,ctype,status,str(path.relative_to(raw_dir.parent.parent)),sha,len(body),'AVAILABLE')
    except urllib.error.HTTPError as e:
        return FetchResult(source_id,url,req_time,now(),e.headers.get_content_type() if e.headers else None,e.code,None,None,None,'HTTP_ERROR',str(e))
    except urllib.error.URLError as e:
        reason=e.reason
        if isinstance(reason, socket.gaierror) or 'name resolution' in str(reason).lower() or 'nodename' in str(reason).lower():
            status='DNS_FAILURE'
        elif isinstance(reason, TimeoutError) or 'timed out' in str(reason).lower():
            status='NETWORK_FAILURE'
        else:
            status='NETWORK_FAILURE'
        return FetchResult(source_id,url,req_time,now(),None,None,None,None,None,status,str(reason))
    except TimeoutError as e:
        return FetchResult(source_id,url,req_time,now(),None,None,None,None,None,'NETWORK_ERROR',str(e))
    except Exception as e:
        return FetchResult(source_id,url,req_time,now(),None,None,None,None,None,'NETWORK_ERROR',f'{type(e).__name__}: {e}')

def check_content_type(content_type: str|None, expected: set[str]) -> str:
    if not content_type: return 'UNKNOWN'
    c=content_type.lower().split(';',1)[0].strip()
    return 'EXPECTED' if c in {x.lower() for x in expected} else 'UNEXPECTED'

def write_metadata(result: FetchResult, path: Path):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(asdict(result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
