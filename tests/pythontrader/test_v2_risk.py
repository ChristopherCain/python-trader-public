from pythontrader.domain import AssetClass, Instrument, Order, OrderType, Side
from pythontrader.risk.portfolio_engine import PortfolioRiskEngine, RiskPolicy


def test_memecoin_position_is_downsized():
    engine = PortfolioRiskEngine(
        RiskPolicy(max_order=1_000_000, max_symbol=1_000_000, max_memecoin_fraction=0.02)
    )
    instrument = Instrument("MEME", AssetClass.MEMECOIN, "dex")
    order = Order("1", "MEME", Side.BUY, 100_000, OrderType.MARKET)
    result = engine.check(order, instrument, 1.0, {}, equity=100_000, liquidity_usd=100_000)
    assert result.accepted
    assert result.max_qty <= 2_000


def test_historical_var_positive_on_loss_tail():
    value = PortfolioRiskEngine.historical_var(
        [-0.10, -0.03, 0.01, 0.02, 0.03], 100_000, confidence=0.8
    )
    assert value >= 3_000
