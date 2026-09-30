from dataclasses import dataclass


@dataclass(slots=True)
class RiskLimits:
    max_gross: float
    max_symbol: float
    max_order: float
    max_daily_loss: float
    max_leverage: float = 2.0
