from pythontrader.domain import AssetClass
from pythontrader.universe.registry import InstrumentRegistry


def test_universe_spans_markets():
    r = InstrumentRegistry()
    classes = {x.asset_class for x in r.all()}
    assert {
        AssetClass.EQUITY,
        AssetClass.FX,
        AssetClass.CRYPTO,
        AssetClass.MEMECOIN,
        AssetClass.PERP,
        AssetClass.FUTURE,
    }.issubset(classes)
    assert r.get("BTC-PERP").underlying == "BTC-USD"
