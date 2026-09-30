from __future__ import annotations

from dataclasses import dataclass

from pythontrader.domain import Fill, Order
from pythontrader.execution.oms import OrderManagementSystem
from pythontrader.execution.smart_order_router import RoutingPlan, SmartOrderRouter
from pythontrader.execution.venue_scoring import VenueSnapshot
from pythontrader.marketdata.orderbook import OrderBook


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    parent_order_id: str
    plan: RoutingPlan
    fills: tuple[Fill, ...]
    filled_qty: float
    avg_price: float
    fees: float


class ExecutionCoordinator:
    """Connects routing plans to the deterministic OMS/replay execution path."""

    def __init__(
        self, router: SmartOrderRouter | None = None, oms: OrderManagementSystem | None = None
    ) -> None:
        self.router = router or SmartOrderRouter()
        self.oms = oms or OrderManagementSystem()

    def execute_simulated(
        self,
        parent: Order,
        snapshots: list[VenueSnapshot],
        *,
        urgency: float,
        adv_notional: float,
        volatility_daily: float,
    ) -> ExecutionReport:
        plan = self.router.route(
            parent,
            snapshots,
            urgency=urgency,
            adv_notional=adv_notional,
            volatility_daily=volatility_daily,
        )
        fills: list[Fill] = []
        child_index = 0
        for child in plan.children:
            snapshot = next(item for item in snapshots if item.venue == child.venue)
            child_order = Order(
                id=f"{parent.id}:{child_index}",
                symbol=parent.symbol,
                side=parent.side,
                qty=child.qty,
                order_type=child.order_type,
                limit_price=child.limit_price,
                strategy=parent.strategy,
                venue=child.venue,
                reduce_only=parent.reduce_only,
                leverage=parent.leverage,
            )
            child_index += 1
            self.oms.submit(child_order)
            book = OrderBook(parent.symbol)
            book.reset(
                bids=[(snapshot.bid, snapshot.bid_size)],
                asks=[(snapshot.ask, snapshot.ask_size)],
                sequence=1,
                ts=0.0,
            )
            fills.extend(self.oms.execute_against_book(child_order.id, book))

        filled_qty = sum(fill.qty for fill in fills)
        notional = sum(fill.qty * fill.price for fill in fills)
        avg = notional / filled_qty if filled_qty else 0.0
        fees = sum(fill.fee for fill in fills)
        return ExecutionReport(parent.id, plan, tuple(fills), filled_qty, avg, fees)
