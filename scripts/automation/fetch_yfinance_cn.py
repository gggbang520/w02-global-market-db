import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from common import ROOT, load_csi300_listings, yahoo_symbol

SOURCE_ID = "SRC-YAHOO-YFINANCE"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--batch-size", type=int, default=40)
    ap.add_argument("--sleep", type=float, default=1.5)
    args = ap.parse_args()

    listings = load_csi300_listings()
    mapping = {yahoo_symbol(x["ticker"], x["exchange"]): x for x in listings}
    symbols = list(mapping)

    end = datetime.now(timezone.utc).date() + timedelta(days=1)
    start = end - timedelta(days=max(args.days, 7))

    rows = []
    failures = []

    for i in range(0, len(symbols), args.batch_size):
        batch = symbols[i:i+args.batch_size]
        try:
            df = yf.download(
                batch,
                start=start.isoformat(),
                end=end.isoformat(),
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
                group_by="column",
            )
            if df.empty:
                continue

            if not isinstance(df.columns, pd.MultiIndex):
                continue

            level0 = set(df.columns.get_level_values(0))
            fields = {"Open","High","Low","Close","Adj Close","Volume"}

            if level0.intersection(fields):
                tickers = sorted(set(df.columns.get_level_values(1)))
                for sym in tickers:
                    if sym not in mapping:
                        continue
                    sub = df.xs(sym, axis=1, level=1, drop_level=True)
                    meta = mapping[sym]
                    for dt, r in sub.iterrows():
                        close = r.get("Close")
                        if pd.isna(close):
                            continue
                        rows.append({
                            "ticker": meta["ticker"],
                            "exchange": meta["exchange"],
                            "trade_date": pd.Timestamp(dt).date().isoformat(),
                            "open": None if pd.isna(r.get("Open")) else float(r.get("Open")),
                            "high": None if pd.isna(r.get("High")) else float(r.get("High")),
                            "low": None if pd.isna(r.get("Low")) else float(r.get("Low")),
                            "close": float(close),
                            "adjusted_close": None if pd.isna(r.get("Adj Close")) else float(r.get("Adj Close")),
                            "price_type": "RAW_CLOSE",
                            "volume": None if pd.isna(r.get("Volume")) else float(r.get("Volume")),
                            "turnover": None,
                            "currency": "CNY",
                        })
        except Exception as e:
            failures.append({"batch_start": i, "error": str(e)})
        time.sleep(args.sleep)

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.drop_duplicates(["ticker","exchange","trade_date"]).sort_values(["trade_date","exchange","ticker"])

    dest = ROOT / "data/raw/inbox/market"
    meta = ROOT / "data/raw/_metadata"
    dest.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = dest / f"{SOURCE_ID}__stock_daily__CN__{start.isoformat()}_{(end-timedelta(days=1)).isoformat()}__{stamp}.csv"
    out.to_csv(path, index=False, encoding="utf-8")

    report = {
        "source_id": SOURCE_ID,
        "source_origin": "AUTO_PROVIDER",
        "provider": "yfinance / Yahoo Finance",
        "dataset": "STOCK_DAILY",
        "market": "CN",
        "start_date": start.isoformat(),
        "end_date": (end-timedelta(days=1)).isoformat(),
        "requested_listings": len(listings),
        "downloaded_rows": int(len(out)),
        "distinct_listings": int(out["ticker"].nunique()) if not out.empty else 0,
        "distinct_trade_dates": int(out["trade_date"].nunique()) if not out.empty else 0,
        "failures": failures,
        "license_gate": "REVIEW",
        "publication_scope": "INTERNAL_SNAPSHOT_ONLY",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    (meta / (path.stem + ".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
