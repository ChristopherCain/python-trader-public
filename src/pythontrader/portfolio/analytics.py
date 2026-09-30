import math
from statistics import fmean


def drawdown(equity_curve: list[float]) -> float:
    peak = 0.0
    worst = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        if peak:
            worst = min(worst, e / peak - 1)
    return worst


def sharpe(returns: list[float], annualization: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    m = fmean(returns)
    var = sum((r - m) ** 2 for r in returns) / (len(returns) - 1)
    return m / (var**0.5) * math.sqrt(annualization) if var else 0.0
