from pythontrader.domain import Fill, Side
from pythontrader.portfolio.book import Portfolio


def test_roundtrip_realized_pnl():
    p = Portfolio(10000)
    p.apply(Fill("1", "A", Side.BUY, 10, 100, 0, "SIM"))
    p.apply(Fill("2", "A", Side.SELL, 10, 110, 0, "SIM"))
    assert p.positions["A"].realized_pnl == 100
