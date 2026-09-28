from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data/history"
OUT = ROOT / "reports/quality/history_audit.json"

def main():
    batch_files = sorted(HISTORY.rglob("price_daily__*__SRC-GITHUB-TUSHARE-ARCHIVE.json"))
    batches = []
    key_to_files = defaultdict(list)
    total_records = 0

    for p in batch_files:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            batches.append({"file": str(p.relative_to(ROOT)), "parse_status": "FAILED", "error": str(e)})
            continue

        records = obj if isinstance(obj, list) else obj.get("records", [])
        keys = set()
        for r in records:
            key = (r.get("listing_id"), r.get("trade_date"), r.get("source_id"), r.get("price_type"))
            if all(key[:2]) and key[2]:
                keys.add(key)
                key_to_files[key].append(str(p.relative_to(ROOT)))

        dates = sorted({r.get("trade_date") for r in records if r.get("trade_date")})
        listings = sorted({r.get("listing_id") for r in records if r.get("listing_id")})
        total_records += len(records)
        batches.append({
            "file": str(p.relative_to(ROOT)),
            "parse_status": "OK",
            "records": len(records),
            "distinct_keys": len(keys),
            "distinct_listings": len(listings),
            "distinct_trade_dates": len(dates),
            "trade_date_min": dates[0] if dates else None,
            "trade_date_max": dates[-1] if dates else None,
            "file_size_bytes": p.stat().st_size,
        })

    overlaps = [{"key": list(k), "files": files} for k, files in key_to_files.items() if len(files) > 1]
    standardized = ROOT / "data/standardized/stocks"
    standardized_count = sum(1 for p in standardized.glob("*.json")) if standardized.exists() else 0

    report = {
        "status": "SUCCESS",
        "history_batch_file_count": len(batch_files),
        "history_batch_record_sum": total_records,
        "overlap_key_count_across_batch_files": len(overlaps),
        "standardized_row_file_count": standardized_count,
        "storage_warning": "REVIEW: row-level standardized JSON should be partitioned before multi-year expansion." if standardized_count > 5000 else "OK",
        "batches": batches,
        "overlap_samples": overlaps[:100],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
