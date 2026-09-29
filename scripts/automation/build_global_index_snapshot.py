from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/index/global_index_weekly_state.json"
OUTPUT = ROOT / "reports/index/latest_index_snapshot.json"


def main() -> None:
    weekly = json.loads(INPUT.read_text(encoding="utf-8"))["content"]
    if isinstance(weekly, str):
        weekly = json.loads(weekly)

    snapshot = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_trade_date": weekly.get("end_date"),
        "source_id": "SRC-DERIVED-INDEX-SNAPSHOT",
        "source_origin": "DERIVED_FROM_WEEKLY_STATE",
        "quality_status": "PARTIAL",
        "indices": [],
    }

    for index_id, count in weekly.get("records_by_index", {}).items():
        status = "OK" if count > 1 else "PARTIAL"
        snapshot["indices"].append({
            "index_id": index_id,
            "close": None,
            "daily_change_pct": None,
            "weekly_change_pct": None,
            "monthly_change_pct": None,
            "ytd_change_pct": None,
            "records_available": count,
            "quality_status": status,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
