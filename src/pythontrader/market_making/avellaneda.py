import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MakerQuote:
    bid: float
    ask: float
    size: float


class AvellanedaStoikov:
    def __init__(self, gamma: float = 0.08, kappa: float = 1.5, base_size: float = 10):
        self.gamma = gamma
        self.kappa = kappa
        self.base_size = base_size

    def quote(self, mid: float, inventory: float, vol: float, horizon: float = 1.0) -> MakerQuote:
        reservation = mid - inventory * self.gamma * (vol**2) * horizon
        spread = self.gamma * (vol**2) * horizon + (2 / self.gamma) * math.log(
            1 + self.gamma / self.kappa
        )
        spread = max(mid * 0.0002, spread)
        size = max(1, self.base_size / (1 + abs(inventory) / 100))
        return MakerQuote(reservation - spread / 2, reservation + spread / 2, size)
