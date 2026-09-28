from __future__ import annotations
import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "SRC-GITHUB-TUSHARE-ARCHIVE"
DEST_DIR = ROOT / "data/history/DATA-2026-W39/stocks"

from scripts.providers.manual_file import ManualFileProvider
from scripts.ingest_market_data import resolve_listing, validate

def latest_raw_file():
    inbox = ROOT / "data/raw/inbox/market"
    files = sorted(
        inbox.glob(f"{SOURCE}__stock_daily__CN__*.csv"),
        key=lambda p: p.stat().st_mtime,
    )
    if not files:
        raise FileNotFoundError("No auto-fetched GitHub archive CSV found.")
    return files[-1]

def main():
    raw_path = latest_raw_file()
    provider = ManualFileProvider(raw_path)
    raw = provider.parse()
    normalized = resolve_listing(provider.normalize(raw))
    result = validate(normalized)

    if result["invalid"] or result["duplicate"] or result["review"]:
        raise RuntimeError(
            f"History materialization blocked: raw={len(raw)}, "
            f"valid={len(result['valid'])}, invalid={len(result['invalid'])}, "
            f"duplicate={len(result['duplicate'])}, review={len(result['review'])}"
        )

    dedup = OrderedDict()
    for r in result["valid"]:
        key = (r["listing_id"], r["trade_date"], r["source_id"], r["price_type"])
        dedup[key] = r

    records = list(dedup.values())
    records.sort(key=lambda r: (r["trade_date"], r["exchange_mic"], r["ticker"]))

    dates = sorted({r["trade_date"] for r in records})
    listings = sorted({r["listing_id"] for r in records})
    if not dates:
        raise RuntimeError("No valid historical records found.")

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    out = DEST_DIR / f"price_daily__{dates[0]}_{dates[-1]}__{SOURCE}.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    receipt = {
        "source_id": SOURCE,
        "dataset": "stock_daily",
        "input_file": str(raw_path.relative_to(ROOT)),
        "history_file": str(out.relative_to(ROOT)),
        "input_rows": len(raw),
        "records": len(records),
        "distinct_listings": len(listings),
        "distinct_trade_dates": len(dates),
        "trade_date_min": dates[0],
        "trade_date_max": dates[-1],
        "dedup_key": ["listing_id", "trade_date", "source_id", "price_type"],
        "status": "SUCCESS",
    }
    report_dir = ROOT / "reports/ingestion"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"history_materialization__{SOURCE}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
