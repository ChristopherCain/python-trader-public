from __future__ import annotations

from dataclasses import dataclass

from pythontrader.domain import AssetClass, OrderType


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    style: str
    order_type: OrderType
    slices: int
    participation: float
    post_only: bool
    notes: tuple[str, ...]


class UniversalExecutionPlanner:
    def plan(self, instrument, urgency, spread_bps, volatility, notional):
        a = instrument.asset_class
        if a == AssetClass.MEMECOIN:
            return ExecutionPlan(
                "liquidity-aware",
                OrderType.IOC,
                5,
                0.0025,
                False,
                ("thin-liquidity guard", "impact cap"),
            )
        if a == AssetClass.PERP:
            return ExecutionPlan(
                "adaptive-maker-taker",
                OrderType.POST_ONLY if urgency < 0.6 else OrderType.IOC,
                8,
                0.01,
                urgency < 0.6,
                ("funding-aware", "reduce-only capable"),
            )
        if a in (AssetClass.EQUITY, AssetClass.ETF):
            return ExecutionPlan(
                "pov-vwap", OrderType.LIMIT, 12, 0.02, False, ("session-aware", "auction-aware")
            )
        if a == AssetClass.FX:
            return ExecutionPlan("rfq-sweep", OrderType.IOC, 6, 0.01, False, ("pip-aware",))
        if a == AssetClass.FUTURE:
            return ExecutionPlan(
                "microprice-pov", OrderType.LIMIT, 10, 0.015, False, ("contract-multiplier-aware",)
            )
        if a == AssetClass.CRYPTO:
            return ExecutionPlan(
                "venue-sweep",
                OrderType.IOC if urgency > 0.5 else OrderType.LIMIT,
                8,
                0.015,
                False,
                ("24x7",),
            )
        return ExecutionPlan("adaptive", OrderType.LIMIT, 6, 0.01, False, ())
