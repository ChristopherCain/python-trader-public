import math
from statistics import fmean


def historical_var(returns: list[float], notional: float, alpha: float = 0.99) -> float:
    if not returns:
        return 0.0
    x = sorted(returns)
    i = max(0, min(len(x) - 1, int((1 - alpha) * len(x))))
    return max(0, -x[i] * notional)


def parametric_var(returns: list[float], notional: float, z: float = 2.326) -> float:
    if len(returns) < 2:
        return 0.0
    m = fmean(returns)
    sd = math.sqrt(sum((r - m) ** 2 for r in returns) / (len(returns) - 1))
    return max(0, (z * sd - m) * notional)
