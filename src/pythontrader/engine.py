from __future__ import annotations

from uuid import uuid4

from pythontrader.agents.ensemble import StrategyEnsemble
from pythontrader.domain import Order, OrderType, Side
from pythontrader.execution.simulator import ExecutionSimulator
from pythontrader.features.engine import FeatureEngine
from pythontrader.marketdata.cache import MarketCache
from pythontrader.orders.store import OrderStore
from pythontrader.portfolio.book import Portfolio
from pythontrader.risk.engine import RiskEngine
from pythontrader.risk.limits import RiskLimits
from pythontrader.settings import Settings
from pythontrader.strategies.entropy_regime import EntropyRegimeStrategy
from pythontrader.strategies.liquidity import LiquidityStrategy
from pythontrader.strategies.mean_reversion import MeanReversionStrategy
from pythontrader.strategies.momentum import MomentumStrategy
from pythontrader.strategies.vol_breakout import VolatilityBreakoutStrategy
from pythontrader.telemetry.metrics import Metrics


class TradingEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = MarketCache()
        self.features = FeatureEngine(self.cache)
        self.ensemble = StrategyEnsemble(
            [
                MomentumStrategy(),
                MeanReversionStrategy(),
                LiquidityStrategy(),
                VolatilityBreakoutStrategy(),
                EntropyRegimeStrategy(),
            ]
        )
        self.portfolio = Portfolio(settings.starting_cash)
        self.risk = RiskEngine(
            RiskLimits(
                settings.max_gross_exposure,
                settings.max_symbol_exposure,
                settings.max_order_notional,
                settings.max_daily_loss,
            )
        )
        self.execution = ExecutionSimulator()
        self.orders = OrderStore()
        self.metrics = Metrics(settings.telemetry_window)
        self.last_quotes = {}

    def on_quote(self, q):
        self.cache.on_quote(q)
        self.last_quotes[q.symbol] = q
        f = self.features.snapshot(q.symbol)
        if not f:
            return None
        c = self.ensemble.decide(f)
        self.metrics.observe("consensus", c.score)
        if abs(c.score) < 0.025:
            return None
        qty = max(1, min(250, abs(c.score) * 100))
        side = Side.BUY if c.score > 0 else Side.SELL
        order = Order(uuid4().hex, q.symbol, side, qty, OrderType.MARKET, strategy="ensemble")
        self.orders.add(order)
        marks = {s: x.mid for s, x in self.last_quotes.items()}
        d = self.risk.check(order, q.mid, self.portfolio, marks)
        if not d.accepted:
            self.orders.reject(order.id, d.reason)
            self.metrics.inc("orders_rejected")
            return None
        order.qty = d.adjusted_qty
        fill = self.execution.execute(order, q)
        if fill:
            self.portfolio.apply(fill)
            self.orders.filled(fill)
            self.metrics.inc("fills")
            self.metrics.set("equity", self.portfolio.equity(marks))
        return fill

    def snapshot(self):
        marks = {s: q.mid for s, q in self.last_quotes.items()}
        return {
            "mode": self.settings.mode,
            "cash": self.portfolio.cash,
            "equity": self.portfolio.equity(marks),
            "gross": self.portfolio.gross(marks),
            "positions": {
                s: {"qty": p.qty, "avg_price": p.avg_price, "realized_pnl": p.realized_pnl}
                for s, p in self.portfolio.positions.items()
            },
            "metrics": self.metrics.snapshot(),
        }
