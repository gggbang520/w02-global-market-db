import argparse
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from common import ROOT, load_csi300_listings

SOURCE_ID = "SRC-GITHUB-TUSHARE-ARCHIVE"
REPO = "shaocongWu/Multivariate_Stock_Time_Series_Dataset"
BRANCH = "main"

def stem_code(stem):
    s = re.sub(r"[^0-9]", "", stem.upper())
    return s.zfill(6) if s else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-01-18")
    ap.add_argument("--end", default="2021-01-29")
    args = ap.parse_args()

    listings = load_csi300_listings()
    wanted = {x["ticker"]: x for x in listings}

    tree_url = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
    tree = requests.get(tree_url, timeout=30, headers={"Accept":"application/vnd.github+json"})
    tree.raise_for_status()
    items = tree.json().get("tree", [])

    files = {}
    for item in items:
        p = item.get("path","")
        if p.lower().endswith(".csv"):
            code = stem_code(Path(p).stem)
            if code in wanted:
                files[code] = p

    rows = []
    failures = []

    for code, path in sorted(files.items()):
        url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"
        try:
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            df = pd.read_csv(io.BytesIO(r.content))
            cols = {str(c).strip().lower(): c for c in df.columns}

            def pick(*names):
                for n in names:
                    if n in cols:
                        return cols[n]
                return None

            dcol = pick("date","trade_date","datetime")
            ccol = pick("close")
            if not dcol or not ccol:
                raise ValueError("date/close columns not found")

            df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
            df = df[df[dcol].notna()].copy()
            df["trade_date"] = df[dcol].dt.date.astype(str)
            df = df[(df["trade_date"] >= args.start) & (df["trade_date"] <= args.end)]

            meta = wanted[code]
            rows.append(pd.DataFrame({
                "ticker": code,
                "exchange": meta["exchange"],
                "trade_date": df["trade_date"],
                "open": pd.to_numeric(df[pick("open")], errors="coerce") if pick("open") else None,
                "high": pd.to_numeric(df[pick("high")], errors="coerce") if pick("high") else None,
                "low": pd.to_numeric(df[pick("low")], errors="coerce") if pick("low") else None,
                "close": pd.to_numeric(df[ccol], errors="coerce"),
                "adjusted_close": None,
                "price_type": "RAW_CLOSE",
                "volume": pd.to_numeric(df[pick("volume","vol")], errors="coerce") if pick("volume","vol") else None,
                "turnover": pd.to_numeric(df[pick("turnover","amount","amt")], errors="coerce") if pick("turnover","amount","amt") else None,
                "currency": "CNY",
            }))
        except Exception as e:
            failures.append({"ticker": code, "path": path, "error": str(e)})

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not out.empty:
        out = out.drop_duplicates(["ticker","exchange","trade_date"]).sort_values(["trade_date","exchange","ticker"])

    dest = ROOT / "data/raw/inbox/market"
    meta = ROOT / "data/raw/_metadata"
    dest.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = dest / f"{SOURCE_ID}__stock_daily__CN__{args.start}_{args.end}__{stamp}.csv"
    out.to_csv(path, index=False, encoding="utf-8")

    report = {
        "source_id": SOURCE_ID,
        "source_origin": "AUTO_PROVIDER",
        "declared_upstream_source": "Tushare Pro",
        "verification_status": "SOURCE_DECLARED_NOT_DIRECTLY_RETRIEVED",
        "repository": f"https://github.com/{REPO}",
        "dataset": "STOCK_DAILY",
        "market": "CN",
        "start_date": args.start,
        "end_date": args.end,
        "requested_listings": len(listings),
        "matched_csv_files": len(files),
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
