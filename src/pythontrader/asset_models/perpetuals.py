from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PerpState:
    mark: float
    index: float
    funding_rate: float
    open_interest: float
    leverage: float = 1.0

    @property
    def basis_bps(self):
        return 10000 * (self.mark / self.index - 1) if self.index else 0.0

    @property
    def carry_signal(self):
        return max(-1.0, min(1.0, -self.funding_rate * 10000 / 25))


def liquidation_price(entry, side, leverage, maintenance=0.005):
    if leverage <= 0:
        raise ValueError("leverage must be positive")
    move = (1 / leverage) - maintenance
    return entry * (1 - move) if side == "long" else entry * (1 + move)
