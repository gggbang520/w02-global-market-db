from __future__ import annotations

import argparse
import io
import json
import subprocess
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/automation"))

from common import ROOT
from scripts.ingest_market_data import resolve_listing, validate
from scripts.providers.manual_file import ManualFileProvider

SOURCE_ID = "SRC-YAHOO-YFINANCE"
MEMBERSHIP_SOURCE = "SRC-CSI300-SECONDARY"
MEMBERSHIP_URL = "https://raw.githubusercontent.com/unliftedq/index-constitution/main/history/csi300.csv"
STATE_PATH = ROOT / "reports/backfill/csi300_yahoo_backfill_state.json"
HISTORY_DIR = ROOT / "data/history/DATA-2026-W39/stocks"
PARTITION_ROOT = ROOT / "data/standardized/partitions"


def quarter_ranges(start: date, end: date):
    out = []
    cursor = date(start.year, ((start.month - 1) // 3) * 3 + 1, 1)
    while cursor <= end:
        q_end = {
            1: date(cursor.year, 3, 31),
            4: date(cursor.year, 6, 30),
            7: date(cursor.year, 9, 30),
            10: date(cursor.year, 12, 31),
        }[cursor.month]
        s, e = max(start, cursor), min(end, q_end)
        if s <= e:
            out.append((f"{cursor.year}Q{((cursor.month - 1)//3)+1}", s, e))
        cursor = date(cursor.year + 1, 1, 1) if cursor.month == 10 else date(cursor.year, cursor.month + 3, 1)
    return out


def load_membership():
    r = requests.get(MEMBERSHIP_URL, timeout=45)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    df.columns = [str(c).strip().lower() for c in df.columns]
    df["opt-in"] = pd.to_datetime(df["opt-in"], errors="coerce")
    df["opt-out"] = pd.to_datetime(df["opt-out"], errors="coerce")
    df["ticker"] = df["symbol"].astype(str).str.extract(r"(\d{6})", expand=False)
    df["exchange_mic"] = df["symbol"].astype(str).str.upper().map(
        lambda s: "XSHG" if s.startswith("SH") else ("XSHE" if s.startswith("SZ") else None)
    )
    return df.dropna(subset=["ticker", "exchange_mic", "opt-in"]).copy()


def intervals_for(df, start, end):
    active = df[(df["opt-in"] <= pd.Timestamp(end)) &
                (df["opt-out"].isna() | (df["opt-out"] >= pd.Timestamp(start)))]
    out = {}
    for _, r in active.iterrows():
        key = (r["exchange_mic"], r["ticker"])
        out.setdefault(key, []).append((r["opt-in"].date(),
                                         r["opt-out"].date() if pd.notna(r["opt-out"]) else None))
    return out


def membership_allows(intervals, exchange, ticker, dt):
    return any(s <= dt and (e is None or dt <= e)
               for s, e in intervals.get((exchange, ticker), []))


def yahoo_symbol(ticker, exchange):
    return f"{ticker}{'.SS' if exchange == 'XSHG' else '.SZ'}"


def fetch_prices(symbols, start, end, batch_size, sleep_seconds):
    rows, failures = [], []

    def one_pass(batch, pause):
        local_rows, local_failures = [], []
        for i in range(0, len(batch), batch_size):
            group = batch[i:i + batch_size]
            try:
                df = yf.download(
                    group,
                    start=start.isoformat(),
                    end=(end + timedelta(days=1)).isoformat(),
                    auto_adjust=False,
                    actions=False,
                    progress=False,
                    threads=False,
                    group_by="column",
                )
                if df.empty or not isinstance(df.columns, pd.MultiIndex):
                    raise ValueError("Yahoo returned empty/non-multiindex batch")

                fields = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
                ticker_level = 1 if set(map(str, df.columns.get_level_values(0))) & fields else 0
                available = set(map(str, df.columns.get_level_values(ticker_level)))

                for sym in group:
                    if sym not in available:
                        local_failures.append({"symbol": sym, "error": "ticker_missing_in_batch"})
                        continue
                    sub = df.xs(sym, axis=1, level=ticker_level, drop_level=True)
                    if "Close" not in sub.columns:
                        local_failures.append({"symbol": sym, "error": "close_missing"})
                        continue

                    for dt, r in sub.iterrows():
                        close = r.get("Close")
                        if pd.isna(close):
                            continue
                        local_rows.append({
                            "ticker": sym[:6],
                            "yahoo_symbol": sym,
                            "trade_date": pd.Timestamp(dt).date().isoformat(),
                            "open": None if pd.isna(r.get("Open")) else float(r["Open"]),
                            "high": None if pd.isna(r.get("High")) else float(r["High"]),
                            "low": None if pd.isna(r.get("Low")) else float(r["Low"]),
                            "close": float(r["Close"]),
                            "adjusted_close": None if pd.isna(r.get("Adj Close")) else float(r["Adj Close"]),
                            "price_type": "RAW_CLOSE",
                            "volume": None if pd.isna(r.get("Volume")) else float(r["Volume"]),
                            "turnover": None,
                            "currency": "CNY",
                        })
            except Exception as e:
                local_failures.extend({"symbol": s, "error": str(e)} for s in group)
            if pause:
                time.sleep(pause)
        return local_rows, local_failures

    rows, first_failures = one_pass(symbols, sleep_seconds)

    # Retry missing symbols individually. This catches transient Yahoo batch failures
    # without throwing away the rest of a quarter.
    retry_symbols = sorted({x["symbol"] for x in first_failures})
    for sym in retry_symbols:
        recovered, retry_failures = one_pass([sym], max(sleep_seconds, 2.0))
        if recovered:
            rows.extend(recovered)
        else:
            failures.extend(retry_failures or [{"symbol": sym, "error": "retry_failed"}])

    # Retain only failures that still have no downloaded rows.
    recovered_symbols = {r["yahoo_symbol"] for r in rows}
    failures = [x for x in failures if x.get("symbol") not in recovered_symbols]

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.drop_duplicates(["ticker", "trade_date", "yahoo_symbol"]).sort_values(
            ["trade_date", "ticker"]
        )
    return out, failures

def write_quarter(q, start, end, membership, records, raw, failures):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir, mem_dir, meta_dir = ROOT/"data/raw/inbox/market", ROOT/"data/raw/cn", ROOT/"data/raw/_metadata"
    for d in (raw_dir, mem_dir, meta_dir, HISTORY_DIR):
        d.mkdir(parents=True, exist_ok=True)

    mem_path = mem_dir / f"{MEMBERSHIP_SOURCE}__index_constituents__CN__{start}_{end}__{stamp}.csv"
    raw_path = raw_dir / f"{SOURCE_ID}__stock_daily__CN__HISTORICAL_CSI300__{start}_{end}__{stamp}.csv"
    hist_path = HISTORY_DIR / f"price_daily__{start}_{end}__{SOURCE_ID}.json"
    mem_snapshot = membership[(membership["opt-in"].dt.date <= end) &
                              (membership["opt-out"].isna() | (membership["opt-out"].dt.date >= start))]
    mem_snapshot.to_csv(mem_path, index=False, encoding="utf-8-sig")
    raw.to_csv(raw_path, index=False, encoding="utf-8")
    hist_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    buckets = {}
    for r in records:
        k = (r["trade_date"][:4], r["trade_date"][5:7])
        buckets.setdefault(k, []).append(r)
    for (year, month), rows in buckets.items():
        p = PARTITION_ROOT / SOURCE_ID / year / month / "stock_daily.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    report = {
        "quarter": q, "status": "PARTIAL" if (failures) else "SUCCESS",
        "source_id": SOURCE_ID, "source_origin": "AUTO_PROVIDER",
        "provider": "yfinance / Yahoo Finance", "declared_upstream_source": "Yahoo Finance",
        "historical_universe_source": MEMBERSHIP_SOURCE, "historical_universe_url": MEMBERSHIP_URL,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "membership_codes_considered": int(len(mem_snapshot)),
        "raw_rows": int(len(raw)), "standardized_rows": int(len(records)),
        "distinct_listings": int(len({(r["exchange_mic"], r["ticker"]) for r in records})),
        "distinct_trade_dates": int(len({r["trade_date"] for r in records})),
        "download_failures": failures, "license_gate": "REVIEW",
        "publication_scope": "INTERNAL_SNAPSHOT_ONLY",
        "raw_file": str(raw_path.relative_to(ROOT)),
        "history_file": str(hist_path.relative_to(ROOT)),
        "membership_file": str(mem_path.relative_to(ROOT)),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    rp = ROOT / "reports/backfill" / f"csi300_yahoo_{q}.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def git_commit(q):
    subprocess.run(["git", "add", "data/", "reports/backfill/"], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    subprocess.run(["git", "config", "user.name", "W02 Data Bot"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", f"data: backfill CSI300 {q} via Yahoo"], cwd=ROOT, check=True)
    subprocess.run(["git", "push"], cwd=ROOT, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--batch-size", type=int, default=40)
    ap.add_argument("--sleep", type=float, default=1.5)
    args = ap.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if start > end:
        raise SystemExit("--start must be <= --end")

    membership = load_membership()
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {"version": 1, "quarters": {}}

    for q, qs, qe in quarter_ranges(start, end):
        prev = state["quarters"].get(q, {})
        if (
            prev.get("status") == "SUCCESS"
            and prev.get("end_date") == qe.isoformat()
            and prev.get("validation_status", "PASS") == "PASS"
            and not prev.get("download_failures")
        ):
            print(f"SKIP {q}")
            continue

        state["quarters"][q] = {"status": "RUNNING", "start_date": qs.isoformat(), "end_date": qe.isoformat()}
        save_state(state)

        intervals = intervals_for(membership, qs, qe)
        symbols = [yahoo_symbol(t, ex) for ex, t in sorted(intervals)]
        prices, failures = fetch_prices(symbols, qs, qe, args.batch_size, args.sleep)
        if prices.empty:
            state["quarters"][q] = {"status": "FAILED", "start_date": qs.isoformat(), "end_date": qe.isoformat(), "error": "zero Yahoo rows"}
            save_state(state)
            raise RuntimeError(f"{q}: zero Yahoo rows")

        prices["dt"] = pd.to_datetime(prices["trade_date"]).dt.date
        mask = [membership_allows(intervals, "XSHG" if s.endswith(".SS") else "XSHE", s[:6], d)
                for s, d in zip(prices["yahoo_symbol"], prices["dt"])]
        prices = prices.loc[mask].drop(columns=["dt"]).drop_duplicates(["ticker", "trade_date"])

        if prices.empty:
            raise RuntimeError(f"{q}: all rows failed PIT membership filtering")

        provider = ManualFileProvider(ROOT/"_virtual.csv", source_id=SOURCE_ID, source_origin="AUTO_PROVIDER")
        normalized = provider.normalize(prices.to_dict("records"))
        resolved = resolve_listing(normalized, allow_synthetic_historical=True)
        checked = validate(resolved)
        if not checked["valid"]:
            state["quarters"][q] = {
                "status": "FAILED",
                "start_date": qs.isoformat(),
                "end_date": qe.isoformat(),
                "error": (
                    f"no publishable records: invalid={len(checked['invalid'])}, "
                    f"duplicate={len(checked['duplicate'])}, review={len(checked['review'])}, "
                    f"download_failures={len(failures)}"
                ),
            }
            save_state(state)
            raise RuntimeError(f"{q}: no publishable records")

        records = sorted(
            checked["valid"],
            key=lambda r: (r["trade_date"], r["exchange_mic"], r["ticker"])
        )
        report = write_quarter(q, qs, qe, membership, records, prices, failures)
        report.update({
            "validation_invalid_rows": len(checked["invalid"]),
            "validation_duplicate_rows": len(checked["duplicate"]),
            "validation_review_rows": len(checked["review"]),
            "validation_status": (
                "PASS"
                if not (checked["invalid"] or checked["duplicate"] or checked["review"] or failures)
                else "PARTIAL"
            ),
        })
        if report["validation_status"] == "PARTIAL":
            report["status"] = "PARTIAL"
        state["quarters"][q] = report
        save_state(state)
        subprocess.run(["python", "-m", "pytest", "-q"], cwd=ROOT, check=True)
        git_commit(q)
        print(json.dumps(report, ensure_ascii=False, indent=2))

    save_state(state)


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
