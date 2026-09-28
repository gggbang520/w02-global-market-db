from __future__ import annotations
import socket, ssl, urllib.error, urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urlparse

@dataclass
class HTTPProbeResult:
    url: str
    dns_status: str
    tcp_status: str
    tls_status: str
    http_status: str
    status_code: int | None
    redirect_url: str | None
    content_type: str | None
    error: str | None

def probe_http(url: str, timeout: int = 10) -> HTTPProbeResult:
    u = urlparse(url); host = u.hostname or ''
    dns_status = 'PASS'
    try:
        infos = socket.getaddrinfo(host, u.port or 443, type=socket.SOCK_STREAM)
        if not infos: dns_status = 'DNS_FAILURE'
    except socket.gaierror as e:
        return HTTPProbeResult(url,'DNS_FAILURE','NOT_RUN','NOT_RUN','NOT_RUN',None,None,None,f'{type(e).__name__}: {e}')
    tcp_status='PASS'; tls_status='PASS'
    try:
        with socket.create_connection((host, u.port or 443), timeout=timeout) as sock:
            if u.scheme == 'https':
                ctx=ssl.create_default_context()
                with ctx.wrap_socket(sock, server_hostname=host): pass
    except ssl.SSLError as e:
        return HTTPProbeResult(url,dns_status,tcp_status,'TLS_FAILURE','NOT_RUN',None,None,None,f'{type(e).__name__}: {e}')
    except OSError as e:
        return HTTPProbeResult(url,dns_status,'TCP_FAILURE','NOT_RUN','NOT_RUN',None,None,None,f'{type(e).__name__}: {e}')
    try:
        req=urllib.request.Request(url, headers={'User-Agent':'W02-Network-Diagnostics/0.6'}, method='GET')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return HTTPProbeResult(url,dns_status,tcp_status,tls_status,'HTTP_SUCCESS',r.status,r.geturl(),r.headers.get('Content-Type'))
    except urllib.error.HTTPError as e:
        return HTTPProbeResult(url,dns_status,tcp_status,tls_status,'HTTP_ERROR',e.code,e.geturl() if hasattr(e,'geturl') else None,e.headers.get('Content-Type') if e.headers else None,str(e))
    except urllib.error.URLError as e:
        return HTTPProbeResult(url,dns_status,tcp_status,tls_status,'HTTP_ERROR',None,None,None,str(e.reason))
    except Exception as e:
        return HTTPProbeResult(url,dns_status,tcp_status,tls_status,'HTTP_ERROR',None,None,None,f'{type(e).__name__}: {e}')
