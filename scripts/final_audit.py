from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_RE = re.compile(r"price_daily__.*__(SRC-[A-Z0-9-]+)\.json$")
EXPECTED_BACKFILL = [
    f"{year}Q{q}"
    for year in range(2021, 2027)
    for q in range(1, 5)
    if not (year == 2026 and q > 3)
]


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_records(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return obj.get("records", [])
    return []


def main():
    report = {
        "status": "SUCCESS",
        "audit_version": 2,
        "generated_by": "scripts/final_audit.py",
        "raw_market": {},
        "history": {},
        "standardized": {},
        "backfill_state": {},
        "checks": {},
    }

    # 1. RAW market inbox: exact byte-for-byte duplicate inventory.
    raw = ROOT / "data/raw/inbox/market"
    raw_groups = defaultdict(list)
    if raw.exists():
        for p in raw.iterdir():
            if p.is_file():
                raw_groups[file_sha(p)].append(str(p.relative_to(ROOT)))
    raw_dupes = {k: v for k, v in raw_groups.items() if len(v) > 1}
    report["raw_market"] = {
        "file_count": sum(len(v) for v in raw_groups.values()),
        "sha_group_count": len(raw_groups),
        "exact_duplicate_group_count": len(raw_dupes),
        "exact_duplicate_groups": raw_dupes,
    }

    # 2. History inventory across ALL known sources.
    history = ROOT / "data/history"
    batches = []
    source_stats = defaultdict(lambda: {
        "file_count": 0,
        "record_count": 0,
        "distinct_listings": set(),
        "distinct_trade_dates": set(),
        "min_trade_date": None,
        "max_trade_date": None,
    })
    seen_keys = set()
    overlap_samples = []
    overlap_count = 0

    if history.exists():
        history_files = sorted(history.rglob("price_daily__*.json"))
        for p in history_files:
            rel = str(p.relative_to(ROOT))
            source_id = "UNKNOWN"
            m = SOURCE_RE.match(p.name)
            if m:
                source_id = m.group(1)
            try:
                obj = load_json(p)
                records = extract_records(obj)
            except Exception as e:
                batches.append({
                    "file": rel,
                    "source_id": source_id,
                    "parse_status": "FAILED",
                    "error": str(e),
                })
                continue

            dates = sorted({r.get("trade_date") for r in records if r.get("trade_date")})
            listings = {
                (r.get("exchange_mic"), r.get("ticker"), r.get("listing_id"))
                for r in records
                if r.get("ticker") or r.get("listing_id")
            }

            stats = source_stats[source_id]
            stats["file_count"] += 1
            stats["record_count"] += len(records)
            stats["distinct_listings"].update(listings)
            stats["distinct_trade_dates"].update(dates)
            if dates:
                if stats["min_trade_date"] is None or dates[0] < stats["min_trade_date"]:
                    stats["min_trade_date"] = dates[0]
                if stats["max_trade_date"] is None or dates[-1] > stats["max_trade_date"]:
                    stats["max_trade_date"] = dates[-1]

            # Duplicate logical observations across history batches of the SAME source.
            for r in records:
                entity = (
                    r.get("listing_id")
                    or r.get("index_id")
                    or r.get("security_id")
                    or f"{r.get('exchange_mic')}:{r.get('ticker')}"
                )
                dt = r.get("trade_date")
                price_type = r.get("price_type")
                if entity and dt:
                    key = (source_id, entity, dt, price_type)
                    if key in seen_keys:
                        overlap_count += 1
                        if len(overlap_samples) < 50:
                            overlap_samples.append({
                                "key": list(key),
                                "file": rel,
                            })
                    else:
                        seen_keys.add(key)

            batches.append({
                "file": rel,
                "source_id": source_id,
                "parse_status": "SUCCESS",
                "records": len(records),
                "distinct_listings": len(listings),
                "distinct_trade_dates": len(dates),
                "trade_date_min": dates[0] if dates else None,
                "trade_date_max": dates[-1] if dates else None,
                "size_bytes": p.stat().st_size,
            })

    report["history"] = {
        "batch_file_count": len(batches),
        "batch_record_sum": sum(x.get("records", 0) for x in batches),
        "parse_failures": sum(1 for x in batches if x.get("parse_status") == "FAILED"),
        "same_source_logical_overlap_count": overlap_count,
        "overlap_samples": overlap_samples,
        "batches": batches,
        "sources": {
            source_id: {
                "file_count": stats["file_count"],
                "record_count": stats["record_count"],
                "distinct_listings": len(stats["distinct_listings"]),
                "distinct_trade_dates": len(stats["distinct_trade_dates"]),
                "min_trade_date": stats["min_trade_date"],
                "max_trade_date": stats["max_trade_date"],
            }
            for source_id, stats in sorted(source_stats.items())
        },
    }

    # 3. Standardized partition inventory for every source.
    std_root = ROOT / "data/standardized/partitions"
    standardized = {}
    legacy_files = []

    if std_root.exists():
        for source_dir in sorted(p for p in std_root.iterdir() if p.is_dir()):
            canonical = []
            legacy = []
            for p in source_dir.rglob("stock_daily.jsonl"):
                rel = p.relative_to(source_dir).parts
                is_canonical = (
                    len(rel) == 3
                    and len(rel[0]) == 4
                    and rel[0].isdigit()
                    and len(rel[1]) == 2
                    and rel[1].isdigit()
                    and rel[2] == "stock_daily.jsonl"
                )
                target = canonical if is_canonical else legacy
                target.append({
                    "path": str(p.relative_to(ROOT)),
                    "size_bytes": p.stat().st_size,
                })
                if not is_canonical:
                    legacy_files.append(str(p.relative_to(ROOT)))
            standardized[source_dir.name] = {
                "canonical_partition_count": len(canonical),
                "canonical_partitions": canonical,
                "legacy_partition_file_count": len(legacy),
                "legacy_partition_files": legacy,
            }

    report["standardized"] = {
        "source_count": len(standardized),
        "sources": standardized,
        "legacy_partition_file_count": len(legacy_files),
        "legacy_partition_files": legacy_files,
    }

    # 4. Yahoo historical backfill state: coverage, quality, and state consistency.
    state_path = ROOT / "reports/backfill/csi300_yahoo_backfill_state.json"
    state_summary = {
        "file_present": state_path.exists(),
        "expected_quarter_count": len(EXPECTED_BACKFILL),
        "present_quarters": [],
        "missing_quarters": [],
        "status_counts": defaultdict(int),
        "validation_status_counts": defaultdict(int),
        "download_failure_quarters": [],
        "state_status_vs_validation_mismatch": [],
        "partial_quarters": [],
        "license_gate_counts": defaultdict(int),
        "publication_scope_counts": defaultdict(int),
        "raw_rows": 0,
        "standardized_rows": 0,
    }

    if state_path.exists():
        try:
            state = load_json(state_path)
            quarters = state.get("quarters", {})
            state_summary["present_quarters"] = sorted(quarters.keys())
            state_summary["missing_quarters"] = [
                q for q in EXPECTED_BACKFILL if q not in quarters
            ]

            for q in EXPECTED_BACKFILL:
                item = quarters.get(q)
                if not item:
                    continue
                status = item.get("status", "UNKNOWN")
                validation = item.get("validation_status", "UNKNOWN")
                state_summary["status_counts"][status] += 1
                state_summary["validation_status_counts"][validation] += 1
                state_summary["raw_rows"] += int(item.get("raw_rows", 0) or 0)
                state_summary["standardized_rows"] += int(item.get("standardized_rows", 0) or 0)
                gate = item.get("license_gate", "UNKNOWN")
                scope = item.get("publication_scope", "UNKNOWN")
                state_summary["license_gate_counts"][gate] += 1
                state_summary["publication_scope_counts"][scope] += 1

                if item.get("download_failures"):
                    state_summary["download_failure_quarters"].append(q)
                if validation == "PARTIAL":
                    state_summary["partial_quarters"].append({
                        "quarter": q,
                        "invalid_rows": item.get("validation_invalid_rows", 0),
                        "duplicate_rows": item.get("validation_duplicate_rows", 0),
                        "review_rows": item.get("validation_review_rows", 0),
                    })
                expected_status = "PARTIAL" if validation == "PARTIAL" else status
                if validation == "PARTIAL" and status != "PARTIAL":
                    state_summary["state_status_vs_validation_mismatch"].append({
                        "quarter": q,
                        "status": status,
                        "validation_status": validation,
                    })
        except Exception as e:
            state_summary["parse_error"] = str(e)

    # JSON cannot serialize defaultdict directly.
    for key in ("status_counts", "validation_status_counts", "license_gate_counts", "publication_scope_counts"):
        state_summary[key] = dict(state_summary[key])

    report["backfill_state"] = state_summary

    # 5. High-level checks. These are findings, not publication authorization.
    checks = {
        "raw_preserved": raw.exists(),
        "history_preserved": history.exists(),
        "state_present": state_path.exists(),
        "has_exact_duplicate_raw_files": bool(raw_dupes),
        "has_history_parse_failures": report["history"]["parse_failures"] > 0,
        "has_history_overlaps": overlap_count > 0,
        "has_legacy_standardized_files": bool(legacy_files),
        "backfill_has_missing_quarters": bool(state_summary["missing_quarters"]),
        "backfill_has_download_failure_quarters": bool(state_summary["download_failure_quarters"]),
        "backfill_has_partial_quarters": bool(state_summary["partial_quarters"]),
        "backfill_state_validation_mismatch": bool(state_summary["state_status_vs_validation_mismatch"]),
        "all_expected_backfill_quarters_present": not state_summary["missing_quarters"],
    }
    report["checks"] = checks

    # Overall audit status describes data state, not business value.
    report["status"] = "REVIEW" if any([
        checks["has_history_parse_failures"],
        checks["has_history_overlaps"],
        checks["has_legacy_standardized_files"],
        checks["backfill_has_missing_quarters"],
        checks["backfill_has_download_failure_quarters"],
        checks["backfill_has_partial_quarters"],
        checks["backfill_state_validation_mismatch"],
    ]) else "SUCCESS"

    out = ROOT / "reports/quality/final_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
