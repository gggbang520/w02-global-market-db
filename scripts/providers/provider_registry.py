from __future__ import annotations
from .manual_file import ManualFileProvider
from .index.yahoo_index import YahooIndexProvider

REGISTRY={'SRC-MANUAL-FILE': ManualFileProvider}
REGISTRY['SRC-YAHOO-INDEX'] = YahooIndexProvider

def register(source_id, provider_cls): REGISTRY[source_id]=provider_cls

def get_provider(source_id, *args, **kwargs): return REGISTRY[source_id](*args, **kwargs)
