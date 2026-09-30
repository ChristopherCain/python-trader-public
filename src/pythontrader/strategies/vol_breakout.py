from pythontrader.domain import Signal
from pythontrader.features.engine import FeatureVector

from .base import Strategy


class VolatilityBreakoutStrategy(Strategy):
    name = "vol_breakout"

    def evaluate(self, f: FeatureVector) -> Signal:
        score = max(-1.0, min(1.0, (f.vol - 0.0015) * 120 * f.imbalance))
        conf = max(0.05, min(0.99, abs(score) * 0.75 + 0.20))
        return Signal(
            f.symbol, score, conf, 30, self.name, {"vol": f.vol, "spread_bps": f.spread_bps}
        )
