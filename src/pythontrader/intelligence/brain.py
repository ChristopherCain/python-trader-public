from __future__ import annotations

from dataclasses import dataclass

from .experts import MeanReversionExpert, MicrostructureExpert, TrendExpert, VolatilityExpert


@dataclass(frozen=True, slots=True)
class BrainDecision:
    score: float
    confidence: float
    regime: str
    votes: tuple
    action: str


class TradingBrain:
    def __init__(self, experts=None):
        self.experts = experts or [
            TrendExpert(),
            MeanReversionExpert(),
            MicrostructureExpert(),
            VolatilityExpert(),
        ]

    def infer(self, features: dict):
        votes = tuple(x.vote(features) for x in self.experts)
        den = sum(max(0.01, v.confidence) for v in votes)
        score = sum(v.score * v.confidence for v in votes) / den
        conf = sum(v.confidence for v in votes) / len(votes)
        vol = float(features.get("volatility", 0))
        trend = abs(float(features.get("momentum", 0)))
        regime = "stress" if vol > 0.05 else "trend" if trend > 0.01 else "range"
        action = "buy" if score > 0.08 else "sell" if score < -0.08 else "hold"
        return BrainDecision(score, conf, regime, votes, action)
