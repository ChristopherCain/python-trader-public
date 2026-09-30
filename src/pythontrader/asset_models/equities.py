from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EquityContext:
    market_open: bool
    adv_usd: float
    borrow_available: bool = True
    halt: bool = False

    def capacity(self, participation=0.02):
        return max(0.0, self.adv_usd * participation)
