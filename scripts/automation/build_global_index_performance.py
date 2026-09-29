from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY_ROOT = ROOT / "data/history"
OUTPUT = ROOT / "reports/index/global_index_performance.json"


def load_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        return json.loads(data["content"])
    return data


def find_daily_files():
    return sorted(HISTORY_ROOT.glob("**/indices/price_daily__*__*.json"))


def rows_from(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("records", "data", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def trade_date(row):
    return row.get("date") or row.get("trade_date") or row.get("Date")


def close_value(row):
    return row.get("close") or row.get("Close")


def pct(current, previous):
    if current is None or previous in (None, 0):
        return None
    return round((current / previous - 1) * 100, 4)


def build_item(path: Path):
    index_id = path.name.split("price_daily__", 1)[1].split("__", 1)[0]
    rows = rows_from(load_json(path))
    rows = sorted(rows, key=lambda x: trade_date(x) or "")
    if not rows:
        return None

    latest = rows[-1]
    latest_close = close_value(latest)
    previous_close = close_value(rows[-2]) if len(rows) > 1 else None

    month_base = rows[-22] if len(rows) > 22 else None
    year_base = next((r for r in rows if str(trade_date(r)).startswith(str(trade_date(latest))[:4])), rows[0])

    return {
        "index_id": index_id,
        "latest_trade_date": trade_date(latest),
        "close": latest_close,
        "daily_change_pct": pct(latest_close, previous_close),
        "monthly_change_pct": pct(latest_close, close_value(month_base)) if month_base else None,
        "ytd_change_pct": pct(latest_close, close_value(year_base)),
        "records_available": len(rows),
    }


def main():
    records = []
    for path in find_daily_files():
        item = build_item(path)
        if item:
            records.append(item)

    output = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "SRC-DERIVED-INDEX-PERFORMANCE",
        "source_origin": "DERIVED_FROM_DAILY_HISTORY",
        "record_count": len(records),
        "records": sorted(records, key=lambda x: x["index_id"]),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
