from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Opportunity:
    symbol: str
    asset_class: str
    score: float
    confidence: float
    liquidity: float
    risk: float

    @property
    def quality(self):
        return self.score * self.confidence * (1 - self.risk) * min(1.0, self.liquidity)


def rank(xs):
    return sorted(xs, key=lambda x: abs(x.quality), reverse=True)
