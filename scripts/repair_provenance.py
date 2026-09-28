from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STD = ROOT / "data/standardized/partitions"
SOURCE = "SRC-GITHUB-TUSHARE-ARCHIVE"
TARGET = STD / "SRC-GITHUB-TUSHARE-ARCHIVE_REPAIRED"

TARGET.mkdir(parents=True, exist_ok=True)

def repair_partition(rel):
    p = STD / rel
    if not p.exists():
        return {"found": False, "records": 0}
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if not line.strip():
            continue
        r = json.loads(line)
        r["source_id"] = SOURCE
        r["source_origin"] = "AUTO_PROVIDER"
        out.append(r)
    # group output by original year/month encoded in path
    parts = rel.split("/")
    year, month = parts[-3], parts[-2]
    dest = TARGET / year / month
    dest.mkdir(parents=True, exist_ok=True)
    out.sort(key=lambda x: (x.get("trade_date",""), x.get("exchange_mic",""), x.get("ticker","")))
    (dest / "stock_daily.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in out),
        encoding="utf-8",
    )
    return {"found": True, "records": len(out), "year": year, "month": month}

def main():
    targets = [
        "2020/01/SRC-MANUAL-FILE/stock_daily.jsonl",
        "2020/02/SRC-MANUAL-FILE/stock_daily.jsonl",
        "2020/03/SRC-MANUAL-FILE/stock_daily.jsonl",
        "2021/01/SRC-MANUAL-FILE/stock_daily.jsonl",
    ]
    results = [repair_partition(x) for x in targets]
    repaired = sum(x.get("records", 0) for x in results)

    # Replace the temporary root with the canonical partition layout.
    canonical = STD / SOURCE
    for p in TARGET.rglob("stock_daily.jsonl"):
        parts = p.parts[-3:]
        year, month = parts[0], parts[1]
        dest = canonical / year / month
        dest.mkdir(parents=True, exist_ok=True)
        dest.joinpath("stock_daily.jsonl").write_bytes(p.read_bytes())

    # Remove only the four known auto-ingested manual-labelled partitions.
    removed = []
    for rel in targets:
        p = STD / rel
        if p.exists():
            p.unlink()
            # remove empty parents
            parent = p.parent
            while parent != STD and parent.exists():
                try:
                    parent.rmdir()
                    parent = parent.parent
                except OSError:
                    break
            removed.append(rel)

    # Clean temporary repair tree.
    if TARGET.exists():
        for p in sorted(TARGET.rglob("*"), key=lambda x: len(x.parts), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                try: p.rmdir()
                except OSError: pass

    report = {
        "status": "SUCCESS",
        "repaired_records": repaired,
        "source_id": SOURCE,
        "source_origin": "AUTO_PROVIDER",
        "repaired_source_partitions": results,
        "removed_manual_label_partitions": removed,
        "reason": "These records originated from GitHub Actions automated retrieval but were mislabeled by the generic manual-file parser."
    }
    out = ROOT / "reports/quality/provenance_repair.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
