from pythontrader.domain import Signal
from pythontrader.features.engine import FeatureVector

from .base import Strategy


class EntropyRegimeStrategy(Strategy):
    name = "entropy_regime"

    def evaluate(self, f: FeatureVector) -> Signal:
        score = max(-1.0, min(1.0, (0.69 - f.entropy) * 2 * f.imbalance))
        conf = max(0.05, min(0.99, abs(score) * 0.75 + 0.20))
        return Signal(
            f.symbol, score, conf, 30, self.name, {"vol": f.vol, "spread_bps": f.spread_bps}
        )
