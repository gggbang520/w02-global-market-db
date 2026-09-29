from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY_ROOT = ROOT / "data/history"
WEEKLY_STATE = ROOT / "reports/index/global_index_weekly_state.json"
OUTPUT = ROOT / "reports/index/latest_index_snapshot.json"


def load_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        return json.loads(data["content"])
    return data


def find_daily_files() -> list[Path]:
    return sorted(HISTORY_ROOT.glob("**/indices/price_daily__*__*.json"))


def calc_pct(current, previous):
    if current is None or previous in (None, 0):
        return None
    return round((current / previous - 1) * 100, 4)


def extract_rows(data) -> list[dict]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("records", "data", "rows"):
            if isinstance(data.get(key), list):
                return data[key]

    return []


def build_daily_snapshot(path: Path) -> dict | None:
    name = path.name
    try:
        index_id = name.split("price_daily__", 1)[1].split("__", 1)[0]
    except IndexError:
        return None

    data = load_json(path)
    rows = extract_rows(data)
    if not rows:
        return {
            "index_id": index_id,
            "quality_status": "PARTIAL",
            "close": None,
        }

    rows = sorted(rows, key=lambda x: x.get("date", x.get("trade_date", "")))
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else None

    close = latest.get("close") or latest.get("Close")
    prev_close = previous.get("close") or previous.get("Close") if previous else None

    return {
        "index_id": index_id,
        "close": close,
        "daily_change_pct": calc_pct(close, prev_close),
        "latest_trade_date": latest.get("date", latest.get("trade_date")),
        "records_available": len(rows),
        "quality_status": "OK" if len(rows) > 1 else "PARTIAL",
    }


def main() -> None:
    weekly = load_json(WEEKLY_STATE)

    weekly_rows = {}
    for row in weekly.get("records", []):
        index_id = row.get("index_id")
        if index_id:
            weekly_rows[index_id] = row

    snapshot_items = {}
    latest_dates = []
    for file in find_daily_files():
        item = build_daily_snapshot(file)
        if item:
            snapshot_items[item["index_id"]] = item
            if item.get("latest_trade_date"):
                latest_dates.append(item["latest_trade_date"])

    indices = []
    all_ids = set(snapshot_items) | set(weekly_rows)

    for index_id in sorted(all_ids):
        item = snapshot_items.get(index_id, {
            "index_id": index_id,
            "close": None,
            "quality_status": "PARTIAL",
        })

        weekly = weekly_rows.get(index_id, {})
        item.update({
            "weekly_change_pct": weekly.get("weekly_change_pct"),
            "ytd_change_pct": weekly.get("ytd_change_pct"),
            "monthly_change_pct": None,
        })

        indices.append(item)

    latest_trade_date = weekly.get("end_date")
    if not latest_trade_date and latest_dates:
        latest_trade_date = max(latest_dates)

    output = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_trade_date": latest_trade_date,
        "source_id": "SRC-DERIVED-INDEX-SNAPSHOT",
        "source_origin": "DERIVED_FROM_DAILY_AND_WEEKLY",
        "indices": indices,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
