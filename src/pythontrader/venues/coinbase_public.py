from __future__ import annotations

from pythontrader.domain import Quote

from .base import VenueAdapter, VenueCapabilities
from .httpjson import JsonHttp


class CoinbasePublic(VenueAdapter):
    capabilities = VenueCapabilities("COINBASE-PUBLIC", ("crypto", "memecoin"), True, False)

    def __init__(self, http=None):
        self.http = http or JsonHttp()

    def health(self):
        try:
            self.http.get("https://api.exchange.coinbase.com/time")
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": type(e).__name__}

    def quote(self, symbol):
        product = symbol.replace("-USD", "-USD")
        d = self.http.get(f"https://api.exchange.coinbase.com/products/{product}/book?level=1")
        bid, ask = d["bids"][0], d["asks"][0]
        return Quote(
            symbol,
            float(bid[0]),
            float(ask[0]),
            float(bid[1]),
            float(ask[1]),
            venue=self.capabilities.name,
        )
