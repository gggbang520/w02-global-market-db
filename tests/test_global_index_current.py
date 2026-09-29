import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "build_global_index_current",
    ROOT / "scripts/automation/build_global_index_current.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_row(trade_date, close, open_=None, high=None, low=None):
    return {
        "index_id": "TEST",
        "index_symbol": "T",
        "index_name": "Test",
        "index_name_en": "Test",
        "market": "Test",
        "currency": "USD",
        "trade_date": trade_date,
        "open": open_ if open_ is not None else close,
        "high": high if high is not None else close,
        "low": low if low is not None else close,
        "close": close,
        "volume": 10,
        "source_id": "SRC-YAHOO-INDEX",
        "source_origin": "AUTO_PROVIDER",
        "declared_upstream_source": "Test source",
        "data_quality_status": "SOURCE_CONFIRMED",
        "license_gate": "REVIEW",
        "publication_scope": "INTERNAL_SNAPSHOT_ONLY",
    }


def test_snapshot_uses_latest_and_previous_close():
    rows = [
        make_row("2025-01-06", 100),
        make_row("2025-01-10", 110),
    ]
    out = mod.build_snapshot({"TEST": rows})
    assert len(out) == 1
    item = out[0]
    assert item["observation_date"] == "2025-01-10"
    assert item["latest_close"] == 110
    assert item["daily_change_pct"] == 10.0
    assert item["week_change_pct"] == 10.0
    assert item["status"] == "SUCCESS"


def test_snapshot_month_and_ytd_base():
    rows = [
        make_row("2024-12-27", 100),
        make_row("2025-01-06", 110),
        make_row("2025-01-10", 120),
    ]
    out = mod.build_snapshot({"TEST": rows})
    item = out[0]
    assert item["month_change_pct"] == 20.0
    assert item["ytd_pct"] == 20.0


def test_single_observation_is_partial_and_preserves_null_changes():
    rows = [make_row("2026-09-29", 100)]
    out = mod.build_snapshot({"TEST": rows})
    item = out[0]
    assert item["status"] == "PARTIAL"
    assert item["daily_change_pct"] is None
    assert item["week_change_pct"] is None
    assert item["month_change_pct"] is None
