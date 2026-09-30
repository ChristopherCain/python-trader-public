from time import perf_counter

from pythontrader.engine import TradingEngine
from pythontrader.marketdata.synthetic import SyntheticFeed
from pythontrader.settings import Settings

N = 20000
e = TradingEngine(Settings())
f = SyntheticFeed(["AAPL", "MSFT", "NVDA"])
t = perf_counter()
for _ in range(N):
    for q in f.step():
        e.on_quote(q)
dt = perf_counter() - t
print({"quotes": N * 3, "seconds": round(dt, 3), "quotes_per_second": round(N * 3 / dt)})
