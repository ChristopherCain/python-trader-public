from pythontrader.domain import Fill, Order, OrderType, Quote, Side

from .slippage import impact_bps


class ExecutionSimulator:
    def __init__(self, fee_bps: float = 0.3):
        self.fee_bps = fee_bps

    def execute(self, order: Order, q: Quote) -> Fill | None:
        touch = q.ask if order.side is Side.BUY else q.bid
        if order.order_type is OrderType.LIMIT and order.limit_price is not None:
            if order.side is Side.BUY and order.limit_price < q.ask:
                return None
            if order.side is Side.SELL and order.limit_price > q.bid:
                return None
        avail = q.ask_size if order.side is Side.BUY else q.bid_size
        slip = impact_bps(order.qty, avail) / 10000
        px = touch * (1 + slip if order.side is Side.BUY else 1 - slip)
        fee = abs(px * order.qty) * self.fee_bps / 10000
        return Fill(order.id, order.symbol, order.side, order.qty, px, fee, "SIM")
