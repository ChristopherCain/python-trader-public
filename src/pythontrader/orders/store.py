from dataclasses import dataclass
from enum import Enum

from pythontrader.domain import Fill, Order


class OrderStatus(str, Enum):
    NEW = "new"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass(slots=True)
class OrderRecord:
    order: Order
    status: OrderStatus = OrderStatus.NEW
    fill: Fill | None = None
    reason: str = ""


class OrderStore:
    def __init__(self):
        self.records = {}

    def add(self, o: Order):
        self.records[o.id] = OrderRecord(o)

    def filled(self, f: Fill):
        r = self.records[f.order_id]
        r.status = OrderStatus.FILLED
        r.fill = f

    def reject(self, oid: str, reason: str):
        r = self.records[oid]
        r.status = OrderStatus.REJECTED
        r.reason = reason
