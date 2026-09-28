from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data/history/DATA-2026-W39/stocks"
STD = ROOT / "data/standardized/partitions"
SOURCE = "SRC-GITHUB-TUSHARE-ARCHIVE"

TARGET_FILES = [
    HISTORY / "price_daily__2020-01-02_2020-03-31__SRC-GITHUB-TUSHARE-ARCHIVE.json",
    HISTORY / "price_daily__2021-01-18_2021-01-29__SRC-GITHUB-TUSHARE-ARCHIVE.json",
]

def main():
    buckets = defaultdict(dict)
    input_records = 0

    for p in TARGET_FILES:
        if not p.exists():
            raise FileNotFoundError(f"Required History batch missing: {p}")
        records = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"History batch is not a list: {p}")

        for original in records:
            input_records += 1
            r = dict(original)
            r["source_id"] = SOURCE
            r["source_origin"] = "AUTO_PROVIDER"
            key = (r.get("listing_id"), r.get("trade_date"), r.get("source_id"), r.get("price_type"))
            if not key[0] or not key[1]:
                continue
            dt = str(r["trade_date"])
            buckets[(dt[:4], dt[5:7])][key] = r

    canonical = STD / SOURCE
    canonical.mkdir(parents=True, exist_ok=True)

    partition_meta = []
    written = 0
    for (year, month), records_map in sorted(buckets.items()):
        rows = list(records_map.values())
        rows.sort(key=lambda x: (x.get("trade_date",""), x.get("exchange_mic",""), x.get("ticker","")))
        dest = canonical / year / month
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / "stock_daily.jsonl"
        out.write_text(
            "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows),
            encoding="utf-8",
        )
        written += len(rows)
        partition_meta.append({"year":year,"month":month,"records":len(rows),"file":str(out.relative_to(ROOT))})

    report = {
        "status": "SUCCESS",
        "source_id": SOURCE,
        "source_origin": "AUTO_PROVIDER",
        "input_history_records": input_records,
        "rebuilt_records": written,
        "dedupe_key": ["listing_id","trade_date","source_id","price_type"],
        "canonical_partition_root": str(canonical.relative_to(ROOT)),
        "legacy_malformed_partition_preserved_for_manual_review": True,
        "partitions": partition_meta,
    }
    out = ROOT / "reports/quality/provenance_repair_v2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
