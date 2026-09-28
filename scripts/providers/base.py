from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

class MarketDataProvider(ABC):
    source_id: str = ''
    source_origin: str = 'MANUAL'
    dataset: str = 'stock_daily'

    @abstractmethod
    def discover(self): ...
    @abstractmethod
    def fetch(self): ...
    @abstractmethod
    def parse(self, input_path: Path): ...
    @abstractmethod
    def normalize(self, records): ...
    @abstractmethod
    def capabilities(self) -> dict[str, Any]: ...
