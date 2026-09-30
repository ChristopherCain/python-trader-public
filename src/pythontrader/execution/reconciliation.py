from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pythontrader.execution.oms import OrderManagementSystem, OrderStatus


class ReconciliationIssue(str, Enum):
    LOCAL_ONLY = "local-only"
    VENUE_ONLY = "venue-only"
    STATUS_MISMATCH = "status-mismatch"
    FILLED_QTY_MISMATCH = "filled-qty-mismatch"


@dataclass(frozen=True, slots=True)
class VenueOrderState:
    client_order_id: str
    venue_order_id: str
    status: str
    filled_qty: float


@dataclass(frozen=True, slots=True)
class ReconciliationDiff:
    order_id: str
    issue: ReconciliationIssue
    local_status: str | None
    venue_status: str | None
    local_filled_qty: float
    venue_filled_qty: float


class ExecutionReconciler:
    """Compares local OMS state with a venue snapshot without mutating either side."""

    def compare(
        self, oms: OrderManagementSystem, venue_orders: list[VenueOrderState]
    ) -> list[ReconciliationDiff]:
        venue = {item.client_order_id: item for item in venue_orders}
        diffs: list[ReconciliationDiff] = []
        terminal = {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED}

        for order_id, state in oms.orders.items():
            remote = venue.get(order_id)
            if remote is None:
                if state.status not in terminal:
                    diffs.append(
                        ReconciliationDiff(
                            order_id,
                            ReconciliationIssue.LOCAL_ONLY,
                            state.status.value,
                            None,
                            state.filled_qty,
                            0.0,
                        )
                    )
                continue
            if state.status.value != remote.status:
                diffs.append(
                    ReconciliationDiff(
                        order_id,
                        ReconciliationIssue.STATUS_MISMATCH,
                        state.status.value,
                        remote.status,
                        state.filled_qty,
                        remote.filled_qty,
                    )
                )
            if abs(state.filled_qty - remote.filled_qty) > 1e-9:
                diffs.append(
                    ReconciliationDiff(
                        order_id,
                        ReconciliationIssue.FILLED_QTY_MISMATCH,
                        state.status.value,
                        remote.status,
                        state.filled_qty,
                        remote.filled_qty,
                    )
                )

        for order_id, remote in venue.items():
            if order_id not in oms.orders:
                diffs.append(
                    ReconciliationDiff(
                        order_id,
                        ReconciliationIssue.VENUE_ONLY,
                        None,
                        remote.status,
                        0.0,
                        remote.filled_qty,
                    )
                )
        return diffs
