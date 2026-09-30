from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time

from pythontrader.domain import Fill, Order, OrderType, Side
from pythontrader.marketdata.orderbook import OrderBook


class OrderStatus(str, Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass(slots=True)
class OrderState:
    order: Order
    status: OrderStatus = OrderStatus.NEW
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    fees: float = 0.0
    reject_reason: str = ""
    updated_at: float = field(default_factory=time)
    venue_order_id: str | None = None

    @property
    def remaining_qty(self) -> float:
        return max(0.0, self.order.qty - self.filled_qty)

    def apply_fill(self, fill: Fill) -> None:
        if fill.order_id != self.order.id:
            raise ValueError("fill/order mismatch")
        if fill.qty <= 0 or fill.qty > self.remaining_qty + 1e-9:
            raise ValueError("invalid fill quantity")
        old_notional = self.avg_fill_price * self.filled_qty
        self.filled_qty += fill.qty
        self.avg_fill_price = (old_notional + fill.price * fill.qty) / self.filled_qty
        self.fees += fill.fee
        self.status = (
            OrderStatus.FILLED if self.remaining_qty <= 1e-9 else OrderStatus.PARTIALLY_FILLED
        )
        self.updated_at = fill.ts


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    taker_fee_bps: float = 5.0
    maker_fee_bps: float = 1.0
    max_book_fraction: float = 0.15
    min_fill_qty: float = 1e-8


class OrderManagementSystem:
    """Stateful OMS with idempotent fills and deterministic L2 execution.

    This is used by the simulator and replay harness. Live venue adapters can
    drive the same state machine by calling accept/reject/apply_fill.
    """

    def __init__(self, config: ExecutionConfig | None = None) -> None:
        self.config = config or ExecutionConfig()
        self.orders: dict[str, OrderState] = {}
        self._fill_ids: set[str] = set()
        self.events: list[tuple[float, str, str]] = []

    def submit(self, order: Order) -> OrderState:
        if order.id in self.orders:
            raise ValueError(f"duplicate order id {order.id}")
        if order.qty <= 0:
            raise ValueError("order quantity must be positive")
        state = OrderState(order=order)
        self.orders[order.id] = state
        self.events.append((time(), order.id, "submitted"))
        return state

    def accept(self, order_id: str, venue_order_id: str | None = None) -> OrderState:
        state = self._state(order_id)
        if state.status not in {OrderStatus.NEW, OrderStatus.ACCEPTED}:
            raise ValueError(f"cannot accept order in {state.status}")
        state.status = OrderStatus.ACCEPTED
        state.venue_order_id = venue_order_id
        state.updated_at = time()
        self.events.append((state.updated_at, order_id, "accepted"))
        return state

    def reject(self, order_id: str, reason: str) -> OrderState:
        state = self._state(order_id)
        if state.filled_qty:
            raise ValueError("cannot reject an order after fill")
        state.status = OrderStatus.REJECTED
        state.reject_reason = reason
        state.updated_at = time()
        self.events.append((state.updated_at, order_id, f"rejected:{reason}"))
        return state

    def cancel(self, order_id: str) -> OrderState:
        state = self._state(order_id)
        if state.status in {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELED}:
            return state
        state.status = OrderStatus.CANCELED
        state.updated_at = time()
        self.events.append((state.updated_at, order_id, "canceled"))
        return state

    def apply_fill(self, fill_id: str, fill: Fill) -> OrderState:
        if fill_id in self._fill_ids:
            return self._state(fill.order_id)
        state = self._state(fill.order_id)
        if state.status in {OrderStatus.REJECTED, OrderStatus.CANCELED, OrderStatus.FILLED}:
            raise ValueError(f"cannot fill order in {state.status}")
        state.apply_fill(fill)
        self._fill_ids.add(fill_id)
        self.events.append((fill.ts, fill.order_id, f"fill:{fill.qty}@{fill.price}"))
        return state

    def execute_against_book(
        self, order_id: str, book: OrderBook, *, ts: float | None = None
    ) -> list[Fill]:
        state = self._state(order_id)
        if state.status == OrderStatus.NEW:
            self.accept(order_id)
        if state.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            return []
        order = state.order
        candidates = book.asks if order.side is Side.BUY else book.bids
        if not candidates:
            return []

        remaining = state.remaining_qty
        fills: list[Fill] = []
        for index, level in enumerate(candidates):
            if remaining <= self.config.min_fill_qty:
                break
            if (
                order.order_type in {OrderType.LIMIT, OrderType.POST_ONLY}
                and order.limit_price is not None
            ):
                crosses = (
                    level.price <= order.limit_price
                    if order.side is Side.BUY
                    else level.price >= order.limit_price
                )
                if not crosses:
                    break
            available = level.size * self.config.max_book_fraction
            qty = min(remaining, available)
            if qty <= self.config.min_fill_qty:
                continue
            fee = level.price * qty * self.config.taker_fee_bps / 10_000.0
            fill = Fill(
                order.id,
                order.symbol,
                order.side,
                qty,
                level.price,
                fee,
                order.venue or "replay",
                ts or time(),
            )
            self.apply_fill(f"{order.id}:{index}:{self._state(order.id).filled_qty:.12g}", fill)
            fills.append(fill)
            remaining -= qty
            if order.order_type is OrderType.IOC:
                break
        if order.order_type is OrderType.IOC and self._state(order_id).remaining_qty > 0:
            self.cancel(order_id)
        return fills

    def open_orders(self) -> list[OrderState]:
        active = {OrderStatus.NEW, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}
        return [x for x in self.orders.values() if x.status in active]

    def _state(self, order_id: str) -> OrderState:
        try:
            return self.orders[order_id]
        except KeyError as exc:
            raise KeyError(f"unknown order {order_id}") from exc

    def snapshot(self) -> dict[str, object]:
        return {
            "orders": len(self.orders),
            "open": len(self.open_orders()),
            "fills": len(self._fill_ids),
            "states": {
                oid: {
                    "status": state.status.value,
                    "filled_qty": state.filled_qty,
                    "remaining_qty": state.remaining_qty,
                    "avg_fill_price": state.avg_fill_price,
                    "fees": state.fees,
                    "reject_reason": state.reject_reason,
                }
                for oid, state in self.orders.items()
            },
        }
