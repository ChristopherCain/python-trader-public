from dataclasses import dataclass

from pythontrader.engine import TradingEngine


@dataclass(frozen=True, slots=True)
class BacktestResult:
    start_equity: float
    end_equity: float
    fills: int
    return_pct: float


class BacktestRunner:
    def __init__(self, engine: TradingEngine):
        self.engine = engine

    def run(self, frames):
        start = self.engine.portfolio.cash
        fills = 0
        for frame in frames:
            for q in frame:
                fills += self.engine.on_quote(q) is not None
        end = self.engine.snapshot()["equity"]
        return BacktestResult(start, end, fills, (end / start - 1) * 100 if start else 0)
