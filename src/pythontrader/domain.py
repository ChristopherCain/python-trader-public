from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from time import time


class AssetClass(str, Enum):
    EQUITY = "equity"
    ETF = "etf"
    FX = "fx"
    CRYPTO = "crypto"
    MEMECOIN = "memecoin"
    PERP = "perp"
    FUTURE = "future"
    INDEX = "index"
    COMMODITY = "commodity"
    OPTION = "option"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    IOC = "ioc"
    POST_ONLY = "post_only"


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    asset_class: AssetClass
    venue: str
    currency: str = "USD"
    tick_size: float = 0.01
    lot_size: float = 1.0
    multiplier: float = 1.0
    underlying: str | None = None
    expiry: str | None = None
    metadata: Mapping[str, str | float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    ts: float = field(default_factory=time)
    venue: str = ""

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> float:
        return max(0.0, self.ask - self.bid)


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    price: float
    size: float
    aggressor: Side
    ts: float = field(default_factory=time)
    venue: str = ""


@dataclass(frozen=True, slots=True)
class Signal:
    symbol: str
    score: float
    confidence: float
    horizon_s: int
    source: str
    metadata: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class Order:
    id: str
    symbol: str
    side: Side
    qty: float
    order_type: OrderType
    limit_price: float | None = None
    strategy: str = ""
    venue: str = ""
    reduce_only: bool = False
    leverage: float = 1.0
    created_at: float = field(default_factory=time)


@dataclass(frozen=True, slots=True)
class Fill:
    order_id: str
    symbol: str
    side: Side
    qty: float
    price: float
    fee: float
    venue: str
    ts: float = field(default_factory=time)


@dataclass(slots=True)
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


@dataclass(frozen=True, slots=True)
class RiskDecision:
    accepted: bool
    reason: str
    adjusted_qty: float
