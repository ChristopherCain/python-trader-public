from pythontrader.domain import Signal
from pythontrader.features.engine import FeatureVector

from .base import Strategy


class MomentumStrategy(Strategy):
    name = "momentum"

    def evaluate(self, f: FeatureVector) -> Signal:
        score = max(-1.0, min(1.0, f.imbalance * 1.7 + (0.18 - f.spread_bps / 100) * 0.2))
        conf = max(0.05, min(0.99, abs(score) * 0.75 + 0.20))
        return Signal(
            f.symbol, score, conf, 30, self.name, {"vol": f.vol, "spread_bps": f.spread_bps}
        )
