from pathlib import Path
import json

CANDIDATE_FILES = [
    Path("data/current/constituents/CSI300__current.json"),
    Path("data/current/constituents/csi300__current.json"),
    Path("data/current/constituents/CSI300_current.json"),
]

def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)

def _ticker(value):
    if value is None:
        return None
    s = str(value).strip().upper()
    for suffix in (".SH", ".SS", ".SZ", ".XSHG", ".XSHE"):
        if s.endswith(suffix):
            s = s[:-len(suffix)]
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits.zfill(6) if digits else None

def _exchange(value):
    if value is None:
        return None
    s = str(value).strip().upper()
    return {
        "XSHG":"XSHG","SH":"XSHG","SSE":"XSHG",
        "XSHE":"XSHE","SZ":"XSHE","SZSE":"XSHE"
    }.get(s)

def find_constituent_file():
    for p in CANDIDATE_FILES:
        if p.exists():
            return p
    found = list(Path("data").rglob("*CSI300*current*.json")) + list(Path("data").rglob("*csi300*current*.json"))
    if not found:
        raise FileNotFoundError("CSI300 current constituent JSON not found under data/")
    return found[0]

def load_csi300_listings():
    path = find_constituent_file()
    obj = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for item in _walk(obj):
        ticker = _ticker(item.get("ticker") or item.get("source_ticker") or item.get("security_code") or item.get("code"))
        ex = _exchange(item.get("exchange_mic") or item.get("exchange"))
        listing_id = item.get("listing_id")
        if not ex and isinstance(listing_id, str):
            if "XSHG" in listing_id: ex = "XSHG"
            elif "XSHE" in listing_id: ex = "XSHE"
        if not ex and ticker:
            if ticker.startswith(("6","68")): ex = "XSHG"
            elif ticker.startswith(("0","2","3")): ex = "XSHE"
        if ticker and ex in {"XSHG","XSHE"}:
            out[(ex, ticker)] = {
                "ticker": ticker,
                "exchange": ex,
                "listing_id": listing_id or f"LST-CN-{ticker}",
            }
    if not out:
        raise ValueError("No CSI300 listings extracted.")
    return list(out.values())

def yahoo_symbol(ticker, exchange):
    return f"{ticker}{'.SS' if exchange == 'XSHG' else '.SZ'}"
