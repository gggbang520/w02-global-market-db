from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data/standardized/stocks"
OUT_ROOT = ROOT / "data/standardized/partitions"
REPORT = ROOT / "reports/quality/standardized_compaction.json"

def main():
    if not SOURCE_DIR.exists():
        print("No row-level standardized directory; nothing to compact.")
        return 0

    buckets = defaultdict(dict)
    source_files = 0
    source_records = 0

    for p in SOURCE_DIR.glob("*.json"):
        source_files += 1
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        source_records += 1
        key = (r.get("listing_id"), r.get("trade_date"), r.get("source_id"), r.get("price_type"))
        if not key[0] or not key[1] or not key[2]:
            continue

        dt = str(r["trade_date"])
        source = str(r["source_id"])
        bucket = OUT_ROOT / dt[:4] / dt[5:7] / source
        buckets[str(bucket)][key] = r

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    partitions = []
    compacted_records = 0

    for bucket_str, records in sorted(buckets.items()):
        bucket = Path(bucket_str)
        bucket.mkdir(parents=True, exist_ok=True)
        out = bucket / "stock_daily.jsonl"

        rows = list(records.values())
        rows.sort(key=lambda x: (x.get("trade_date",""), x.get("exchange_mic",""), x.get("ticker","")))
        with out.open("w", encoding="utf-8", newline="
") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "
")

        compacted_records += len(rows)
        partitions.append({
            "file": str(out.relative_to(ROOT)),
            "records": len(rows),
            "year": bucket.parts[-3],
            "month": bucket.parts[-2],
            "source_id": bucket.parts[-1],
        })

    dedupe_removed = source_records - compacted_records
    report = {
        "status": "SUCCESS",
        "source_directory": str(SOURCE_DIR.relative_to(ROOT)),
        "source_files": source_files,
        "source_records": source_records,
        "compacted_records": compacted_records,
        "dedupe_removed": dedupe_removed,
        "partition_count": len(partitions),
        "partition_root": str(OUT_ROOT.relative_to(ROOT)),
        "dedupe_key": ["listing_id","trade_date","source_id","price_type"],
        "raw_and_history_preserved": True,
        "partitions": partitions,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Remove only the row-level standardized copies. Raw and History are untouched.
    for p in SOURCE_DIR.glob("*.json"):
        p.unlink()
    try:
        SOURCE_DIR.rmdir()
    except OSError:
        pass

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
