from pythontrader.domain import AssetClass, Instrument, OrderType
from pythontrader.execution.universal_router import UniversalExecutionPlanner


def test_asset_specific_plans():
    p = UniversalExecutionPlanner()
    m = p.plan(Instrument("DOGE", AssetClass.MEMECOIN, "X"), 0.3, 10, 0.2, 10000)
    d = p.plan(Instrument("BTC-PERP", AssetClass.PERP, "X"), 0.2, 2, 0.05, 10000)
    assert m.style == "liquidity-aware" and m.participation < 0.01
    assert d.style == "adaptive-maker-taker" and d.order_type == OrderType.POST_ONLY
