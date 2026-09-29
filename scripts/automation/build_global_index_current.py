from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_HISTORY_DIR = ROOT / "data/history/DATA-2026-W39/indices"
SNAPSHOT_PATH = ROOT / "data/standardized/index_current_snapshot.json"
REPORT_PATH = ROOT / "reports/index/global_index_current_state.json"


def pct_change(current, base):
    if current is None or base in (None, 0):
        return None
    return (float(current) / float(base) - 1.0) * 100.0


def load_daily_records():
    grouped = defaultdict(dict)
    for path in sorted(INDEX_HISTORY_DIR.glob("price_daily__*__SRC-YAHOO-INDEX.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, list):
            continue
        for row in payload:
            index_id = row.get("index_id")
            trade_date = row.get("trade_date")
            close = row.get("close")
            if not index_id or not trade_date or close is None:
                continue
            grouped[index_id][trade_date] = row
    return {
        index_id: sorted(rows.values(), key=lambda r: r["trade_date"])
        for index_id, rows in grouped.items()
    }


def build_snapshot(index_rows, snapshot_date=None):
    snapshots = []
    target_date = date.fromisoformat(snapshot_date) if snapshot_date else None

    for index_id, rows in sorted(index_rows.items()):
        usable = [
            r for r in rows
            if target_date is None or date.fromisoformat(r["trade_date"]) <= target_date
        ]
        if not usable:
            continue

        latest = usable[-1]
        latest_date = latest["trade_date"]
        latest_close = latest.get("close")

        previous = usable[-2] if len(usable) >= 2 else None
        daily_change = pct_change(latest_close, previous.get("close") if previous else None)

        latest_day = date.fromisoformat(latest_date)
        iso_year, iso_week, _ = latest_day.isocalendar()
        week_rows = [
            r for r in usable
            if date.fromisoformat(r["trade_date"]).isocalendar()[:2] == (iso_year, iso_week)
        ]
        month_rows = [
            r for r in usable
            if date.fromisoformat(r["trade_date"]).year == latest_day.year
            and date.fromisoformat(r["trade_date"]).month == latest_day.month
        ]

        week_base = week_rows[0].get("close") if week_rows else None
        month_base = month_rows[0].get("close") if month_rows else None

        prior_year_rows = [
            r for r in usable
            if date.fromisoformat(r["trade_date"]).year == latest_day.year - 1
        ]
        ytd_base = prior_year_rows[-1].get("close") if prior_year_rows else None

        trailing = usable[-252:]
        highs = [float(r["high"]) for r in trailing if r.get("high") is not None]
        lows = [float(r["low"]) for r in trailing if r.get("low") is not None]

        status = "SUCCESS" if len(usable) >= 2 else "PARTIAL"

        snapshots.append({
            "index_id": index_id,
            "index_symbol": latest.get("index_symbol"),
            "index_name": latest.get("index_name"),
            "index_name_en": latest.get("index_name_en"),
            "market": latest.get("market"),
            "currency": latest.get("currency"),
            "observation_date": latest_date,
            "latest_close": latest_close,
            "latest_open": latest.get("open"),
            "latest_high": latest.get("high"),
            "latest_low": latest.get("low"),
            "daily_change_pct": daily_change,
            "week_change_pct": pct_change(latest_close, week_base) if len(week_rows) >= 2 else None,
            "month_change_pct": pct_change(latest_close, month_base) if len(month_rows) >= 2 else None,
            "ytd_pct": pct_change(latest_close, ytd_base),
            "trailing_252d_high": max(highs) if highs else None,
            "trailing_252d_low": min(lows) if lows else None,
            "trading_days_available": len(usable),
            "status": status,
            "source_id": latest.get("source_id"),
            "source_origin": latest.get("source_origin"),
            "declared_upstream_source": latest.get("declared_upstream_source"),
            "data_quality_status": latest.get("data_quality_status"),
            "license_gate": latest.get("license_gate"),
            "publication_scope": latest.get("publication_scope"),
            "snapshot_generated_at": datetime.now(timezone.utc).isoformat(),
        })

    return snapshots


def write_snapshot(rows):
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_report(rows):
    counts = defaultdict(int)
    for row in rows:
        counts[row["status"]] += 1

    state = {
        "version": 1,
        "frequency": "CURRENT_SNAPSHOT",
        "record_count": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "snapshot_file": str(SNAPSHOT_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def git_commit(label):
    return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()

    index_rows = load_daily_records()
    rows = build_snapshot(index_rows, args.as_of)
    write_snapshot(rows)
    state = write_report(rows)
    git_commit(args.as_of or "latest")

    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
