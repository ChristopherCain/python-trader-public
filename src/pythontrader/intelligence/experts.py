from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExpertVote:
    name: str
    score: float
    confidence: float
    rationale: str


class Expert:
    name = "expert"

    def vote(self, features: dict) -> ExpertVote:
        raise NotImplementedError


class TrendExpert(Expert):
    name = "trend"

    def vote(self, f):
        m = float(f.get("momentum", 0))
        return ExpertVote(self.name, max(-1, min(1, m * 20)), 0.65, "multi-horizon momentum")


class MeanReversionExpert(Expert):
    name = "mean_reversion"

    def vote(self, f):
        z = float(f.get("zscore", 0))
        return ExpertVote(
            self.name, max(-1, min(1, -z / 3)), 0.55, "distance from local equilibrium"
        )


class MicrostructureExpert(Expert):
    name = "microstructure"

    def vote(self, f):
        x = float(f.get("imbalance", 0))
        return ExpertVote(self.name, max(-1, min(1, x)), 0.70, "order-book pressure")


class VolatilityExpert(Expert):
    name = "volatility"

    def vote(self, f):
        v = float(f.get("volatility", 0))
        score = -min(1, v * 20)
        return ExpertVote(self.name, score, 0.5, "volatility-aware risk pressure")
