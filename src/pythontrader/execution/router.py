from dataclasses import dataclass

from pythontrader.domain import Fill, Order, Quote

from .simulator import ExecutionSimulator


@dataclass(frozen=True, slots=True)
class RouteDecision:
    venue: str
    score: float


class SmartOrderRouter:
    def __init__(self, executor: ExecutionSimulator):
        self.executor = executor

    def route(self, order: Order, quotes: list[Quote]) -> Fill | None:
        if not quotes:
            return None
        q = min(quotes, key=lambda x: x.spread)
        return self.executor.execute(order, q)
