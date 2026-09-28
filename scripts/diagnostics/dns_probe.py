from __future__ import annotations
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

@dataclass
class DNSResult:
    host: str
    status: str
    addresses: list[str]
    error: str | None = None

def probe_dns(host: str) -> DNSResult:
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addrs = sorted({x[4][0] for x in infos})
        return DNSResult(host, 'PASS' if addrs else 'DNS_FAILURE', addrs)
    except socket.gaierror as e:
        return DNSResult(host, 'DNS_FAILURE', [], f'{type(e).__name__}: {e}')
    except Exception as e:
        return DNSResult(host, 'DNS_FAILURE', [], f'{type(e).__name__}: {e}')
