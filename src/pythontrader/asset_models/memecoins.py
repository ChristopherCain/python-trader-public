from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemeCoinContext:
    liquidity_usd: float
    holders: int
    top10_pct: float
    age_hours: float
    realized_vol: float

    def fragility(self):
        concentration = max(0.0, min(1.0, (self.top10_pct - 0.25) / 0.65))
        thin = max(0.0, min(1.0, 1 - self.liquidity_usd / 1_000_000))
        young = max(0.0, min(1.0, 1 - self.age_hours / 168))
        return max(0.0, min(1.0, 0.45 * concentration + 0.35 * thin + 0.20 * young))

    def max_notional(self):
        return max(250.0, self.liquidity_usd * (0.0025 * (1 - self.fragility())))
