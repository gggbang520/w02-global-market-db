from __future__ import annotations

import argparse
import io
import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from scripts.providers.provider_registry import get_provider

ROOT = Path(__file__).resolve().parents[2]
MASTER_PATH = ROOT / "data/standardized/index_master.json"
HISTORY_DIR = ROOT / "data/history/DATA-2026-W39/indices"
PARTITION_ROOT = ROOT / "data/standardized/partitions/SRC-YAHOO-INDEX"
REPORT_PATH = ROOT / "reports/index/global_index_fetch_state.json"


def load_master():
    return json.loads(MASTER_PATH.read_text(encoding="utf-8"))


def fetch_one(symbol: str, start: date, end: date):
    provider = get_provider("SRC-YAHOO-INDEX")

    return provider.fetch_history(
        symbol,
        start,
        end
    )


def validate(df):
    invalid = []
    valid = []
    for _, r in df.iterrows():
        errs = []
        vals = [r.get(k) for k in ("open", "high", "low", "close")]
        if any(pd.isna(v) for v in vals):
            errs.append("OHLC_MISSING")
        else:
            o, h, l, c = [float(v) for v in vals]
            if not (h >= l and h >= o and h >= c and l <= o and l <= c and c >= 0):
                errs.append("OHLC_INVALID")
        if not pd.isna(r.get("volume")) and float(r["volume"]) < 0:
            errs.append("VOLUME_INVALID")
        item = r.to_dict()
        item["validation_errors"] = errs
        (invalid if errs else valid).append(item)
    return valid, invalid


def serialize_record(item, meta):
    return {
        "index_id": meta["index_id"],
        "index_symbol": meta.get("yahoo_symbol"),
        "index_name": meta["index_name"],
        "index_name_en": meta["index_name_en"],
        "market": meta["market"],
        "currency": meta["currency"],
        "trade_date": item["trade_date"],
        "open": None if pd.isna(item["open"]) else float(item["open"]),
        "high": None if pd.isna(item["high"]) else float(item["high"]),
        "low": None if pd.isna(item["low"]) else float(item["low"]),
        "close": None if pd.isna(item["close"]) else float(item["close"]),
        "adjusted_close": None if pd.isna(item["adjusted_close"]) else float(item["adjusted_close"]),
        "price_type": "RAW_CLOSE",
        "volume": None if pd.isna(item["volume"]) else float(item["volume"]),
        "source_id": "SRC-YAHOO-INDEX",
        "source_origin": "AUTO_PROVIDER",
        "declared_upstream_source": meta.get("declared_upstream_source"),
        "data_quality_status": "SOURCE_CONFIRMED",
        "license_gate": "REVIEW",
        "publication_scope": "INTERNAL_SNAPSHOT_ONLY",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def write_outputs(meta, records, start, end, invalid_count):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    PARTITION_ROOT.mkdir(parents=True, exist_ok=True)

    history_path = HISTORY_DIR / f"price_daily__{meta['index_id']}__{start}_{end}__SRC-YAHOO-INDEX.json"
    history_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    buckets = {}
    for r in records:
        buckets.setdefault((r["trade_date"][:4], r["trade_date"][5:7]), []).append(r)
    for (year, month), rows in buckets.items():
        p = PARTITION_ROOT / year / month / "index_daily.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    return history_path


def git_commit(label):
    subprocess.run(["git", "add", "data/history", "data/standardized/partitions/SRC-YAHOO-INDEX", "reports/index/global_index_fetch_state.json"], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    subprocess.run(["git", "config", "user.name", "W02 Data Bot"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", f"data: fetch global index history {label}"], cwd=ROOT, check=True)
    subprocess.run(["git", "push"], cwd=ROOT, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", required=True)
    args = ap.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if start > end:
        raise SystemExit("--start must be <= --end")

    master = load_master()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {"version": 1, "start_date": args.start, "end_date": args.end, "indexes": {}}

    for meta in master:
        symbol = meta.get("yahoo_symbol")
        if not symbol:
            state["indexes"][meta["index_id"]] = {
                "status": "MANUAL_PENDING",
                "reason": "official metadata registered; no Yahoo symbol used as proxy",
                "official_index_code": meta.get("official_index_code"),
            }
            continue

        try:
            df = fetch_one(symbol, start, end)
            if df.empty:
                state["indexes"][meta["index_id"]] = {"status": "ACCESS_OR_NO_DATA", "yahoo_symbol": symbol}
                continue
            valid, invalid = validate(df)
            records = [serialize_record(x, meta) for x in valid]
            hp = write_outputs(meta, records, start, end, len(invalid))
            state["indexes"][meta["index_id"]] = {
                "status": "SUCCESS" if not invalid and len(records) >= 1000 else "PARTIAL",
                "yahoo_symbol": symbol,
                "records": len(records),
                "invalid_rows": len(invalid),
                "trade_date_min": records[0]["trade_date"] if records else None,
                "trade_date_max": records[-1]["trade_date"] if records else None,
                "history_file": str(hp.relative_to(ROOT)),
                "source_id": "SRC-YAHOO-INDEX",
                "declared_upstream_source": meta.get("declared_upstream_source"),
                "license_gate": "REVIEW",
                "publication_scope": "INTERNAL_SNAPSHOT_ONLY",
            }
        except Exception as e:
            state["indexes"][meta["index_id"]] = {
                "status": "FAILED",
                "yahoo_symbol": symbol,
                "error": str(e),
            }

    REPORT_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    label = f"{start}_{end}"
    git_commit(label)
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
