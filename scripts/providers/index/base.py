from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import MarketDataProvider


class IndexProvider(MarketDataProvider):
    """Base class for index market data providers.

    This layer extends the existing MarketDataProvider contract and does not
    replace the current provider workflow.
    """

    dataset: str = "index_daily"

    def index_metadata(self) -> dict[str, Any]:
        return {}

    def capabilities(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "source_id": self.source_id,
            "source_origin": self.source_origin,
        }

    def parse(self, input_path: Path):
        raise NotImplementedError

    def normalize(self, records):
        return records
