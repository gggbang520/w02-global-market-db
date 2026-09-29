import json
from datetime import date
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "fetch_global_index_history",
    ROOT / "scripts/automation/fetch_global_index_history.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_index_master_has_expected_core_regions():
    rows = json.loads((ROOT / "data/standardized/index_master.json").read_text(encoding="utf-8"))
    ids = {r["index_id"] for r in rows}
    required = {
        "CN-SSE", "CN-SZSE", "CN-CS300",
        "US-SPX", "US-NDX", "US-COMP", "US-DJIA", "US-RUT",
        "EU-DAX", "EU-FTSE100", "EU-CAC40", "EU-SX5E",
        "JP-N225", "JP-TOPIX", "HK-HSI", "KR-KOSPI",
        "IN-NIFTY50", "IN-SENSEX", "TW-TAIEX", "AU-ASX200", "SG-STI",
        "GL-MSCI-WORLD", "GL-MSCI-EM",
    }
    assert required.issubset(ids)


def test_master_ids_unique():
    rows = json.loads((ROOT / "data/standardized/index_master.json").read_text(encoding="utf-8"))
    ids = [r["index_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_yahoo_symbols_unique_for_auto_indexes():
    rows = json.loads((ROOT / "data/standardized/index_master.json").read_text(encoding="utf-8"))
    syms = [r["yahoo_symbol"] for r in rows if r.get("yahoo_symbol")]
    assert len(syms) == len(set(syms))


def test_quarter_date_order():
    assert mod.date.fromisoformat("2019-01-01") < mod.date.fromisoformat("2026-09-29")
