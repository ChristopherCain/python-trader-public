from time import time

from pythontrader.domain import Fill, Order, OrderType, Side
from pythontrader.execution.oms import OrderManagementSystem, OrderStatus
from pythontrader.marketdata.orderbook import OrderBook


def test_market_order_fills():
    book = OrderBook("BTC")
    book.reset([(99, 100)], [(101, 100)], sequence=1, ts=1.0)
    oms = OrderManagementSystem()
    order = Order("o1", "BTC", Side.BUY, 5, OrderType.MARKET)
    oms.submit(order)
    fills = oms.execute_against_book("o1", book)
    assert fills
    state = oms.orders["o1"]
    assert state.status is OrderStatus.FILLED
    assert state.filled_qty == 5


def test_duplicate_fill_id_is_idempotent():
    oms = OrderManagementSystem()
    order = Order("o2", "BTC", Side.BUY, 10, OrderType.LIMIT, limit_price=101)
    oms.submit(order)
    oms.accept("o2")
    fill = Fill("o2", "BTC", Side.BUY, 2, 100, 0.01, "test", time())
    oms.apply_fill("fill-1", fill)
    before = oms.orders["o2"].filled_qty
    oms.apply_fill("fill-1", fill)
    assert oms.orders["o2"].filled_qty == before
