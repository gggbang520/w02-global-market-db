from __future__ import annotations

from pathlib import Path

from .base import IndexProvider


class YahooIndexProvider(IndexProvider):
    """Yahoo index provider wrapper.

    Phase 1 only provides the provider abstraction. Existing
    SRC-YAHOO-INDEX production fetching remains unchanged.
    """

    source_id = "SRC-YAHOO-INDEX"
    source_origin = "AUTO_PROVIDER"

    def discover(self):
        return []

    def fetch(self):
        raise NotImplementedError(
            "Yahoo index integration remains on the existing fetch workflow in Phase 1"
        )

    def parse(self, input_path: Path):
        raise NotImplementedError

    def normalize(self, records):
        return records

    def capabilities(self):
        return {
            "provider": "yahoo_index",
            "source_id": self.source_id,
            "source_origin": self.source_origin,
            "status": "framework_only",
        }
