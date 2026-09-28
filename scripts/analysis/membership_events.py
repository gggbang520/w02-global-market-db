"""CSI300 historical membership event model for W02 V1.1.

The V1.0 secondary archive is a point-in-time/history evidence source, not a
complete official event ledger. V1.1 therefore stores only events explicitly
supported by evidence and leaves unresolved effective dates as null.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from typing import Any, Iterable

EVENT_TYPES = {"ADD", "REMOVE", "WEIGHT_CHANGE", "RANK_CHANGE", "REBALANCE", "UNKNOWN"}

@dataclass
class MembershipEvent:
    event_id: str
    index_id: str
    security_id: str | None
    listing_id: str | None
    event_date: str | None
    effective_from: str | None
    effective_to: str | None
    event_type: str
    old_weight: float | None = None
    new_weight: float | None = None
    old_rank: int | None = None
    new_rank: int | None = None
    source_id: str = "SRC-INDEX-CONSTITUTION-SECONDARY"
    source_origin: str = "SECONDARY"
    data_quality_status: str = "SOURCE_CONFIRMED"
    license_gate: str = "REVIEW"
    evidence_type: str = "SECONDARY_EVENT"
    effective_date_status: str = "NOT_ESTABLISHED"
    notes: str = ""

    def __post_init__(self):
        if self.event_type not in EVENT_TYPES:
            raise ValueError(self.event_type)


def event_dict(**kwargs: Any) -> dict[str, Any]:
    return asdict(MembershipEvent(**kwargs))


def active_from_events(events: Iterable[dict[str, Any]], observation_date: str) -> dict[str, dict[str, Any]]:
    """Apply only events with a *resolved* effective_from date.

    Events without a resolved effective date are deliberately ignored rather
    than guessed. A caller should use a separately verified snapshot as an
    anchor when the event ledger is incomplete.
    """
    d = date.fromisoformat(observation_date)
    state: dict[str, dict[str, Any]] = {}
    for e in sorted(events, key=lambda x: (x.get("effective_from") or "9999-12-31", x["event_id"])):
        ef = e.get("effective_from")
        if not ef or date.fromisoformat(ef) > d:
            continue
        key = e.get("listing_id")
        if not key:
            continue
        if e["event_type"] == "ADD":
            state[key] = e
        elif e["event_type"] == "REMOVE":
            state.pop(key, None)
    return state
