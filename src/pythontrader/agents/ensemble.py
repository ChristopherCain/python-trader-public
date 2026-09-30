from dataclasses import dataclass

from pythontrader.features.engine import FeatureVector
from pythontrader.strategies.base import Strategy


@dataclass(frozen=True, slots=True)
class Consensus:
    symbol: str
    score: float
    confidence: float
    votes: int


class StrategyEnsemble:
    def __init__(self, strategies: list[Strategy], weights: dict[str, float] | None = None):
        self.strategies = strategies
        self.weights = weights or {}

    def decide(self, f: FeatureVector) -> Consensus:
        sigs = [s.evaluate(f) for s in self.strategies]
        denom = sum(self.weights.get(s.source, 1.0) * s.confidence for s in sigs) or 1.0
        score = sum(s.score * s.confidence * self.weights.get(s.source, 1.0) for s in sigs) / denom
        conf = sum(s.confidence for s in sigs) / len(sigs) if sigs else 0.0
        return Consensus(f.symbol, max(-1, min(1, score)), conf, len(sigs))
