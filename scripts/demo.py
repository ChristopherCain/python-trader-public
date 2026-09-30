from pythontrader.engine import TradingEngine
from pythontrader.marketdata.synthetic import SyntheticFeed
from pythontrader.settings import Settings

if __name__ == "__main__":
    e = TradingEngine(Settings())
    f = SyntheticFeed(["AAPL", "MSFT", "NVDA", "EURUSD", "BTCUSD"])
    for _ in range(10000):
        for q in f.step():
            e.on_quote(q)
    from pprint import pprint

    pprint(e.snapshot())
