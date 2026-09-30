from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic

from pythontrader.domain import Quote


@dataclass(slots=True)
class CachedQuote:
    quote: Quote
    received_at: float = field(default_factory=monotonic)


class MarketDataRouter:
    """Venue-independent quote router with freshness and fallback semantics."""

    def __init__(self, *, max_age_s: float = 5.0) -> None:
        self.max_age_s = max_age_s
        self._sources: dict[str, Callable[[str], Quote]] = {}
        self._cache: dict[tuple[str, str], CachedQuote] = {}

    def register(self, venue: str, source: Callable[[str], Quote]) -> None:
        if not venue:
            raise ValueError("venue name is required")
        self._sources[venue] = source

    def get(self, venue: str, symbol: str, *, allow_stale: bool = False) -> Quote:
        key = (venue, symbol)
        source = self._sources.get(venue)
        if source is None:
            raise KeyError(f"unknown market-data venue {venue}")
        try:
            quote = source(symbol)
            self._validate(quote)
            self._cache[key] = CachedQuote(quote)
            return quote
        except Exception:
            cached = self._cache.get(key)
            if cached is None:
                raise
            age = monotonic() - cached.received_at
            if not allow_stale and age > self.max_age_s:
                raise
            return cached.quote

    @staticmethod
    def _validate(quote: Quote) -> None:
        if quote.bid <= 0 or quote.ask <= 0:
            raise ValueError("quote prices must be positive")
        if quote.ask < quote.bid:
            raise ValueError("crossed quote")
