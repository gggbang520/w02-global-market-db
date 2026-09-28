"""Point-in-time membership lookup engine for W02 V1.1."""
from __future__ import annotations
from datetime import date
from typing import Any, Iterable


def _d(value: str | None):
    return date.fromisoformat(value) if value else None


def membership_at(records: Iterable[dict[str, Any]], trade_date: str) -> dict[str, dict[str, Any]]:
    d = _d(trade_date)
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        start, end = _d(r.get("effective_from")), _d(r.get("effective_to"))
        if start and start <= d and (end is None or d < end):
            key = r.get("listing_id") or r.get("ticker")
            if key:
                out[key] = r
    return out


def status_for_price(
    listing_id: str,
    trade_date: str,
    active: dict[str, dict[str, Any]],
    *,
    snapshot_complete: bool = False,
) -> tuple[str, dict[str, Any] | None]:
    r = active.get(listing_id)
    if r:
        return "IN_INDEX", r
    if snapshot_complete:
        return "OUT_OF_INDEX", None
    return "UNKNOWN", None


def snapshot_at(snapshots: Iterable[dict[str, Any]], trade_date: str) -> dict[str, dict[str, Any]]:
    """Return the latest available historical snapshot on or before trade_date."""
    d = _d(trade_date)
    candidates = [s for s in snapshots if _d(s.get('observation_date')) and _d(s.get('observation_date')) <= d]
    if not candidates:
        return {}
    s = max(candidates, key=lambda x: x['observation_date'])
    return {m.get('listing_id') or m.get('ticker'): m for m in s.get('members', []) if m.get('listing_id') or m.get('ticker')}
