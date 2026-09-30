from __future__ import annotations

from urllib.parse import quote as uq

from pythontrader.domain import Quote

from .base import VenueAdapter, VenueCapabilities
from .httpjson import JsonHttp


class BinancePublic(VenueAdapter):
    capabilities = VenueCapabilities("BINANCE-PUBLIC", ("crypto", "memecoin"), True, False)

    def __init__(self, http=None):
        self.http = http or JsonHttp()

    def health(self):
        try:
            self.http.get("https://api.binance.com/api/v3/ping")
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": type(e).__name__}

    def quote(self, symbol):
        s = symbol.replace("-USD", "USDT").replace("-", "")
        d = self.http.get("https://api.binance.com/api/v3/ticker/bookTicker?symbol=" + uq(s))
        return Quote(
            symbol,
            float(d["bidPrice"]),
            float(d["askPrice"]),
            float(d["bidQty"]),
            float(d["askQty"]),
            venue=self.capabilities.name,
        )
