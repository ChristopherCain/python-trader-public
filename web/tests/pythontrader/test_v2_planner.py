from pythontrader.domain import AssetClass, Instrument
from pythontrader.intelligence.planner import MarketContext, TradingPlanner


def test_planner_has_asset_specific_execution():
    p = TradingPlanner()
    ctx = MarketContext(0.9, 0.0, 0.8, 0.2, 0.9, 0.8, funding=0.0002, basis=5)
    perp = p.plan(Instrument("BTC-PERP", AssetClass.PERP, "x"), ctx)
    assert perp.action in {"buy", "sell", "hold"}
    if perp.action != "hold":
        assert perp.execution_style in {"maker_taker", "ioc_guarded"}
