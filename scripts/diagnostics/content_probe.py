from __future__ import annotations
from pathlib import Path
import mimetypes

def detect_content_type(path: str | Path) -> str:
    p=Path(path)
    ext=p.suffix.lower()
    known={
        '.xls':'application/vnd.ms-excel',
        '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.csv':'text/csv', '.json':'application/json', '.zip':'application/zip'
    }
    return known.get(ext) or mimetypes.guess_type(p.name)[0] or 'application/octet-stream'

def validate_content_type(actual: str | None, expected: set[str]) -> str:
    if not actual: return 'CONTENT_TYPE_UNEXPECTED'
    base=actual.split(';',1)[0].strip().lower()
    return 'HTTP_SUCCESS' if base in {x.lower() for x in expected} else 'CONTENT_TYPE_UNEXPECTED'
