from pythontrader.engine import TradingEngine
from pythontrader.marketdata.synthetic import SyntheticFeed
from pythontrader.settings import Settings


def test_engine_runs():
    e = TradingEngine(Settings())
    f = SyntheticFeed(["AAPL", "MSFT"])
    for _ in range(300):
        for q in f.step():
            e.on_quote(q)
    s = e.snapshot()
    assert s["equity"] > 0
    assert "positions" in s
