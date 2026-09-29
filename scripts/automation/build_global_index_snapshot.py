from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/index/global_index_weekly_state.json"
OUTPUT = ROOT / "reports/index/latest_index_snapshot.json"


def load_weekly_state() -> dict:
    data = json.loads(INPUT.read_text(encoding="utf-8"))

    # Support wrapped outputs while preserving backward compatibility
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        return json.loads(data["content"])

    return data


def main() -> None:
    weekly = load_weekly_state()

    records = weekly.get("records", [])
    latest_date = weekly.get("end_date")

    grouped = {}
    for row in records:
        index_id = row.get("index_id")
        if not index_id:
            continue
        grouped.setdefault(index_id, []).append(row)

    snapshot = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_trade_date": latest_date,
        "source_id": "SRC-DERIVED-INDEX-SNAPSHOT",
        "source_origin": "DERIVED_FROM_WEEKLY_STATE",
        "quality_status": "OK",
        "indices": [],
    }

    for index_id, rows in grouped.items():
        rows = sorted(rows, key=lambda x: x.get("date", ""))
        latest = rows[-1]

        snapshot["indices"].append({
            "index_id": index_id,
            "close": latest.get("close"),
            "weekly_change_pct": latest.get("weekly_change_pct"),
            "daily_change_pct": None,
            "monthly_change_pct": None,
            "ytd_change_pct": latest.get("ytd_change_pct"),
            "records_available": len(rows),
            "quality_status": "OK" if len(rows) > 1 else "PARTIAL",
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
