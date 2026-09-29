import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/index/global_index_performance.json"
MASTER = ROOT / "data/standardized/index_master.json"
OUTPUT = ROOT / "reports/market/regional_market_strength.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    performance = load(INPUT)
    master = load(MASTER)
    markets = {x["index_id"]: x.get("market", "UNKNOWN") for x in master}

    regions = {}
    rows = performance.get("indices", performance if isinstance(performance, list) else [])
    for row in rows:
        idx = row.get("index_id")
        region = markets.get(idx, "UNKNOWN")
        regions.setdefault(region, []).append(row)

    output = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "SRC-DERIVED-REGIONAL-STRENGTH",
        "source_origin": "DERIVED_FROM_INDEX_PERFORMANCE",
        "regions": []
    }

    for region, items in sorted(regions.items()):
        output["regions"].append({
            "region": region,
            "index_count": len(items),
            "indexes": items,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
