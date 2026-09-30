from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import sqrt
from statistics import mean

from pythontrader.domain import AssetClass, Instrument, Order, Side


@dataclass(frozen=True, slots=True)
class PositionView:
    symbol: str
    qty: float
    mark: float
    multiplier: float = 1.0
    asset_class: AssetClass = AssetClass.EQUITY
    sector: str = ""

    @property
    def notional(self) -> float:
        return self.qty * self.mark * self.multiplier


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    max_gross: float = 2_000_000.0
    max_net: float = 1_000_000.0
    max_symbol: float = 250_000.0
    max_order: float = 100_000.0
    max_leverage: float = 4.0
    max_daily_loss: float = 50_000.0
    max_sector_fraction: float = 0.40
    max_memecoin_fraction: float = 0.05
    max_perp_fraction: float = 0.40
    min_liquidity_usd: float = 10_000.0


@dataclass(frozen=True, slots=True)
class RiskResult:
    accepted: bool
    reason: str
    max_qty: float
    gross_after: float
    net_after: float
    symbol_after: float
    leverage_after: float


class PortfolioRiskEngine:
    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self.policy = policy or RiskPolicy()
        self.high_water_equity: float | None = None
        self.day_start_equity: float | None = None

    def exposures(self, positions: Mapping[str, PositionView]) -> tuple[float, float]:
        values = [p.notional for p in positions.values()]
        return sum(abs(v) for v in values), sum(values)

    def check(
        self,
        order: Order,
        instrument: Instrument,
        mark: float,
        positions: Mapping[str, PositionView],
        *,
        equity: float,
        daily_pnl: float = 0.0,
        liquidity_usd: float | None = None,
    ) -> RiskResult:
        if mark <= 0 or equity <= 0:
            return RiskResult(False, "invalid_mark_or_equity", 0.0, 0.0, 0.0, 0.0, float("inf"))
        if daily_pnl <= -self.policy.max_daily_loss:
            return RiskResult(
                False,
                "daily_loss_limit",
                0.0,
                *self._after(order, instrument, mark, positions, 0.0, equity),
            )
        if liquidity_usd is not None and liquidity_usd < self.policy.min_liquidity_usd:
            return RiskResult(
                False,
                "insufficient_liquidity",
                0.0,
                *self._after(order, instrument, mark, positions, 0.0, equity),
            )

        requested_notional = abs(order.qty * mark * instrument.multiplier)
        hard_notional = min(self.policy.max_order, self.policy.max_symbol)
        max_qty = hard_notional / (mark * instrument.multiplier)

        if instrument.asset_class is AssetClass.MEMECOIN:
            max_qty = min(
                max_qty, equity * self.policy.max_memecoin_fraction / (mark * instrument.multiplier)
            )
        elif instrument.asset_class is AssetClass.PERP:
            max_qty = min(
                max_qty, equity * self.policy.max_perp_fraction / (mark * instrument.multiplier)
            )

        proposed = min(order.qty, max_qty)
        gross, net, symbol, leverage = self._after(
            order, instrument, mark, positions, proposed, equity
        )
        if proposed <= 0:
            return RiskResult(False, "zero_capacity", 0.0, gross, net, symbol, leverage)
        if gross > self.policy.max_gross:
            return RiskResult(False, "gross_limit", 0.0, gross, net, symbol, leverage)
        if abs(net) > self.policy.max_net:
            return RiskResult(False, "net_limit", 0.0, gross, net, symbol, leverage)
        if abs(symbol) > self.policy.max_symbol:
            return RiskResult(False, "symbol_limit", 0.0, gross, net, symbol, leverage)
        if leverage > self.policy.max_leverage:
            return RiskResult(False, "leverage_limit", 0.0, gross, net, symbol, leverage)

        sector = str(instrument.metadata.get("sector", ""))
        if sector:
            sector_notional = sum(abs(p.notional) for p in positions.values() if p.sector == sector)
            sector_notional += abs(proposed * mark * instrument.multiplier)
            if sector_notional > equity * self.policy.max_sector_fraction:
                return RiskResult(False, "sector_concentration", 0.0, gross, net, symbol, leverage)
        reason = "accepted" if proposed >= order.qty else "downsized"
        return RiskResult(True, reason, proposed, gross, net, symbol, leverage)

    def _after(
        self,
        order: Order,
        instrument: Instrument,
        mark: float,
        positions: Mapping[str, PositionView],
        qty: float,
        equity: float,
    ) -> tuple[float, float, float, float]:
        signed = qty if order.side is Side.BUY else -qty
        existing = positions.get(order.symbol)
        current = 0.0 if existing is None else existing.qty
        projected = current + signed
        notionals = []
        for symbol, p in positions.items():
            if symbol == order.symbol:
                continue
            notionals.append(p.notional)
        symbol_notional = projected * mark * instrument.multiplier
        notionals.append(symbol_notional)
        gross = sum(abs(x) for x in notionals)
        net = sum(notionals)
        leverage = gross / max(equity, 1e-9)
        return gross, net, symbol_notional, leverage

    @staticmethod
    def historical_var(returns: list[float], notional: float, confidence: float = 0.99) -> float:
        if not returns or notional <= 0:
            return 0.0
        ordered = sorted(returns)
        tail_index = max(0, min(len(ordered) - 1, int((1.0 - confidence) * len(ordered))))
        return max(0.0, -ordered[tail_index] * notional)

    @staticmethod
    def parametric_var(returns: list[float], notional: float, z: float = 2.326347874) -> float:
        if len(returns) < 2 or notional <= 0:
            return 0.0
        mu = mean(returns)
        variance = sum((x - mu) ** 2 for x in returns) / (len(returns) - 1)
        sigma = sqrt(max(variance, 0.0))
        return max(0.0, (z * sigma - mu) * notional)

    @staticmethod
    def stress(positions: Mapping[str, PositionView], shocks: Mapping[str, float]) -> float:
        pnl = 0.0
        for symbol, p in positions.items():
            shock = shocks.get(symbol, shocks.get(p.asset_class.value, 0.0))
            pnl += p.notional * shock
        return pnl
