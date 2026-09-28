from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    report = {"status":"SUCCESS","raw_market":{},"history":{},"standardized":{},"checks":{}}

    raw = ROOT / "data/raw/inbox/market"
    raw_groups = defaultdict(list)
    if raw.exists():
        for p in raw.iterdir():
            if p.is_file():
                raw_groups[file_sha(p)].append(str(p.relative_to(ROOT)))
    raw_dupes = {k:v for k,v in raw_groups.items() if len(v)>1}
    report["raw_market"] = {
        "file_count": sum(len(v) for v in raw_groups.values()),
        "sha_group_count": len(raw_groups),
        "exact_duplicate_group_count": len(raw_dupes),
        "exact_duplicate_groups": raw_dupes,
    }

    history = ROOT / "data/history"
    batches = []
    key_to_batches = defaultdict(list)
    if history.exists():
        for p in sorted(history.rglob("price_daily__*__SRC-GITHUB-TUSHARE-ARCHIVE.json")):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                batches.append({"file":str(p.relative_to(ROOT)),"parse_status":"FAILED","error":str(e)})
                continue
            records = obj if isinstance(obj,list) else obj.get("records",[])
            dates = sorted({r.get("trade_date") for r in records if r.get("trade_date")})
            listings = sorted({r.get("listing_id") for r in records if r.get("listing_id")})
            for r in records:
                k=(r.get("listing_id"),r.get("trade_date"),r.get("source_id"),r.get("price_type"))
                if k[0] and k[1] and k[2]:
                    key_to_batches[k].append(str(p.relative_to(ROOT)))
            batches.append({
                "file":str(p.relative_to(ROOT)),
                "records":len(records),
                "distinct_listings":len(listings),
                "distinct_trade_dates":len(dates),
                "trade_date_min":dates[0] if dates else None,
                "trade_date_max":dates[-1] if dates else None,
                "size_bytes":p.stat().st_size
            })
    overlaps = {str(k):v for k,v in key_to_batches.items() if len(v)>1}
    report["history"]={
        "batch_file_count":len(batches),
        "batch_record_sum":sum(x.get("records",0) for x in batches),
        "overlap_key_count":len(overlaps),
        "batches":batches,
        "overlap_samples":list(overlaps.items())[:50]
    }

    std = ROOT / "data/standardized/partitions/SRC-GITHUB-TUSHARE-ARCHIVE"
    canonical=[]; legacy=[]
    if std.exists():
        for p in std.rglob("stock_daily.jsonl"):
            rel=p.relative_to(std).parts
            if len(rel)==3 and len(rel[0])==4 and rel[0].isdigit() and len(rel[1])==2 and rel[1].isdigit():
                canonical.append(str(p.relative_to(ROOT)))
            else:
                legacy.append(str(p.relative_to(ROOT)))
    report["standardized"]={
        "canonical_partition_count":len(canonical),
        "canonical_partitions":sorted(canonical),
        "legacy_partition_file_count":len(legacy),
        "legacy_partition_files":sorted(legacy),
    }
    report["checks"]={
        "raw_preserved":raw.exists(),
        "history_preserved":history.exists(),
        "canonical_standardized_source_present":std.exists(),
        "has_exact_duplicate_raw_files":bool(raw_dupes),
        "has_history_overlaps":bool(overlaps),
        "has_legacy_standardized_files":bool(legacy),
    }
    out=ROOT/"reports/quality/final_audit.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    raise SystemExit(main())
