from __future__ import annotations

from dataclasses import dataclass

from pythontrader.domain import Quote


@dataclass(slots=True)
class BookState:
    symbol: str
    bid: float = 0.0
    ask: float = 0.0
    bid_size: float = 0.0
    ask_size: float = 0.0
    updates: int = 0

    def update(self, q: Quote) -> None:
        if q.bid <= 0 or q.ask <= 0 or q.bid > q.ask:
            raise ValueError("invalid quote")
        self.bid, self.ask = q.bid, q.ask
        self.bid_size, self.ask_size = q.bid_size, q.ask_size
        self.updates += 1

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2 if self.ask else 0.0

    @property
    def imbalance(self) -> float:
        t = self.bid_size + self.ask_size
        return (self.bid_size - self.ask_size) / t if t else 0.0
