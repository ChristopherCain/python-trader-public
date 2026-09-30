from __future__ import annotations

from random import Random

from pythontrader.domain import Quote

from .base import VenueAdapter, VenueCapabilities


class SyntheticUniversalVenue(VenueAdapter):
    capabilities = VenueCapabilities(
        "SIM-X",
        ("equity", "etf", "fx", "crypto", "memecoin", "perp", "future", "index", "commodity"),
        True,
        False,
        True,
        True,
        20.0,
    )

    def __init__(self, seed=42):
        self.rng = Random(seed)
        self.last = {}

    def health(self):
        return {"ok": True, "mode": "deterministic-universal"}

    def quote(self, symbol):
        anchors = {
            "AAPL": 220,
            "NVDA": 180,
            "SPY": 650,
            "EURUSD": 1.17,
            "USDJPY": 148,
            "BTC-USD": 95000,
            "ETH-USD": 3600,
            "BTC-PERP": 95020,
            "ETH-PERP": 3601,
            "DOGE-USD": 0.22,
            "SHIB-USD": 0.000013,
            "ES": 6700,
            "NQ": 25000,
            "XAUUSD": 3900,
            "WTI": 68,
            "SPX": 6700,
        }
        p = self.last.get(symbol, anchors.get(symbol, 100.0))
        vol = 0.0008 if p > 10 else 0.0025
        p = max(1e-9, p * (1 + self.rng.gauss(0, vol)))
        self.last[symbol] = p
        spread = max(p * 0.00015, 1e-8)
        return Quote(symbol, p - spread / 2, p + spread / 2, 1000, 1000, venue="SIM-X")
