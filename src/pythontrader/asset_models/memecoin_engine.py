from __future__ import annotations

from dataclasses import dataclass
from math import log1p


@dataclass(frozen=True, slots=True)
class MemeMarketState:
    price: float
    market_cap: float
    liquidity_usd: float
    volume_24h: float
    top10_holder_fraction: float
    deployer_fraction: float
    buy_sell_ratio: float
    unique_traders_1h: int
    pool_age_hours: float


@dataclass(frozen=True, slots=True)
class MemeRiskScore:
    score: float
    liquidity: float
    concentration: float
    activity: float
    age: float
    notes: tuple[str, ...]


class MemecoinModel:
    def score(self, state: MemeMarketState) -> MemeRiskScore:
        notes: list[str] = []
        liq_ratio = state.liquidity_usd / max(state.market_cap, 1.0)
        liquidity = max(0.0, min(1.0, liq_ratio / 0.12))
        concentration = 1.0 - max(0.0, min(1.0, (state.top10_holder_fraction - 0.25) / 0.55))
        deployer = 1.0 - max(0.0, min(1.0, state.deployer_fraction / 0.15))
        activity = max(0.0, min(1.0, log1p(state.unique_traders_1h) / log1p(500)))
        turnover = max(0.0, min(1.0, state.volume_24h / max(state.market_cap, 1.0)))
        age = max(0.0, min(1.0, state.pool_age_hours / 72.0))
        score = (
            0.28 * liquidity
            + 0.22 * concentration
            + 0.15 * deployer
            + 0.15 * activity
            + 0.10 * turnover
            + 0.10 * age
        )
        if state.liquidity_usd < 25_000:
            notes.append("thin_liquidity")
        if state.top10_holder_fraction > 0.65:
            notes.append("holder_concentration")
        if state.deployer_fraction > 0.10:
            notes.append("deployer_concentration")
        if state.pool_age_hours < 2:
            notes.append("new_pool")
        if state.buy_sell_ratio > 3.0 or state.buy_sell_ratio < 0.33:
            notes.append("flow_imbalance")
        return MemeRiskScore(
            score,
            liquidity,
            concentration * deployer,
            (activity + turnover) / 2.0,
            age,
            tuple(notes),
        )

    def max_position_fraction(self, state: MemeMarketState) -> float:
        risk = self.score(state).score
        liquidity_cap = min(0.02, state.liquidity_usd / max(state.market_cap, 1.0) * 0.10)
        return max(0.0, min(liquidity_cap, 0.02 * risk * risk))

    def price_impact_estimate(self, state: MemeMarketState, notional: float) -> float:
        if state.liquidity_usd <= 0:
            return 1.0
        x = abs(notional) / state.liquidity_usd
        return min(1.0, 0.5 * x + 1.5 * x * x)
