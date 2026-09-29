from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_HISTORY_DIR = ROOT / "data/history/DATA-2026-W39/indices"
WEEKLY_HISTORY_DIR = INDEX_HISTORY_DIR
WEEKLY_PARTITION_ROOT = ROOT / "data/standardized/partitions/SRC-DERIVED-INDEX-WEEKLY"
REPORT_PATH = ROOT / "reports/index/global_index_weekly_state.json"


# Weekly layer consumes the canonical daily index history files and derives only week-level metrics.

def load_daily_records():
    rows = []
    for path in sorted(INDEX_HISTORY_DIR.glob("price_daily__*__SRC-YAHOO-INDEX.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, list):
            continue
        for row in payload:
            if row.get("index_id") and row.get("trade_date") and row.get("close") is not None:
                rows.append(row)
    return rows


def week_key(trade_date: str):
    d = date.fromisoformat(trade_date)
    iso = d.isocalendar()
    return iso.year, iso.week


def pct_change(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (float(current) / float(previous) - 1.0) * 100.0


def build_weekly(daily_rows):
    grouped = defaultdict(list)
    for row in daily_rows:
        grouped[row["index_id"]].append(row)

    all_weekly = []
    for index_id, rows in grouped.items():
        rows.sort(key=lambda r: r["trade_date"])

        by_week = defaultdict(list)
        for row in rows:
            by_week[week_key(row["trade_date"])].append(row)

        weekly_rows = []
        for (iso_year, iso_week), week_rows in sorted(by_week.items()):
            week_rows.sort(key=lambda r: r["trade_date"])
            first = week_rows[0]
            last = week_rows[-1]
            values = [float(r["high"]) for r in week_rows if r.get("high") is not None]
            lows = [float(r["low"]) for r in week_rows if r.get("low") is not None]
            volumes = [float(r["volume"]) for r in week_rows if r.get("volume") is not None]

            item = {
                "index_id": index_id,
                "index_symbol": last.get("index_symbol"),
                "index_name": last.get("index_name"),
                "index_name_en": last.get("index_name_en"),
                "market": last.get("market"),
                "currency": last.get("currency"),
                "week_year": iso_year,
                "week_number": iso_week,
                "week_start_date": first["trade_date"],
                "week_end_date": last["trade_date"],
                "observation_date": last["trade_date"],
                "trading_days": len(week_rows),
                "open": first.get("open"),
                "high": max(values) if values else None,
                "low": min(lows) if lows else None,
                "close": last.get("close"),
                "adjusted_close": last.get("adjusted_close"),
                "volume": sum(volumes) if volumes else None,
                "source_id": "SRC-DERIVED-INDEX-WEEKLY",
                "source_origin": "DERIVED_FROM_DAILY",
                "declared_upstream_source": last.get("declared_upstream_source"),
                "data_quality_status": "SOURCE_CONFIRMED",
                "license_gate": "REVIEW",
                "publication_scope": "INTERNAL_SNAPSHOT_ONLY",
                "derived_from_frequency": "DAILY",
                "derived_at": datetime.now(timezone.utc).isoformat(),
            }
            weekly_rows.append(item)

        previous_close = None
        prior_year_last_close = {}
        for item in weekly_rows:
            item["weekly_change_pct"] = pct_change(item["close"], previous_close)
            previous_close = item["close"]
            prior_year_last_close.setdefault(item["week_year"], item["close"])

        # Use the final weekly close of the prior calendar year as the YTD base.
        last_close_by_year = {}
        for item in weekly_rows:
            last_close_by_year[item["week_year"]] = item["close"]
        for item in weekly_rows:
            base = last_close_by_year.get(item["week_year"] - 1)
            item["ytd_pct"] = pct_change(item["close"], base)

        all_weekly.extend(weekly_rows)

    all_weekly.sort(key=lambda r: (r["index_id"], r["week_end_date"]))
    return all_weekly


def write_outputs(records, start_date, end_date):
    WEEKLY_PARTITION_ROOT.mkdir(parents=True, exist_ok=True)

    by_year = defaultdict(list)
    for row in records:
        by_year[row["week_year"]].append(row)

    for year, rows in by_year.items():
        path = WEEKLY_PARTITION_ROOT / str(year) / "index_weekly.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows) + "\n",
            encoding="utf-8",
        )

    history_path = WEEKLY_HISTORY_DIR / (
        f"index_weekly__{start_date}_{end_date}__SRC-DERIVED-INDEX-WEEKLY.json"
    )
    history_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return history_path


def git_commit(label):
    # GitHub Actions owns the commit/push step so derived-data writes do not
    # retrigger this workflow through its own output paths.
    return

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default="2026-09-29")
    args = ap.parse_args()

    daily = load_daily_records()
    records = build_weekly(daily)
    history_path = write_outputs(records, args.start, args.end)

    index_counts = defaultdict(int)
    for row in records:
        index_counts[row["index_id"]] += 1

    state = {
        "version": 1,
        "start_date": args.start,
        "end_date": args.end,
        "source_id": "SRC-DERIVED-INDEX-WEEKLY",
        "source_origin": "DERIVED_FROM_DAILY",
        "frequency": "WEEKLY",
        "record_count": len(records),
        "index_count": len(index_counts),
        "records_by_index": dict(sorted(index_counts.items())),
        "history_file": str(history_path.relative_to(ROOT)),
        "license_gate": "REVIEW",
        "publication_scope": "INTERNAL_SNAPSHOT_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    git_commit(f"{args.start}_{args.end}")
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
