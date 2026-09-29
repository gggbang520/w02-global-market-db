from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "reports/index/latest_index_snapshot.json"
PERFORMANCE = ROOT / "reports/index/global_index_performance.json"
REGIONAL = ROOT / "reports/market/regional_market_strength.json"
OUTPUT = ROOT / "reports/dashboard/global_market_overview.json"


def load(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        return json.loads(data["content"])
    return data


def main():
    snapshot = load(SNAPSHOT) if SNAPSHOT.exists() else {}
    performance = load(PERFORMANCE) if PERFORMANCE.exists() else {}
    regional = load(REGIONAL) if REGIONAL.exists() else {}

    performance_records = performance.get("records", []) if isinstance(performance, dict) else []
    performance_map = {
        record.get("index_id"): record
        for record in performance_records
        if isinstance(record, dict) and record.get("index_id")
    }

    snapshot_records = snapshot.get("indices", []) if isinstance(snapshot, dict) else []
    merged_indices = []

    for item in snapshot_records:
        if not isinstance(item, dict):
            continue

        index_id = item.get("index_id")
        merged = dict(item)
        performance_item = performance_map.get(index_id, {})

        for field in [
            "daily_change_pct",
            "weekly_change_pct",
            "monthly_change_pct",
            "ytd_change_pct",
            "close",
            "latest_trade_date",
            "records_available",
        ]:
            if performance_item.get(field) is not None:
                merged[field] = performance_item[field]

        merged_indices.append(merged)

    output = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "SRC-DERIVED-GLOBAL-MARKET-OVERVIEW",
        "source_origin": "DERIVED_FROM_SNAPSHOT_PERFORMANCE_REGIONAL",
        "index_count": len(merged_indices),
        "indices": merged_indices,
        "regional_strength": regional,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
