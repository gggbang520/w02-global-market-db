"""
Index Provider Layer package.

Phase 1 introduces the index-specific provider framework without changing
existing production fetch flows.
"""

from .base import IndexProvider
from .yahoo_index import YahooIndexProvider

__all__ = ["IndexProvider", "YahooIndexProvider"]
