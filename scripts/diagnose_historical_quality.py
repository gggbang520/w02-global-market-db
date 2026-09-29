from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "reports/backfill/csi300_yahoo_backfill_state.json"
OUT = ROOT / "reports/quality/historical_quality_diagnostic.json"


def fnum(v):
    if v is None or str(v).strip() == "":
        return None
    return float(v)


def inspect_row(row):
    errors = []
    vals = {k: fnum(row.get(k)) for k in ("open", "high", "low", "close")}
    if any(v is None for v in vals.values()):
        errors.append("OHLC_MISSING")
    else:
        o, h, l, c = vals["open"], vals["high"], vals["low"], vals["close"]
        if not (h >= l and h >= o and h >= c and l <= o and l <= c and c >= 0):
            errors.append("OHLC_INVALID")
    if row.get("volume") not in (None, ""):
        try:
            if float(row["volume"]) < 0:
                errors.append("VOLUME_INVALID")
        except Exception:
            errors.append("VOLUME_PARSE_ERROR")
    return errors


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    quarters = state.get("quarters", {})
    partials = [q for q, x in quarters.items() if x.get("validation_status") == "PARTIAL"]

    report = {"status": "SUCCESS", "quarters": {}, "focus": "2024Q1"}
    for q in partials:
        item = quarters[q]
        raw_file = ROOT / item["raw_file"]
        summary = {
            "raw_file": str(raw_file.relative_to(ROOT)),
            "exists": raw_file.exists(),
            "row_count": 0,
            "error_counts": {},
            "samples": [],
            "column_names": [],
        }
        if not raw_file.exists():
            summary["status"] = "MISSING_RAW_FILE"
            report["status"] = "REVIEW"
            report["quarters"][q] = summary
            continue

        counts = Counter()
        samples = []
        with raw_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            summary["column_names"] = reader.fieldnames or []
            for row in reader:
                summary["row_count"] += 1
                errors = inspect_row(row)
                for err in errors:
                    counts[err] += 1
                if errors and len(samples) < 30:
                    samples.append({
                        "ticker": row.get("ticker"),
                        "yahoo_symbol": row.get("yahoo_symbol"),
                        "trade_date": row.get("trade_date"),
                        "open": row.get("open"),
                        "high": row.get("high"),
                        "low": row.get("low"),
                        "close": row.get("close"),
                        "volume": row.get("volume"),
                        "errors": errors,
                    })
        summary["error_counts"] = dict(counts)
        summary["samples"] = samples
        report["quarters"][q] = summary

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
