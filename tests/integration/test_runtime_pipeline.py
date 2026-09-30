from __future__ import annotations

import asyncio

from pythontrader.core.runtime import EventRuntime
from pythontrader.domain import AssetClass, Instrument, Order, OrderType, Side
from pythontrader.risk.portfolio_engine import PortfolioRiskEngine


def test_runtime_delivers_in_sequence() -> None:
    async def scenario() -> list[int]:
        runtime = EventRuntime()
        observed: list[int] = []

        async def on_event(event) -> None:
            observed.append(event.sequence)

        runtime.subscribe("quote", on_event)
        for i in range(10):
            await runtime.publish("quote", {"i": i})
        assert await runtime.drain() == 10
        stats = runtime.stats()
        assert stats.published == 10
        assert stats.delivered == 10
        assert stats.failed == 0
        return observed

    assert asyncio.run(scenario()) == list(range(1, 11))


def test_risk_downsizes_perp_order() -> None:
    instrument = Instrument("BTC-PERP", AssetClass.PERP, "test", multiplier=1.0)
    order = Order("1", "BTC-PERP", Side.BUY, 100.0, OrderType.MARKET)
    decision = PortfolioRiskEngine().check(
        order, instrument, 50_000.0, {}, equity=100_000.0, liquidity_usd=1_000_000.0
    )
    assert decision.accepted
    assert 0 < decision.max_qty < order.qty
