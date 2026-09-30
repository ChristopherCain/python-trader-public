from pythontrader.core.ring import NumericRing
from pythontrader.domain import Quote, Trade

from .book import BookState


class MarketCache:
    def __init__(self, window: int = 512):
        self.books = {}
        self.returns = {}
        self.trades = {}
        self.window = window

    def on_quote(self, q: Quote) -> None:
        b = self.books.setdefault(q.symbol, BookState(q.symbol))
        prev = b.mid
        b.update(q)
        r = self.returns.setdefault(q.symbol, NumericRing(self.window))
        if prev > 0:
            r.push(q.mid / prev - 1)

    def on_trade(self, t: Trade) -> None:
        self.trades.setdefault(t.symbol, NumericRing(self.window)).push(t.price)

    def quote(self, symbol: str) -> BookState | None:
        return self.books.get(symbol)
