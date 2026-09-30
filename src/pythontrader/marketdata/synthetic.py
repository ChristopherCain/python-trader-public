from __future__ import annotations

import math
import random
from dataclasses import dataclass

from pythontrader.domain import Quote


@dataclass(slots=True)
class Regime:
    drift: float = 0.0
    vol: float = 0.0015
    spread_bps: float = 2.0
    liquidity: float = 1000.0


class SyntheticFeed:
    def __init__(self, symbols: list[str], seed: int = 7):
        self.rng = random.Random(seed)
        self.regime = Regime()
        self.px = {s: 100 + 20 * i for i, s in enumerate(symbols)}
        self.t = 0

    def set_regime(self, **kw) -> None:
        for k, v in kw.items():
            setattr(self.regime, k, v)

    def step(self) -> list[Quote]:
        self.t += 1
        out = []
        cyc = math.sin(self.t / 40) * self.regime.vol * 0.3
        for s, p in list(self.px.items()):
            shock = self.rng.gauss(self.regime.drift + cyc, self.regime.vol)
            p = max(0.01, p * (1 + shock))
            self.px[s] = p
            half = p * self.regime.spread_bps / 20000
            liq = max(1, self.regime.liquidity * (0.7 + self.rng.random() * 0.6))
            out.append(Quote(s, p - half, p + half, liq, liq * (0.8 + self.rng.random() * 0.4)))
        return out
