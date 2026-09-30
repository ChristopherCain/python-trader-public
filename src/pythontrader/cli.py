import argparse
import json

from pythontrader.engine import TradingEngine
from pythontrader.marketdata.synthetic import SyntheticFeed
from pythontrader.settings import Settings


def main():
    p = argparse.ArgumentParser(prog="pythontrader")
    p.add_argument("command", choices=["run", "state"])
    p.add_argument("--steps", type=int, default=2000)
    a = p.parse_args()
    e = TradingEngine(Settings())
    f = SyntheticFeed(["AAPL", "MSFT", "NVDA", "EURUSD", "BTCUSD"])
    if a.command == "run":
        for _ in range(a.steps):
            for q in f.step():
                e.on_quote(q)
    print(json.dumps(e.snapshot(), indent=2, default=str))


if __name__ == "__main__":
    main()
