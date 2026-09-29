from __future__ import annotations

from typing import Type

from .base import IndexProvider


class IndexProviderResolver:
    """Resolver interface for future index provider routing.

    Phase 1 only defines the interface and does not control production flow.
    """

    def __init__(self):
        self.providers: dict[str, Type[IndexProvider]] = {}

    def register(self, source_id: str, provider_cls: Type[IndexProvider]):
        self.providers[source_id] = provider_cls

    def resolve(self, source_id: str):
        return self.providers.get(source_id)
