from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from .base import IndexProvider


class YahooIndexProvider(IndexProvider):
    """Yahoo index provider wrapper."""

    source_id = "SRC-YAHOO-INDEX"
    source_origin = "AUTO_PROVIDER"

    def discover(self):
        return []

    def fetch_history(self, symbol: str, start: date, end: date):
        """Fetch Yahoo historical index data.

        Keeps the existing production behavior:
        1. Try yfinance.download.
        2. Fallback to Ticker.history when data is empty or insufficient.

        Returns a DataFrame compatible with the existing serialization contract.
        """
        df = yf.download(
            symbol,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
            group_by="column",
        )

        if df.empty or len(df.index) <= 1:
            try:
                fallback = yf.Ticker(symbol).history(
                    start=start.isoformat(),
                    end=(end + timedelta(days=1)).isoformat(),
                    auto_adjust=False,
                    actions=False,
                )
                if not fallback.empty and len(fallback.index) > len(df.index):
                    df = fallback
            except Exception:
                pass

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            if symbol in set(map(str, df.columns.get_level_values(-1))):
                try:
                    df = df.xs(symbol, axis=1, level=-1, drop_level=True)
                except Exception:
                    pass
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]) for c in df.columns]

        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else df.columns[0]

        rename = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adjusted_close",
        }
        for old, new in rename.items():
            if old in df.columns:
                df[new] = pd.to_numeric(df[old], errors="coerce")

        df["trade_date"] = pd.to_datetime(df[date_col]).dt.date.astype(str)

        if "Volume" in df.columns:
            df["volume"] = pd.to_numeric(df["Volume"], errors="coerce")
        else:
            df["volume"] = None

        for col in [
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
        ]:
            if col not in df.columns:
                df[col] = None

        return (
            df[
                [
                    "trade_date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "adjusted_close",
                    "volume",
                ]
            ]
            .dropna(subset=["close"])
            .drop_duplicates(["trade_date"])
            .sort_values("trade_date")
        )

    def fetch(self, symbol=None, start=None, end=None):
        if symbol is None or start is None or end is None:
            raise ValueError("symbol, start and end are required")
        return self.fetch_history(symbol, start, end)

    def parse(self, input_path: Path):
        raise NotImplementedError

    def normalize(self, records):
        return records

    def capabilities(self):
        return {
            "provider": "yahoo_index",
            "source_id": self.source_id,
            "source_origin": self.source_origin,
            "status": "implemented",
        }
