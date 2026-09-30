from pythontrader.domain import Side
from pythontrader.execution.matching import PriceTimeBook, RestingOrder


def test_price_time_cross():
    b = PriceTimeBook()
    b.add(RestingOrder("m", Side.SELL, 100, 5, 5))
    t = RestingOrder("t", Side.BUY, 101, 3, 3)
    m = b.cross(t)
    assert len(m) == 1 and m[0].qty == 3 and b.asks[0].remaining == 2
