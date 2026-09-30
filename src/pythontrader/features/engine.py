from dataclasses import dataclass

from pythontrader.marketdata.cache import MarketCache

from .entropy import directional_entropy
from .volatility import realized_vol


@dataclass(frozen=True, slots=True)
class FeatureVector:
    symbol: str
    mid: float
    spread_bps: float
    imbalance: float
    vol: float
    entropy: float


class FeatureEngine:
    def __init__(self, cache: MarketCache):
        self.cache = cache

    def snapshot(self, symbol: str) -> FeatureVector | None:
        b = self.cache.quote(symbol)
        if not b or not b.mid:
            return None
        rs = self.cache.returns[symbol].last()
        return FeatureVector(
            symbol,
            b.mid,
            (b.ask - b.bid) / b.mid * 10000,
            b.imbalance,
            realized_vol(rs),
            directional_entropy(rs),
        )
