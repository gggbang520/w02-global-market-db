from __future__ import annotations
import json
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "SRC-GITHUB-TUSHARE-ARCHIVE"
DEST_DIR = ROOT / "data/history/DATA-2026-W39/stocks"

def main():
    files = list((ROOT / "data/standardized/stocks").glob("*.json"))
    selected = []
    for p in files:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if obj.get("source_id") == SOURCE and obj.get("trade_date"):
            selected.append(obj)

    dedup = OrderedDict()
    for r in selected:
        key = (r.get("listing_id"), r.get("trade_date"), r.get("source_id"), r.get("price_type"))
        if key[0] and key[1]:
            dedup[key] = r

    records = list(dedup.values())
    records.sort(key=lambda r: (r.get("trade_date",""), r.get("exchange_mic",""), r.get("ticker","")))
    if not records:
        raise RuntimeError("No standardized historical records found for source.")

    dates = sorted({r["trade_date"] for r in records})
    listings = sorted({r["listing_id"] for r in records})

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    out = DEST_DIR / f"price_daily__{dates[0]}_{dates[-1]}__{SOURCE}.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    receipt = {
        "source_id": SOURCE,
        "dataset": "stock_daily",
        "history_file": str(out.relative_to(ROOT)),
        "records": len(records),
        "distinct_listings": len(listings),
        "distinct_trade_dates": len(dates),
        "trade_date_min": dates[0],
        "trade_date_max": dates[-1],
        "dedup_key": ["listing_id","trade_date","source_id","price_type"],
        "status": "SUCCESS"
    }
    report_dir = ROOT / "reports/ingestion"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"history_materialization__{SOURCE}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
