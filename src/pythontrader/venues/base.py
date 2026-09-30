from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pythontrader.domain import Fill, Order, Quote


@dataclass(frozen=True, slots=True)
class VenueCapabilities:
    name: str
    asset_classes: tuple[str, ...]
    market_data: bool = True
    order_entry: bool = False
    shorting: bool = False
    leverage: bool = False
    max_leverage: float = 1.0


class VenueAdapter(ABC):
    capabilities: VenueCapabilities

    @abstractmethod
    def health(self) -> dict: ...
    @abstractmethod
    def quote(self, symbol: str) -> Quote | None: ...
    def execute(self, order: Order, quote: Quote) -> Fill | None:
        raise RuntimeError(f"{self.capabilities.name} has no order-entry implementation")
