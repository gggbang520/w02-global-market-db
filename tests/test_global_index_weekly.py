import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "build_global_index_weekly",
    ROOT / "scripts/automation/build_global_index_weekly.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_build_weekly_uses_first_open_last_close_and_weekly_high_low():
    rows = [
        {
            "index_id": "TEST",
            "index_symbol": "T",
            "index_name": "Test",
            "index_name_en": "Test",
            "market": "Test",
            "currency": "USD",
            "trade_date": "2025-01-06",
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 104,
            "adjusted_close": 104,
            "volume": 10,
            "declared_upstream_source": "Test source",
        },
        {
            "index_id": "TEST",
            "index_symbol": "T",
            "index_name": "Test",
            "index_name_en": "Test",
            "market": "Test",
            "currency": "USD",
            "trade_date": "2025-01-10",
            "open": 104,
            "high": 108,
            "low": 101,
            "close": 107,
            "adjusted_close": 107,
            "volume": 20,
            "declared_upstream_source": "Test source",
        },
    ]
    out = mod.build_weekly(rows)
    assert len(out) == 1
    item = out[0]
    assert item["week_start_date"] == "2025-01-06"
    assert item["week_end_date"] == "2025-01-10"
    assert item["open"] == 100
    assert item["high"] == 108
    assert item["low"] == 99
    assert item["close"] == 107
    assert item["trading_days"] == 2
    assert item["volume"] == 30
    assert item["weekly_change_pct"] is None


def test_weekly_change_and_ytd_use_prior_observation_and_prior_year_end():
    rows = [
        {
            "index_id": "TEST",
            "index_symbol": "T",
            "index_name": "Test",
            "index_name_en": "Test",
            "market": "Test",
            "currency": "USD",
            "trade_date": "2024-12-27",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "adjusted_close": 100,
            "volume": None,
            "declared_upstream_source": "Test source",
        },
        {
            "index_id": "TEST",
            "index_symbol": "T",
            "index_name": "Test",
            "index_name_en": "Test",
            "market": "Test",
            "currency": "USD",
            "trade_date": "2025-01-06",
            "open": 110,
            "high": 112,
            "low": 109,
            "close": 110,
            "adjusted_close": 110,
            "volume": None,
            "declared_upstream_source": "Test source",
        },
        {
            "index_id": "TEST",
            "index_symbol": "T",
            "index_name": "Test",
            "index_name_en": "Test",
            "market": "Test",
            "currency": "USD",
            "trade_date": "2025-01-10",
            "open": 110,
            "high": 115,
            "low": 109,
            "close": 120,
            "adjusted_close": 120,
            "volume": None,
            "declared_upstream_source": "Test source",
        },
    ]
    out = mod.build_weekly(rows)
    assert len(out) == 2
    prior_year, current_year = out
    assert prior_year["week_year"] == 2024
    assert prior_year["ytd_pct"] is None
    assert current_year["week_year"] == 2025
    assert current_year["ytd_pct"] == 20.0
    assert round(current_year["weekly_change_pct"], 8) == 20.0


def test_week_key_is_iso_week():
    assert mod.week_key("2025-01-01") == (2025, 1)
