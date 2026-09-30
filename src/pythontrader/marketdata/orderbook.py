from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class Level:
    price: float
    size: float

    def __post_init__(self) -> None:
        if not isfinite(self.price) or not isfinite(self.size):
            raise ValueError("non-finite book level")
        if self.price <= 0 or self.size < 0:
            raise ValueError("invalid book level")


class OrderBook:
    """Deterministic L2 order book used by replay, execution and market-making.

    Bids are stored descending, asks ascending. Updates are absolute sizes;
    a size of zero removes the level. The object deliberately avoids numpy so it
    remains cheap to instantiate in tests and replay workers.
    """

    def __init__(self, symbol: str, *, max_depth: int = 200) -> None:
        self.symbol = symbol
        self.max_depth = max_depth
        self._bids: list[Level] = []
        self._asks: list[Level] = []
        self.sequence = 0
        self.timestamp = 0.0

    @property
    def bids(self) -> tuple[Level, ...]:
        return tuple(self._bids)

    @property
    def asks(self) -> tuple[Level, ...]:
        return tuple(self._asks)

    @property
    def best_bid(self) -> Level | None:
        return self._bids[0] if self._bids else None

    @property
    def best_ask(self) -> Level | None:
        return self._asks[0] if self._asks else None

    @property
    def mid(self) -> float | None:
        if not self._bids or not self._asks:
            return None
        return (self._bids[0].price + self._asks[0].price) / 2.0

    @property
    def spread(self) -> float | None:
        if not self._bids or not self._asks:
            return None
        return self._asks[0].price - self._bids[0].price

    def crossed(self) -> bool:
        return bool(self._bids and self._asks and self._bids[0].price >= self._asks[0].price)

    def reset(
        self,
        bids: Iterable[tuple[float, float]],
        asks: Iterable[tuple[float, float]],
        *,
        sequence: int,
        ts: float,
    ) -> None:
        bid_levels = [Level(float(p), float(s)) for p, s in bids if float(s) > 0]
        ask_levels = [Level(float(p), float(s)) for p, s in asks if float(s) > 0]
        bid_levels.sort(key=lambda x: x.price, reverse=True)
        ask_levels.sort(key=lambda x: x.price)
        self._bids = bid_levels[: self.max_depth]
        self._asks = ask_levels[: self.max_depth]
        self.sequence = sequence
        self.timestamp = ts
        self._validate()

    def update(self, side: str, price: float, size: float, *, sequence: int, ts: float) -> None:
        if sequence <= self.sequence:
            return
        if self.sequence and sequence != self.sequence + 1:
            raise ValueError(f"sequence gap: expected {self.sequence + 1}, got {sequence}")
        levels = self._bids if side.lower() in {"bid", "buy", "b"} else self._asks
        reverse = levels is self._bids
        self._upsert(levels, Level(float(price), max(0.0, float(size))), reverse=reverse)
        self.sequence = sequence
        self.timestamp = ts
        self._validate()

    def _upsert(self, levels: list[Level], level: Level, *, reverse: bool) -> None:
        found = next((i for i, x in enumerate(levels) if x.price == level.price), None)
        if found is not None:
            if level.size == 0:
                levels.pop(found)
            else:
                levels[found] = level
        elif level.size > 0:
            levels.append(level)
        levels.sort(key=lambda x: x.price, reverse=reverse)
        del levels[self.max_depth :]

    def _validate(self) -> None:
        if any(a.price <= b.price for a, b in zip(self._bids, self._bids[1:])):
            raise ValueError("bid book is not strictly descending")
        if any(a.price >= b.price for a, b in zip(self._asks, self._asks[1:])):
            raise ValueError("ask book is not strictly ascending")
        if self.crossed():
            raise ValueError("crossed order book")

    def microprice(self) -> float | None:
        if not self._bids or not self._asks:
            return None
        b, a = self._bids[0], self._asks[0]
        denom = b.size + a.size
        if denom <= 0:
            return self.mid
        return (a.price * b.size + b.price * a.size) / denom

    def imbalance(self, depth: int = 5) -> float:
        b = sum(x.size for x in self._bids[:depth])
        a = sum(x.size for x in self._asks[:depth])
        denom = a + b
        return 0.0 if denom == 0 else (b - a) / denom

    def depth_notional(self, side: str, levels: int = 10) -> float:
        book = self._bids if side.lower() in {"bid", "buy", "b"} else self._asks
        return sum(x.price * x.size for x in book[:levels])

    def estimate_market_order(self, side: str, qty: float) -> tuple[float, float]:
        if qty <= 0:
            return 0.0, 0.0
        book = self._asks if side.lower() in {"buy", "bid", "b"} else self._bids
        remaining = qty
        notional = 0.0
        filled = 0.0
        for level in book:
            take = min(remaining, level.size)
            notional += take * level.price
            filled += take
            remaining -= take
            if remaining <= 1e-12:
                break
        if filled == 0:
            return 0.0, 0.0
        return filled, notional / filled

    def snapshot(self, depth: int = 20) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "bid": None if not self._bids else self._bids[0].price,
            "ask": None if not self._asks else self._asks[0].price,
            "mid": self.mid,
            "spread": self.spread,
            "microprice": self.microprice(),
            "imbalance": self.imbalance(min(depth, 10)),
            "bids": [(x.price, x.size) for x in self._bids[:depth]],
            "asks": [(x.price, x.size) for x in self._asks[:depth]],
        }
