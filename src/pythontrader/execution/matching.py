from __future__ import annotations

from dataclasses import dataclass

from pythontrader.domain import Side


@dataclass(slots=True)
class RestingOrder:
    id: str
    side: Side
    price: float
    qty: float
    remaining: float


@dataclass(frozen=True, slots=True)
class Match:
    maker_id: str
    taker_id: str
    price: float
    qty: float


class PriceTimeBook:
    def __init__(self):
        self.bids = []
        self.asks = []

    def add(self, o: RestingOrder):
        (self.bids if o.side is Side.BUY else self.asks).append(o)
        self.bids.sort(key=lambda x: -x.price)
        self.asks.sort(key=lambda x: x.price)

    def cross(self, taker: RestingOrder) -> list[Match]:
        side = self.asks if taker.side is Side.BUY else self.bids
        out = []
        i = 0
        while taker.remaining > 0 and i < len(side):
            maker = side[i]
            crosses = (
                taker.price >= maker.price if taker.side is Side.BUY else taker.price <= maker.price
            )
            if not crosses:
                break
            q = min(taker.remaining, maker.remaining)
            out.append(Match(maker.id, taker.id, maker.price, q))
            maker.remaining -= q
            taker.remaining -= q
            if maker.remaining <= 0:
                side.pop(i)
            else:
                i += 1
        if taker.remaining > 0:
            self.add(taker)
        return out
