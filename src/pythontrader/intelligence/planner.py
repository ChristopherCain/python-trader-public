from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from pythontrader.domain import AssetClass, Instrument


@dataclass(frozen=True, slots=True)
class ExpertVote:
    name: str
    score: float
    confidence: float
    horizon_s: int


@dataclass(frozen=True, slots=True)
class MarketContext:
    momentum: float
    mean_reversion: float
    orderflow: float
    volatility: float
    liquidity: float
    regime_trend: float
    funding: float = 0.0
    basis: float = 0.0
    crowding: float = 0.0
    meme_quality: float = 1.0


@dataclass(frozen=True, slots=True)
class TradePlan:
    action: str
    score: float
    confidence: float
    size_fraction: float
    execution_style: str
    reasons: tuple[str, ...]


class TradingPlanner:
    """Cross-asset decision planner.

    The planner deliberately separates alpha, confidence and execution style.
    That keeps the same intelligence layer usable across equities, spot crypto,
    FX, perpetuals and thin on-chain markets.
    """

    def votes(self, instrument: Instrument, ctx: MarketContext) -> list[ExpertVote]:
        votes = [
            ExpertVote(
                "trend", self._clip(ctx.momentum * (0.6 + 0.4 * ctx.regime_trend)), 0.65, 900
            ),
            ExpertVote(
                "mean_reversion",
                self._clip(ctx.mean_reversion * (1.0 - 0.5 * abs(ctx.regime_trend))),
                0.55,
                300,
            ),
            ExpertVote("orderflow", self._clip(ctx.orderflow * ctx.liquidity), 0.70, 60),
        ]
        if instrument.asset_class is AssetClass.PERP:
            votes.extend(
                [
                    ExpertVote("funding_carry", self._clip(-ctx.funding * 8_000), 0.58, 3_600),
                    ExpertVote("basis", self._clip(-ctx.basis / 40.0), 0.52, 1_800),
                    ExpertVote("crowding", self._clip(-ctx.crowding), 0.45, 600),
                ]
            )
        if instrument.asset_class is AssetClass.MEMECOIN:
            votes.append(
                ExpertVote(
                    "meme_quality",
                    self._clip((ctx.meme_quality - 0.5) * 2.0) * abs(ctx.momentum),
                    0.40 + 0.40 * ctx.meme_quality,
                    120,
                )
            )
        return votes

    def plan(self, instrument: Instrument, ctx: MarketContext) -> TradePlan:
        votes = self.votes(instrument, ctx)
        weighted = sum(v.score * v.confidence for v in votes)
        weight = sum(v.confidence for v in votes) or 1.0
        score = self._clip(weighted / weight)
        agreement = 1.0 - min(1.0, self._dispersion([v.score for v in votes]))
        confidence = self._clip01(mean(v.confidence for v in votes) * (0.55 + 0.45 * agreement))
        if ctx.volatility > 0.8:
            confidence *= 0.7
        if instrument.asset_class is AssetClass.MEMECOIN:
            confidence *= ctx.meme_quality
        threshold = (
            0.12
            if instrument.asset_class in {AssetClass.EQUITY, AssetClass.ETF, AssetClass.FX}
            else 0.18
        )
        if abs(score) < threshold:
            return TradePlan("hold", score, confidence, 0.0, "none", tuple(v.name for v in votes))
        action = "buy" if score > 0 else "sell"
        base_size = min(1.0, abs(score) * confidence)
        if instrument.asset_class is AssetClass.MEMECOIN:
            base_size *= 0.25
        execution = self._execution_style(instrument, ctx, base_size)
        reasons = tuple(
            f"{v.name}:{v.score:+.2f}"
            for v in sorted(votes, key=lambda x: abs(x.score * x.confidence), reverse=True)[:4]
        )
        return TradePlan(action, score, confidence, base_size, execution, reasons)

    def _execution_style(self, instrument: Instrument, ctx: MarketContext, size: float) -> str:
        if instrument.asset_class is AssetClass.FX:
            return "rfq_sweep" if size > 0.45 else "passive_limit"
        if instrument.asset_class in {AssetClass.EQUITY, AssetClass.ETF}:
            return "pov" if size > 0.55 else "adaptive_limit"
        if instrument.asset_class is AssetClass.PERP:
            return "maker_taker" if ctx.liquidity > 0.45 else "ioc_guarded"
        if instrument.asset_class is AssetClass.MEMECOIN:
            return "impact_guarded"
        return "venue_sweep" if size > 0.60 else "adaptive_limit"

    @staticmethod
    def _dispersion(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        m = mean(values)
        return mean(abs(x - m) for x in values)

    @staticmethod
    def _clip(value: float) -> float:
        return max(-1.0, min(1.0, value))

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, value))
