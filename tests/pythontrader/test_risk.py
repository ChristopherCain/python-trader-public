from pythontrader.domain import Order, OrderType, Side
from pythontrader.portfolio.book import Portfolio
from pythontrader.risk.engine import RiskEngine
from pythontrader.risk.limits import RiskLimits


def test_order_is_clipped():
    r = RiskEngine(RiskLimits(100000, 50000, 1000, 10000))
    o = Order("x", "A", Side.BUY, 100, OrderType.MARKET)
    d = r.check(o, 100, Portfolio(100000), {"A": 100})
    assert d.accepted and d.adjusted_qty == 10
