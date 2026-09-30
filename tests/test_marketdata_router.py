from pythontrader.domain import Quote
from pythontrader.venues.marketdata_router import MarketDataRouter


def test_marketdata_router_normalizes_source() -> None:
    router = MarketDataRouter()
    router.register("x", lambda symbol: Quote(symbol, 99.0, 101.0, 1.0, 1.0, venue="x"))
    quote = router.get("x", "ABC")
    assert quote.mid == 100.0
    assert quote.venue == "x"
