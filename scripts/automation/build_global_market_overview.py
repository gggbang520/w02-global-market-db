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

    output = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "SRC-DERIVED-GLOBAL-MARKET-OVERVIEW",
        "source_origin": "DERIVED_FROM_SNAPSHOT_PERFORMANCE_REGIONAL",
        "snapshot": snapshot,
        "performance": performance,
        "regional_strength": regional,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
