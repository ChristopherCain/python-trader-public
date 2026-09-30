from __future__ import annotations

from dataclasses import dataclass
from time import time

from pythontrader.domain import Order
from pythontrader.execution.oms import OrderManagementSystem, OrderStatus


@dataclass(frozen=True, slots=True)
class ReplaceResult:
    old_order_id: str
    new_order: Order
    canceled_remaining: float
    ts: float


class CancelReplaceManager:
    """Implements deterministic cancel/replace while preserving filled quantity semantics."""

    def __init__(self, oms: OrderManagementSystem) -> None:
        self.oms = oms

    def replace(self, order_id: str, replacement: Order) -> ReplaceResult:
        state = self.oms._state(order_id)
        if state.status in {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED}:
            raise ValueError(f"cannot replace order in {state.status}")
        if replacement.id == order_id:
            raise ValueError("replacement order must use a new id")
        if replacement.symbol != state.order.symbol or replacement.side != state.order.side:
            raise ValueError("replacement must preserve symbol and side")
        if replacement.qty + 1e-9 < state.filled_qty:
            raise ValueError("replacement quantity below already-filled quantity")

        remaining = state.remaining_qty
        self.oms.cancel(order_id)
        self.oms.submit(replacement)
        self.oms.events.append((time(), replacement.id, f"replaces:{order_id}"))
        return ReplaceResult(order_id, replacement, remaining, time())
