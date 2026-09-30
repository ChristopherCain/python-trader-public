from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PerpMarketState:
    mark: float
    index: float
    funding_rate: float
    open_interest_usd: float
    long_short_ratio: float = 1.0
    maintenance_margin_rate: float = 0.005

    @property
    def basis_bps(self) -> float:
        if self.index <= 0:
            return 0.0
        return (self.mark / self.index - 1.0) * 10_000.0


@dataclass(frozen=True, slots=True)
class PerpPosition:
    qty: float
    entry: float
    leverage: float
    collateral: float

    @property
    def side(self) -> int:
        return 1 if self.qty >= 0 else -1


class PerpetualModel:
    def funding_payment(self, position: PerpPosition, state: PerpMarketState) -> float:
        return -position.qty * state.mark * state.funding_rate

    def unrealized_pnl(self, position: PerpPosition, mark: float) -> float:
        return position.qty * (mark - position.entry)

    def equity(self, position: PerpPosition, state: PerpMarketState) -> float:
        return position.collateral + self.unrealized_pnl(position, state.mark)

    def maintenance_margin(self, position: PerpPosition, state: PerpMarketState) -> float:
        return abs(position.qty * state.mark) * state.maintenance_margin_rate

    def margin_ratio(self, position: PerpPosition, state: PerpMarketState) -> float:
        mm = self.maintenance_margin(position, state)
        return float("inf") if mm == 0 else self.equity(position, state) / mm

    def approximate_liquidation_price(
        self, position: PerpPosition, maintenance_margin_rate: float = 0.005
    ) -> float:
        if position.qty == 0:
            return 0.0
        q = abs(position.qty)
        if position.qty > 0:
            return max(
                0.0,
                (q * position.entry - position.collateral) / (q * (1.0 - maintenance_margin_rate)),
            )
        return (q * position.entry + position.collateral) / (q * (1.0 + maintenance_margin_rate))

    def liquidation_distance_bps(self, position: PerpPosition, state: PerpMarketState) -> float:
        liq = self.approximate_liquidation_price(position, state.maintenance_margin_rate)
        if state.mark <= 0 or liq <= 0:
            return float("inf")
        if position.qty > 0:
            return max(0.0, (state.mark - liq) / state.mark * 10_000.0)
        return max(0.0, (liq - state.mark) / state.mark * 10_000.0)

    def carry_score(
        self, state: PerpMarketState, *, basis_weight: float = 0.35, funding_weight: float = 0.65
    ) -> float:
        funding_component = max(-1.0, min(1.0, -state.funding_rate * 10_000.0 / 10.0))
        basis_component = max(-1.0, min(1.0, -state.basis_bps / 50.0))
        return funding_weight * funding_component + basis_weight * basis_component

    def crowding_score(self, state: PerpMarketState) -> float:
        ratio = max(1e-6, state.long_short_ratio)
        return max(-1.0, min(1.0, (ratio - 1.0) / (ratio + 1.0) * 2.0))
