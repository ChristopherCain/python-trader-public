from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True, slots=True)
class SlippageEstimate:
    arrival_price: float
    expected_price: float
    slippage_bps: float
    market_impact_bps: float
    volatility_bps: float
    participation_penalty_bps: float


class SlippageModel:
    """Square-root impact model with spread, volatility and participation terms."""

    def __init__(
        self,
        *,
        impact_coefficient: float = 18.0,
        volatility_coefficient: float = 0.35,
        participation_coefficient: float = 12.0,
    ) -> None:
        self.impact_coefficient = impact_coefficient
        self.volatility_coefficient = volatility_coefficient
        self.participation_coefficient = participation_coefficient

    def estimate(
        self,
        *,
        side: str,
        arrival_price: float,
        spread_bps: float,
        order_notional: float,
        adv_notional: float,
        volatility_daily: float,
        participation_rate: float,
    ) -> SlippageEstimate:
        if arrival_price <= 0 or order_notional < 0 or adv_notional <= 0:
            raise ValueError("invalid market inputs")
        if not 0 <= participation_rate <= 1:
            raise ValueError("participation_rate must be in [0, 1]")

        size_fraction = order_notional / adv_notional
        impact = self.impact_coefficient * sqrt(max(0.0, size_fraction))
        vol = (
            self.volatility_coefficient
            * max(0.0, volatility_daily)
            * 10_000.0
            * sqrt(max(size_fraction, 1e-12))
        )
        participation = self.participation_coefficient * participation_rate * participation_rate
        half_spread = max(0.0, spread_bps) / 2.0
        total = half_spread + impact + vol + participation
        direction = 1.0 if side.lower() == "buy" else -1.0
        expected = arrival_price * (1.0 + direction * total / 10_000.0)
        return SlippageEstimate(arrival_price, expected, total, impact, vol, participation)
