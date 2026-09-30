from __future__ import annotations

from pythontrader.domain import AssetClass, Instrument

_DEFAULTS = [
    Instrument("AAPL", AssetClass.EQUITY, "NASDAQ", tick_size=0.01),
    Instrument("NVDA", AssetClass.EQUITY, "NASDAQ", tick_size=0.01),
    Instrument("SPY", AssetClass.ETF, "ARCA", tick_size=0.01),
    Instrument("EURUSD", AssetClass.FX, "FX", tick_size=0.00001, lot_size=1000),
    Instrument("USDJPY", AssetClass.FX, "FX", currency="JPY", tick_size=0.001, lot_size=1000),
    Instrument("BTC-USD", AssetClass.CRYPTO, "COINBASE", tick_size=0.01, lot_size=0.00001),
    Instrument("ETH-USD", AssetClass.CRYPTO, "COINBASE", tick_size=0.01, lot_size=0.0001),
    Instrument(
        "BTC-PERP",
        AssetClass.PERP,
        "DERIVATIVES",
        tick_size=0.1,
        lot_size=0.001,
        underlying="BTC-USD",
    ),
    Instrument(
        "ETH-PERP",
        AssetClass.PERP,
        "DERIVATIVES",
        tick_size=0.01,
        lot_size=0.01,
        underlying="ETH-USD",
    ),
    Instrument("DOGE-USD", AssetClass.MEMECOIN, "CRYPTO", tick_size=0.000001, lot_size=1),
    Instrument("SHIB-USD", AssetClass.MEMECOIN, "CRYPTO", tick_size=0.00000001, lot_size=1000),
    Instrument("ES", AssetClass.FUTURE, "CME", tick_size=0.25, multiplier=50, underlying="SPX"),
    Instrument("NQ", AssetClass.FUTURE, "CME", tick_size=0.25, multiplier=20, underlying="NDX"),
    Instrument("XAUUSD", AssetClass.COMMODITY, "METALS", tick_size=0.01),
    Instrument("WTI", AssetClass.COMMODITY, "ENERGY", tick_size=0.01),
    Instrument("SPX", AssetClass.INDEX, "INDEX", tick_size=0.01),
]


class InstrumentRegistry:
    def __init__(self, instruments=None):
        self._items = {x.symbol: x for x in (instruments or _DEFAULTS)}

    def get(self, symbol):
        return self._items[symbol]

    def all(self):
        return tuple(self._items.values())

    def by_asset_class(self, asset_class):
        return tuple(x for x in self._items.values() if x.asset_class == asset_class)

    def add(self, instrument):
        self._items[instrument.symbol] = instrument

    def describe(self):
        return {
            s: {
                "asset_class": i.asset_class.value,
                "venue": i.venue,
                "tick_size": i.tick_size,
                "lot_size": i.lot_size,
                "underlying": i.underlying,
            }
            for s, i in self._items.items()
        }
