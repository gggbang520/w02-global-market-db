from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.diagnostics.dns_probe import probe_dns
from scripts.diagnostics.http_probe import probe_http

ROOT=Path(__file__).resolve().parents[2]
TARGETS={
 'CSI': 'https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000300cons.xls',
 'SSE': 'https://www.sse.com.cn/market/stockdata/',
 'SZSE': 'https://www.szse.cn/market/stock/',
}

def main():
    out=[]
    for name,url in TARGETS.items():
        host=url.split('/')[2]
        dns=probe_dns(host)
        http=probe_http(url) if dns.status=='PASS' else None
        out.append({'source':name,'url':url,'dns':dns.__dict__,'http':http.__dict__ if http else {'status':'NOT_RUN'}})
        print(f'{name} domain: DNS = {dns.status}')
        if http: print(f'  TCP={http.tcp_status} TLS={http.tls_status} HTTP={http.http_status} Content-Type={http.content_type}')
    report=ROOT/'reports/quality/network_diagnostics.json'; report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0
if __name__=='__main__': raise SystemExit(main())
