from pythontrader.domain import Order, RiskDecision
from pythontrader.portfolio.book import Portfolio

from .limits import RiskLimits


class RiskEngine:
    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.locked = False
        self.day_start_equity = None

    def check(
        self, order: Order, price: float, portfolio: Portfolio, marks: dict[str, float]
    ) -> RiskDecision:
        if self.locked:
            return RiskDecision(False, "risk_locked", 0)
        eq = portfolio.equity(marks)
        if self.day_start_equity is None:
            self.day_start_equity = eq
        if eq - self.day_start_equity < -self.limits.max_daily_loss:
            self.locked = True
            return RiskDecision(False, "daily_loss", 0)
        notional = order.qty * price
        if notional > self.limits.max_order:
            q = self.limits.max_order / price
            return RiskDecision(q > 0, "clipped_order_notional", q)
        pos = portfolio.positions.get(order.symbol)
        curr = abs((pos.qty if pos else 0) * price)
        if curr + notional > self.limits.max_symbol:
            q = max(0, (self.limits.max_symbol - curr) / price)
            return RiskDecision(q > 0, "clipped_symbol_exposure", q)
        if portfolio.gross(marks) + notional > self.limits.max_gross:
            return RiskDecision(False, "gross_exposure", 0)
        return RiskDecision(True, "accepted", order.qty)
