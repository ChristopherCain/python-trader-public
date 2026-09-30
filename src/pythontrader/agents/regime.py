from dataclasses import dataclass
from enum import Enum

from pythontrader.features.engine import FeatureVector


class MarketRegime(str, Enum):
    QUIET = "quiet"
    NORMAL = "normal"
    STRESSED = "stressed"
    ILLIQUID = "illiquid"


@dataclass(frozen=True, slots=True)
class RegimeAssessment:
    regime: MarketRegime
    confidence: float


class RegimeClassifier:
    def classify(self, f: FeatureVector) -> RegimeAssessment:
        if f.spread_bps > 15:
            return RegimeAssessment(MarketRegime.ILLIQUID, min(1, f.spread_bps / 40))
        if f.vol > 0.005:
            return RegimeAssessment(MarketRegime.STRESSED, min(1, f.vol / 0.01))
        if f.vol < 0.0007:
            return RegimeAssessment(MarketRegime.QUIET, 0.75)
        return RegimeAssessment(MarketRegime.NORMAL, 0.8)
